from typing_extensions import Literal

from pydantic_ai import Agent, RunContext
import logfire
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from src.service.chunk_service import ChunkService, get_chunk_service
from src.service.activity_service import ActivityService, get_activity_service
import asyncio
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic import Field
from datetime import datetime
from langfuse import Langfuse

load_dotenv()

@dataclass
class AgentConfig:
    chunk_service: ChunkService
    student_id: str
    activity_service: ActivityService

primary_model = GroqModel('openai/gpt-oss-120b')
secondary_model = GroqModel('qwen/qwen3-32b')
fallback_model = FallbackModel(primary_model, secondary_model)

capstone_agent = Agent(fallback_model, deps_type = AgentConfig)

@capstone_agent.instructions
def system_prompt() -> str:
    langfuse = Langfuse()
    prompt = langfuse.get_prompt("capstone/prod")
    return prompt.compile()

@capstone_agent.tool
async def search_chunks(ctx: RunContext[AgentConfig],
                        query: str = Field (..., description="The student's query about activities or events. Extract the core technical query for searching relevant chunks in the database."),
                        top_k: int = Field(default=5, description="The number of top relevant chunks to return.")) -> str:
    """
    Search for relevant chunks in the database based on the query.
    """

    if ctx.deps and ctx.deps.chunk_service:
        chunk_service = ctx.deps.chunk_service
    else:
        chunk_service = get_chunk_service()
    with logfire.span("Searching Chunks with query: {}".format(query)):
        relevant_chunks = await chunk_service.search_chunk_by_query(query, top_k)
        logfire.info(f"Found {len(relevant_chunks)} relevant chunks: {relevant_chunks}")
    return 'Relevant chunks: ' + ','.join([chunk['text_content'] for chunk in relevant_chunks])


ActivityStatus = Literal['OPEN', 'CLOSED', 'COMPLETED', 'CANCELLED']
@capstone_agent.tool
async def search_relevant_activities(ctx: RunContext[AgentConfig], 
                                    time_start: datetime = Field(default=None, description="The start time of the activity (format: YYYY-MM-DD)"),
                                    name: str = Field(default=None, description="The name of the activity"),
                                    time_end: datetime = Field(default=None, description="The end time of the activity (format: YYYY-MM-DD)"),
                                    location: str = Field(default=None, description="The location of the activity"),
                                    status: ActivityStatus = Field(default=None, description="The status of the activity")) -> str:
    """
    Search for relevant activities based on activity name, time range, location, and status.
    """
    if ctx.deps and ctx.deps.chunk_service:
        chunk_service = ctx.deps.chunk_service
    else:
        chunk_service = get_chunk_service()

    with logfire.span("Searching Relevant Activities with parameters: time_start={}, name={}, time_end={}, location={}, status={}".format(time_start, name, time_end, location, status)):
        relevant_activities = await chunk_service.search_relevant_activity(time_start=time_start, name=name, time_end=time_end, location=location, status=status, top_k=5)
        logfire.info(f"Search parameters - time_start: {time_start}, name: {name}, time_end: {time_end}, location: {location}, status: {status}")
        logfire.info(f"Found {len(relevant_activities)} relevant activities: {relevant_activities}")
        if len(relevant_activities) == 0:
            return "No relevant activities found based on the provided parameters."
    return relevant_activities

@capstone_agent.tool
async def register_activity(ctx: RunContext[AgentConfig], 
                            activity_name: str = Field(..., description="The name of the activity the student wants to register for")) -> str:
    """
    Register the student for the specified activity.
    """
    if not ctx.deps.student_id:
        return "Student ID is missing. Unable to register for the activity."
    with logfire.span("Registering for activity: {}".format(activity_name)):
        result = await ctx.deps.activity_service.register_activity(student_id=ctx.deps.student_id, activity_name=activity_name)
        logfire.info(f"Registering student_id: {ctx.deps.student_id} for activity: {activity_name} with result: {result}")
    return result

@capstone_agent.tool
async def unregister_activity(ctx: RunContext[AgentConfig], 
                              activity_name: str = Field(..., description="The name of the activity the student wants to unregister from")) -> str:
    """
    Unregister the student from the specified activity.
    """
    if not ctx.deps.student_id:  
        return "Student ID is missing. Unable to unregister from the activity."
    with logfire.span("Unregistering from activity: {}".format(activity_name)):
        result = await ctx.deps.activity_service.unregister_activity(student_id=ctx.deps.student_id, activity_name=activity_name)
        logfire.info(f"Unregistering student_id: {ctx.deps.student_id} from activity: {activity_name} with result: {result}")
    return result

capstone_agent.model = primary_model

app = capstone_agent.to_web()


