import pytest_asyncio
from src.agents.agent import capstone_agent
from src.agents.agent_config import AgentConfig
from src.service.chunk_service import get_chunk_service
from src.service.activity_service import get_activity_service

@pytest_asyncio.fixture
async def real_agent():
    """Returns the production agent using the real LLM."""
    return capstone_agent

@pytest_asyncio.fixture
async def live_deps():
    """
    Returns AgentConfig with LIVE services.
    This will connect to your real database/vector store.
    Ensure you are running against a development or staging database!
    """
    chunk_service = get_chunk_service()
    activity_service = get_activity_service()
    
    return AgentConfig(
        chunk_service=chunk_service,
        activity_service=activity_service,
        student_id="550e8400-e29b-41d4-a716-446655440000",      # Valid UUID string
        student_name="Test Student"
    )

@pytest_asyncio.fixture()
async def live_guest_deps():
    """Returns AgentConfig for an unauthenticated guest user."""
    chunk_service = get_chunk_service()
    activity_service = get_activity_service()
    
    return AgentConfig(
        chunk_service=chunk_service,
        activity_service=activity_service,
        student_id=None,
        student_name=None
    )
