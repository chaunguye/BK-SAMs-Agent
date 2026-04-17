from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi import UploadFile, BackgroundTasks, HTTPException
import aiofiles
import uuid
from src.service.chunk_service import get_chunk_service
from src.repository.chunk_repo import get_chunk_repo
from src.middleware.authorization import StudentContext, verify_jwt
import os
from fastapi import Depends


router = APIRouter(prefix="/upload", tags=["RAG Document Upload"])

@router.post("")
async def upload_document(file: UploadFile, background_tasks: BackgroundTasks, 
                          student_context: StudentContext = Depends(verify_jwt),
                          activity_id: str = None):
    
    if student_context is None:
        raise HTTPException(status_code=401, detail="Unauthorized. Guest cannot upload documents.")
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
    await chunkRepo.insert_document(doc_id, file_path, suffix, student_context.student_name, file.filename, activity_id)

    # Process document in background (Parsing, chunking, embedding, storing chunks)
    
    background_tasks.add_task(get_chunk_service().process, file_path, doc_id)

    return JSONResponse({"status": "parsed", "filename": file.filename, "document_id": doc_id})
