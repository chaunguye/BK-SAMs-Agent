import asyncio
import uuid
from fastapi import FastAPI, BackgroundTasks, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from src.service.activity_service import ActivityController
from util.chat_request import ChatRequest
import uvicorn
import os
from src.service.chunk_service import get_document_processor
from src.repository.chunk_repo import get_chunk_repo
import aiofiles
import logfire
from src.agents.agent import capstone_agent, AgentConfig
from fastapi import WebSocket
from src.websocket.websocketManager import WebsocketManager

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

app = FastAPI()

logfire.configure()
logfire.instrument_pydantic_ai()
logfire.instrument_fastapi(app)

websocketManager = WebsocketManager()

@app.get("/")
def read_root():
    return {"message": "Welcome to BK-SAMs API"}

@app.post("/upload")
async def upload_document(file: UploadFile, background_tasks: BackgroundTasks):

    #Check file type
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in [".docx", ".pdf"]:
        raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported.")
    
    # Generate unique document ID and file path
    doc_id = str(uuid.uuid4())
    file_path = f"documents/{doc_id}_{file.filename}"
    
    # Save file locally
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(await file.read())

    # Insert document to database
    chunkRepo = await get_chunk_repo()
    await chunkRepo.insert_document(doc_id, file_path, suffix, "anonymous", file.filename)

    # Process document in background (Parsing, chunking, embedding, storing chunks)
    
    background_tasks.add_task((get_document_processor()).process, file_path, doc_id)

    return JSONResponse({"status": "parsed", "filename": file.filename, "document_id": doc_id})

# Need optimization at singleton of AgentConfig and ActivityController, but for now we can just create new instances for each request
@app.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """This endpoint is used to send a message to the agent and get a response."""

    deps = AgentConfig(document_processor=get_document_processor(), activity_manager=ActivityController(), student_id="417aa966-52dd-4216-b823-ae0783ca05b0")
    response = await capstone_agent.run(request.message, deps=deps)
    return JSONResponse({"response": response.output})

@app.get("/test_query")
async def test_query(query: str):
    """This endpoint is used to test the search functionality of the search chunks function."""
    document_processor = get_document_processor()
    results = await document_processor.search_chunk_by_query(query)
    return JSONResponse({"results": [result['text_content'] for result in results]})

@app.websocket("/ws/chat/{student_id}")
async def websocket_endpoint(websocket: WebSocket, student_id: uuid.UUID):
    await websocketManager.connect(student_id, websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.close()
                break
            deps = AgentConfig(document_processor=get_document_processor(), activity_manager=ActivityController(), student_id=student_id)
            async for event in capstone_agent.run_stream_events(data, deps=deps):
                if isinstance(event, PartDeltaEvent):
                    await websocketManager.send_personal_message(student_id, event.delta.content, type="text")
                elif isinstance(event, FunctionToolCallEvent):
                    await websocketManager.send_personal_message(student_id, f"Calling tool: {event.part.tool_name} with args: {event.part.args}", type="tool_call")
                elif isinstance(event, FinalResultEvent):
                    await websocketManager.send_personal_message(student_id, f"Final result: {event.result}", type="final_result")
                else:
                    await websocketManager.send_personal_message(student_id, f"Received event: {event}", type="event")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        websocketManager.disconnect(student_id)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
