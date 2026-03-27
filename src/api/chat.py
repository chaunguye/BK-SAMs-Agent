from src.cache.cache_manager import get_cache_manager
from fastapi import APIRouter, WebSocket, Depends, HTTPException
from src.util.chat_request import ChatRequest
from src.agents.agent import capstone_agent, AgentConfig
from src.service.chunk_service import get_chunk_service
from src.service.activity_service import get_activity_service
import logfire
from fastapi.responses import JSONResponse
from pydantic_ai import (
    AgentRunResultEvent,
    FunctionToolCallEvent,
    PartDeltaEvent,
    TextPartDelta,
    PartEndEvent,
    PartStartEvent,
    TextPart
)
from src.websocket.websocketManager import get_websocket_manager
import asyncio
from src.middleware.authorization import StudentContext, get_student_context
import uuid
from src.service.conversation_service import get_conversation_service
from typing import Optional
import datetime
from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage

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

@router.get("/conversation")
async def get_conversation(student_context: StudentContext = Depends(get_student_context)):
    """This endpoint returns a list of conversation of a user based on user ID"""
    if student_context is None:
        return JSONResponse({"user_type": "guess", "conversation": []})
    converation_service = get_conversation_service()
    conversation_list = await converation_service.get_conversation_list(student_context.student_id)
    list_json = [
        {
            "id": str(conver["id"]),
            "title": conver["title"]
        }
        for conver in conversation_list
    ]
    return JSONResponse({"user_type": "student", "conversation": list_json})

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket,
                             student_context: StudentContext = Depends(get_student_context),
                             conversation_id: Optional[uuid.UUID] = None):
    websocketManager = get_websocket_manager()
    conversation_service = get_conversation_service()
    load_history = False

    logfire.info(f"Conversation ID: {conversation_id}")

    if conversation_id is None and student_context is not None:
        title = f"{datetime.datetime.now()}"
        conversation_id = await conversation_service.create_conversation(title, student_context.student_id)
    elif conversation_id is None and student_context is None:
        conversation_id = uuid.uuid4()
    elif conversation_id is not None and student_context is None:
        logfire.warning(f"Guess try to access to conversation: {conversation_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Access Denied")
    elif conversation_id is not None and student_context is not None:
        load_history = True

    await websocketManager.connect(conversation_id, websocket)

    # if conversation ID => Send history message.
    if load_history:
        prev_chat = conversation_service.load_history(conversation_id)
        [websocketManager.send_personal_message(conversation_id, chat['text_content'], type="text", sender_type=chat['sender_type']) for chat in prev_chat] 
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=600.0)
            except asyncio.TimeoutError:
                print(f"Websocket connection with conversation ID: {conversation_id} timed out.")
                await websocket.close()
                break
            with logfire.span("Fetching Conversation History"):
                history = await conversation_service.get_conversation(conversation_id)
                logfire.info(f"History: {history}")
                logfire.info(f"Type of History: {type(history)}")
                if history:
                    if history[0] is not None:
                        logfire.info(f"Type of each element: {type(history[0])}")
                logfire.info(f"Student Context: {student_context}")
            
            deps = AgentConfig(chunk_service=get_chunk_service(), activity_service=get_activity_service(), student_id=student_context.student_id if student_context else None)
            
            async for event in capstone_agent.run_stream_events(data, deps=deps,message_history=history):
                # print(f"Type: {type(PartDeltaEvent).__name__}")
                # print(f"Attributes: {dir(PartDeltaEvent)}")
                if isinstance(event, PartDeltaEvent) and event.delta and isinstance(event.delta, TextPartDelta):
                    await websocketManager.send_personal_message(conversation_id, event.delta.content_delta, type="text")
                
                elif isinstance(event, PartEndEvent) and event.part and isinstance(event.part, TextPart):
                    await websocketManager.send_personal_message(conversation_id, "Agent has completed the task.", type="end")
                
                elif isinstance(event, FunctionToolCallEvent):
                    await websocketManager.send_personal_message(conversation_id, f"Calling tool: {event.part.tool_name} with args: {event.part.args}", type="tool_call")
                
                elif isinstance(event, AgentRunResultEvent):
                    await websocketManager.send_personal_message(conversation_id, f"Final result: {event}", type="end")

                    message = event.result.new_messages()
                    if student_context:
                        logfire.info(f"Saving conversation and Set Cache for conversation_id: {conversation_id}. Message: {message}")
                        await conversation_service.save_conversation(conversation_id, message, history, student_id=student_context.student_id)
                    else:
                        logfire.info(f"Set Cache only for guess conversation_id: {conversation_id}. Message: {message}")
                        await conversation_service.save_conversation(conversation_id, message, history)

                    logfire.info(f"Full Context Agent Hold: {event.result.all_messages()}")
                    

                elif isinstance(event, PartStartEvent) and event.part and isinstance(event.part, TextPart):
                    await websocketManager.send_personal_message(conversation_id, event.part.content, type="text")
                
                else:
                    await websocketManager.send_personal_message(conversation_id, f"Event: {event}", type="thinking")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        websocketManager.disconnect(conversation_id)