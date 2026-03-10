from pydantic_ai import Agent, RunContext
import logfire
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from src.rag.processing import DocumentProcessor, get_document_processor
import asyncio
from pydantic import Field

load_dotenv()

@dataclass
class AgentConfig:
    document_processor: DocumentProcessor

# google-gla:gemini-2.5-flash
capstone_agent = Agent('groq:openai/gpt-oss-120b', 
                       instructions="""## 🚩 Agent System Prompt

**Role:** You are the **BK-SAMs Assistant**, a friendly and grounded AI guide for university students. Your goal is to help students discover social activities, understand campus events, and manage their registrations.

**Tone and Personality:**

* **Friendly & Peer-like:** Use a warm, supportive, and encouraging tone. You are a fellow student's helpful assistant, not a rigid administrator.
* **Concise:** Students are busy. Provide clear, direct answers using Markdown for readability (bolding, lists).
* **Safe & Accurate:** Only provide information based on the retrieved data. If you don't know something, admit it and suggest a different query.

**Operational Guidelines:**

### 1. Handling Information Queries (RAG)

* When a student asks about activities (e.g., "What clubs are meeting this Friday?" or "Tell me about the volunteer event"), **always** use the `search_chunks` tool.
* **Query Condensing:** If the user's message is long or contains multiple unrelated thoughts, extract the **core technical query** before passing it to `search_chunks`.
* *Bad Parameter:* "Hi, I'm a freshman and I'm really bored so I want to find something fun to do like a sports club or maybe art."
* *Good Parameter:* "Freshman sports clubs and art activities"



### 2. Activity Registration (Placeholder)

* **Registering:** When a student explicitly wants to join an activity, acknowledge their intent.
* *Current Logic:* Note that the registration function is under maintenance. Tell them: "I'll be able to help you sign up for that very soon! For now, I can give you more details about the event."


* **Unregistering:** Handle requests to leave an activity with the same "Under Maintenance" message, maintaining a helpful attitude.

### 3. Handling Spoilers & Context (System Requirement)

* **Crucial:** Always refer only to events and information provided in the current context. Do not "hallucinate" future events or details not found in the search results.
""", deps_type=AgentConfig)

@capstone_agent.tool
async def search_chunks(ctx: RunContext[AgentConfig],
                        query: str = Field (..., description="The student's query about activities or events. Extract the core technical query for searching relevant chunks in the database."),
                        top_k: int = Field(default=5, description="The number of top relevant chunks to return.")) -> str:
    """
    Search for relevant chunks in the database based on the query.
    """

    if ctx.deps and ctx.deps.document_processor:
        document_processor = ctx.deps.document_processor
    else:
        document_processor = get_document_processor()
    relevant_chunks = await document_processor.search_chunk_by_query(query, top_k)
    return 'Relevant chunks: ' + ','.join([chunk['text_content'] for chunk in relevant_chunks])


@capstone_agent.tool
async def search_activities_details(ctx: RunContext[AgentConfig], 
                                    time_start: str = Field(default=None, description="The start time of the activity (format: YYYY-MM-DD)"),
                                    name: str = Field(default=None, description="The name of the activity"),
                                    time_end: str = Field(default=None, description="The end time of the activity (format: YYYY-MM-DD)"),
                                    location: str = Field(default=None, description="The location of the activity"),
                                    status: str = Field(default=None, description="The status of the activity")) -> str:
    """
    Search for relevant activities based on activity name, time range, location, and status.
    """
    if ctx.deps and ctx.deps.document_processor:
        document_processor = ctx.deps.document_processor
    else:
        document_processor = get_document_processor()
    
    relevant_activities = await document_processor.search_relevant_activity(time_start=time_start, name=name, time_end=time_end, location=location, status=status, top_k=5)
    return "Activity search is currently under maintenance. I'll be able to help you with that very soon!"

app = capstone_agent.to_web()


