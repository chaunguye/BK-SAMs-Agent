import uuid
from fastapi import FastAPI, BackgroundTasks, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
from src.rag.processing import DocumentProcessor
from src.repository.chunk_repo import initialize_chunk_repo

app = FastAPI()

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
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Insert document to database
    chunkRepo = await initialize_chunk_repo()
    await chunkRepo.insert_document(doc_id, file_path, suffix, "anonymous")

    # Process document in background (Parsing, chunking, embedding, storing chunks)
    background_tasks.add_task(DocumentProcessor.process, file_path, doc_id)

    return JSONResponse({"status": "parsed", "filename": file.filename, "document_id": doc_id})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
