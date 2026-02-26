from pydantic_ai import Agent, RunContext
import logfire
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from src.rag.processing import DocumentProcessor, get_document_processor
import asyncio

load_dotenv()

@dataclass
class AgentConfig:
    document_processor: DocumentProcessor

capstone_agent = Agent('google-gla:gemini-2.5-flash', instructions='You are a helpful assistant. Call search chunks with every user\'s query.', deps_type=AgentConfig)

@capstone_agent.tool
async def search_chunks(ctx: RunContext[AgentConfig], query: str, top_k: int = 5) -> str:
    """
    Search for relevant chunks in the database based on the query.
    """

    if ctx.deps and ctx.deps.document_processor:
        document_processor = ctx.deps.document_processor
    else:
        document_processor = get_document_processor()
    relevant_chunks = await document_processor.search_chunk_by_query(query, top_k)
    return 'Relevant chunks: ' + ','.join([chunk['text_content'] for chunk in relevant_chunks])



app = capstone_agent.to_web()


