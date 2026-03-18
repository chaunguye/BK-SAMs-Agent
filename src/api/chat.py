from fastapi import APIRouter, WebSocket, Depends, HTTPException
from src.util.chat_request import ChatRequest
from src.agents.agent import capstone_agent, AgentConfig
from src.service.chunk_service import get_chunk_service
from src.service.activity_service import get_activity_service
import logfire
from fastapi.responses import JSONResponse
from pydantic_ai import (
    AgentStreamEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    RunContext,
    TextPartDelta,
    ThinkingPartDelta,
    ToolCallPartDelta,
)
from src.websocket.websocketManager import get_websocket_manager
import asyncio
from src.middleware.authorization import StudentContext, get_student_context

router = APIRouter(prefix="/chat", tags=["Agent Chat"])

@router.post("")
async def chat_with_agent(request: ChatRequest,
                          student_context: StudentContext = Depends(get_student_context)):
    """This endpoint is used to send a message to the agent and get a response."""

    deps = AgentConfig(chunk_service=get_chunk_service(), activity_service=get_activity_service(), student_id=student_context.student_id if student_context else None)
    response = await capstone_agent.run(request.message, deps=deps)
    return JSONResponse({"response": response.output})

@router.get("/test_query")
async def test_query(query: str):
    """This endpoint is used to test the search functionality of the search chunks function."""
    chunk_service = get_chunk_service()
    results = await chunk_service.search_chunks_by_query(query)
    return JSONResponse({"results": [result['text_content'] for result in results]})

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket,
                             student_context: StudentContext = Depends(get_student_context)):
    websocketManager = get_websocket_manager()
    if student_context is None:
        await websocketManager.connect("anonymous", websocket)
    else:
        await websocketManager.connect(student_context.student_id, websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                print(f"Websocket connection with student_id: {student_context.student_id if student_context else 'anonymous'} timed out.")
                await websocket.close()
                break
            deps = AgentConfig(chunk_service=get_chunk_service(), activity_service=get_activity_service(), student_id=student_context.student_id if student_context else None)
            async for event in capstone_agent.run_stream_events(data, deps=deps):
                if isinstance(event, PartDeltaEvent):
                    await websocketManager.send_personal_message(student_context.student_id, event.delta.content_delta, type="text")
                elif isinstance(event, FunctionToolCallEvent):
                    await websocketManager.send_personal_message(student_context.student_id, f"Calling tool: {event.part.tool_name} with args: {event.part.args}", type="tool_call")
                elif isinstance(event, FinalResultEvent):
                    await websocketManager.send_personal_message(student_context.student_id, f"Final result: {event}", type="final_result")
                else:
                    await websocketManager.send_personal_message(student_context.student_id, f"Received event: {event}", type="event")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        if student_context is not None:
            websocketManager.disconnect(student_context.student_id)
        else:
            websocketManager.disconnect("anonymous")