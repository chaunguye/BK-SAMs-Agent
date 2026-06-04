"""Test fallback model behavior when primary model rate limit is hit."""
import asyncio
from src.agents.agent import capstone_agent
from src.agents.agent_config import AgentConfig

async def test_fallback():
    """
    Send multiple requests to trigger rate limit and test fallback.
    Watch the console output to see:
    - Which model is being used
    - When it switches from Groq to Gemini
    """
    
    # Create a mock config
    config = AgentConfig(
        student_id="test_student",
        student_name="Test User",
    )
    
    # Send multiple requests to hit rate limit
    test_prompts = [
        "What is an activity?",
        "Tell me about registered activities",
        "List all activities",
        "Describe learning outcomes",
        "What are competencies?",
        "Tell me more about activities",
        "What is an activity?",
        "Tell me about registered activities",
        "List all activities",
        "Describe learning outcomes",
        "What are competencies?",
        "Tell me more about activities",
    ]
    
    for i, prompt in enumerate(test_prompts):
        print(f"\n{'='*60}")
        print(f"Request {i+1}: {prompt}")
        print(f"{'='*60}")
        try:
            result = await capstone_agent.run(prompt, deps=config)
            print(f"Response: {result.data[:200]}...")  # Print first 200 chars
        except Exception as e:
            print(f"Error: {e}")
            print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_fallback())
