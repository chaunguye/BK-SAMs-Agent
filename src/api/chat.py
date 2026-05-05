import json

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
    TextPart,
    DeferredToolRequests,
    DeferredToolResults
)
from src.websocket.websocketManager import get_websocket_manager
import asyncio
from src.middleware.authorization import StudentContext, get_student_context, get_student_context_by_token
import uuid
from src.service.conversation_service import get_conversation_service
from typing import Optional
import datetime
from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage
from src.util.filter_history import name_conversation
import pytz

router = APIRouter(prefix="/chat", tags=["Agent Chat"])

@router.post("")
async def chat_with_agent(request: ChatRequest,
                          student_context: StudentContext = Depends(get_student_context)):
    """This endpoint is used to send a message to the agent and get a response."""

    deps = AgentConfig(chunk_service=get_chunk_service(), activity_service=get_activity_service(), student_id=student_context.student_id if student_context else None, student_name=student_context.student_name if student_context else None)
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
        return JSONResponse({"user_type": "guest", "conversation": []})
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

@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: uuid.UUID, student_context: StudentContext = Depends(get_student_context)):
    """This endpoint deletes a conversation based on conversation ID"""
    if student_context is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    converation_service = get_conversation_service()
    status = await converation_service.delete_conversation(conversation_id, student_context.student_id)
    if not status:
        raise HTTPException(status_code=403, detail="Forbidden")
    return JSONResponse({"message": "Conversation deleted successfully"})

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket,
                             token: Optional[str] = None,
                             conversation_id: Optional[uuid.UUID] = None):
    websocketManager = get_websocket_manager()
    conversation_service = get_conversation_service()
    student_context = get_student_context_by_token(token) if token else None
    load_history = False

    is_new_conversation = False
    first_message = f"Xin chào, {student_context.student_name}" if student_context else "Xin chào bạn!"
    first_message += " Tôi có thể giúp gì cho bạn hôm nay?"

    logfire.info(f"Conversation ID: {conversation_id}")
    logfire.info(f"Student Context: {student_context}")


    if conversation_id is None and student_context is not None:
        title = "New Chat..."
        logfire.info(f"Creating new conversation for student_id: {student_context.student_id} with title: {title}")
        conversation_id = await conversation_service.create_conversation(title, student_context.student_id)
        is_new_conversation = True
    elif conversation_id is None and student_context is None:
        conversation_id = uuid.uuid4()
    elif conversation_id is not None and student_context is None:
        logfire.warning(f"Guest try to access to conversation: {conversation_id}")
        await websocket.close(code=1008, reason="Access Denied")
    elif conversation_id is not None and student_context is not None:
        # Check if the conversation belongs to the student
        conversation_list = await conversation_service.get_conversation_list(student_context.student_id)
        if not any(str(conver["id"]) == str(conversation_id) for conver in conversation_list):
            logfire.warning(f"Student_id: {student_context.student_id} try to access to conversation: {conversation_id} which is not belong to them")
            await websocket.close(code=1008, reason="Access Denied")
        load_history = True

    await websocketManager.connect(conversation_id, websocket)

    # if conversation ID => Send history message.
    if load_history:
        prev_chat = await conversation_service.load_history(conversation_id)
        logfire.info(f"Load previous chat history for conversation_id {conversation_id}")
        # [websocketManager.send_personal_message(conversation_id, chat['text_content'], type="text", sender_type=chat['sender_type']) for chat in prev_chat] 
        for chat in prev_chat:
            await websocketManager.send_personal_message(conversation_id, chat['text_content'], type="history", sender_type=chat['sender_type'])
    # else:
    #     await websocketManager.send_personal_message(conversation_id, first_message, type="text")

    require_approval = (False, None)

    try:
        while True:
            try:
                raw_data = await asyncio.wait_for(websocket.receive_json(), timeout=600.0)
                data = raw_data.get("message", "")
                # List of approval response 
                approval_response = raw_data.get("approval_response", None)

            except asyncio.TimeoutError:
                print(f"Websocket connection with conversation ID: {conversation_id} timed out.")
                await websocket.close()
                break

            if is_new_conversation and data:
            # Run titling in the background so it doesn't block the chat stream
                async def update_title_task(cid, first_msg):
                    try:
                        new_title = await name_conversation(first_msg)
                        logfire.info(f"Generated title for conversation_id {cid}: {new_title}")
                        await conversation_service.update_title(cid, new_title)
                        # Notify frontend to update the sidebar
                        await websocketManager.send_session_init(cid, new_title)
                    except Exception as e:
                        logfire.error(f"Error occurred while updating conversation title: {e}")
                
                asyncio.create_task(update_title_task(conversation_id, data))
                is_new_conversation = False

            # Not fetch cache on new conversation - Fix this
            with logfire.span("Fetching Conversation History"):
                history = await conversation_service.get_conversation(conversation_id)
                logfire.info(f"History: {history}")
                logfire.info(f"Type of History: {type(history)}")
                if history:
                    if history[0] is not None:
                        logfire.info(f"Type of each element: {type(history[0])}")
                logfire.info(f"Student Context: {student_context}")

            approval_result = None
            if approval_response:
                approval_result = DeferredToolResults()
                for approval in approval_response:
                    approval_result.approvals[approval['tool_call_id']] = approval['confirm']
            
            if approval_result is None and require_approval[0] == True:
                approval_result = DeferredToolResults()
                for id in require_approval[1]:
                    approval_result.approvals[id] = False

            
            deps = AgentConfig(chunk_service=get_chunk_service(), activity_service=get_activity_service(), student_id=student_context.student_id if student_context else None, student_name=student_context.student_name if student_context else None)
            
            async for event in capstone_agent.run_stream_events(data, deps=deps,message_history=history, deferred_tool_results=approval_result):
                # print(f"Type: {type(PartDeltaEvent).__name__}")
                # print(f"Attributes: {dir(PartDeltaEvent)}")
                if isinstance(event, PartDeltaEvent) and event.delta and isinstance(event.delta, TextPartDelta):
                    await websocketManager.send_personal_message(conversation_id, event.delta.content_delta, type="text")
                
                elif isinstance(event, PartEndEvent) and event.part and isinstance(event.part, TextPart):
                    await websocketManager.send_personal_message(conversation_id, "Agent has completed the task.", type="end")
                
                elif isinstance(event, FunctionToolCallEvent):
                    await websocketManager.send_personal_message(conversation_id, f"Calling tool: {event.part.tool_name} with args: {event.part.args}", type="tool_call")
                
                elif isinstance(event, AgentRunResultEvent):
                    if isinstance(event.result.output, DeferredToolRequests):
                        require_approval = (True, [id.tool_call_id for id in event.result.output.approvals])
                        for approval in event.result.output.approvals:
                            # await websocketManager.send_personal_message(conversation_id, f"Please confirm the registration for the activity: {approval.args['name']}\nStatus: {approval.args['status']}\nLocation: {approval.args['location']}\nStart Time: {approval.args['start_time']}\nEnd Time: {approval.args['end_time']}", type="approval", tool_call_id=approval.tool_call_id)
                            logfire.info(f"Args for approval: {approval.args}")
                            args = approval.args
                            if isinstance(args, str):
                                args = json.loads(args)
                            args['start_time'] = datetime.datetime.fromisoformat(args['start_time'])
                            args['end_time'] = datetime.datetime.fromisoformat(args['end_time'])
                            await websocketManager.send_personal_message(conversation_id, f"Vui lòng xác nhận đăng ký hoạt động: \n{args['name']}\nTình trạng: {args['status']}\nĐịa điểm: {args['location']}\nBắt đầu: {args['start_time'].strftime('%d-%m-%Y %H:%M')}\nKết thúc: {args['end_time'].strftime('%d-%m-%Y %H:%M')}", type="approval", tool_call_id=approval.tool_call_id)
                            # await websocketManager.send_personal_message(conversation_id, f"Vui lòng xác nhận đăng ký hoạt động: \n{args['name']}\nTình trạng: {args['status']}\nĐịa điểm: {args['location']}\nBắt đầu: {args['start_time']}\nKết thúc: {args['end_time']}", type="approval", tool_call_id=approval.tool_call_id)

                    else:
                        await websocketManager.send_personal_message(conversation_id, f"Final result: {event}", type="end")

                    message = event.result.new_messages()
                    if student_context:
                        logfire.info(f"Saving conversation and Set Cache for conversation_id: {conversation_id}. Message: {message}")
                        await conversation_service.save_conversation(conversation_id, message, history, student_id=student_context.student_id)
                    else:
                        logfire.info(f"Set Cache only for guest conversation_id: {conversation_id}. Message: {message}")
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