from pydantic_ai import Agent, RunContext, DeferredToolRequests, Tool
from dotenv import load_dotenv
from dataclasses import dataclass
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.fallback import FallbackModel
from pydantic import Field
from datetime import datetime
from langfuse import Langfuse
import uuid
from src.tools.tools import search_chunks, search_activity_chunks, search_relevant_activities, get_activity_details, register_activity, get_activity_ids_by_name, unregister_activity, get_registered_activities
from src.agents.agent_config import AgentConfig

load_dotenv()


primary_model = GroqModel('openai/gpt-oss-120b')
secondary_model = GroqModel('qwen/qwen3-32b')
fallback_model = FallbackModel(primary_model, secondary_model)

capstone_agent = Agent(fallback_model, 
                       deps_type = AgentConfig, 
                       output_type=[str, DeferredToolRequests],
                       tools = [search_chunks, 
                                search_activity_chunks, 
                                search_relevant_activities, 
                                get_activity_details, 
                                get_activity_ids_by_name, 
                                get_registered_activities,
                                Tool(register_activity, requires_approval=True),
                                Tool(unregister_activity, requires_approval=True)
                                ]
                       )

@capstone_agent.instructions
def system_prompt() -> str:
    langfuse = Langfuse()
    prompt = langfuse.get_prompt("capstone/prod")
    return prompt.compile()

@capstone_agent.instructions
def add_user_name(ctx: RunContext[AgentConfig]) -> str:
    context = ""
    if ctx.deps and ctx.deps.student_id:
        context += "This is an authenticated student."
        context + f"The student's name is {ctx.deps.student_name}" if ctx.deps and ctx.deps.student_name else context + "The student's name is not provided."
    else:
            context += "This is a guest . No student information is available. Guest can not register or unregister activities, but can view activity details and search for relevant activities. Please block any attempts to register or unregister activities and respond with an appropriate message indicating that the user is not authenticated."
    return context

@capstone_agent.instructions
def add_current_time() -> str:
    return f"The current date and time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."


capstone_agent.model = primary_model

app = capstone_agent.to_web()


