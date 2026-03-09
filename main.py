import uuid
from fastapi import FastAPI, BackgroundTasks, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
from src.rag.processing import get_document_processor
from src.repository.chunk_repo import get_chunk_repo
import aiofiles
import logfire
from src.agents.agent import capstone_agent, AgentConfig

app = FastAPI()
# app.mount("/chat", agent.to_web())  # Mount the agent's web interface at /chat

logfire.configure()
logfire.instrument_pydantic_ai()
logfire.instrument_fastapi(app)

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

@app.post("/chat")
async def chat_with_agent(message: str):
    """This endpoint is used to send a message to the agent and get a response."""

    deps = AgentConfig(document_processor=get_document_processor())
    response = await capstone_agent.run(message, deps=deps)
    return JSONResponse({"response": response.output})

@app.get("/test_query")
async def test_query(query: str):
    """This endpoint is used to test the search functionality of the document processor."""
    document_processor = get_document_processor()
    results = await document_processor.search_chunk_by_query(query)
    return JSONResponse({"results": [result['text_content'] for result in results]})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
