from google.genai import types

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi import UploadFile, BackgroundTasks, HTTPException
import aiofiles
import uuid
from src.service.chunk_service import get_chunk_service
from src.repository.chunk_repo import get_chunk_repo
from src.repository.activity_repo import get_activity_repo
from src.middleware.authorization import StudentContext, verify_jwt
import os
from fastapi import Depends
from src.testing.rag_chunks_dataset_prepare import prepare_dataset


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

    if activity_id is not None:
        activity_repo = await get_activity_repo()
        activity = await activity_repo.get_activity_by_id(activity_id)

        chunk_service = get_chunk_service()

        activity_string = f"Activity: {activity['name']}, Location: {activity['location']}, Status: {activity['status']}, Description: {activity['description']}"
        activity_embedding = await chunk_service.gemini_embedder.aio.models.embed_content(
            model="gemini-embedding-2",
            contents=activity_string,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )

        await activity_repo.update_activity_embedding(activity_id, activity_embedding.embeddings[0].values)


    return JSONResponse({"status": "parsed", "filename": file.filename, "document_id": doc_id})

@router.get("/activity")
async def get_activity(activity_id: str):
    activity_repo = await get_activity_repo()
    activity = await activity_repo.get_activity_by_id(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    else:
        chunk_service = get_chunk_service()

        activity_string = f"Activity: {activity['name']}, Location: {activity['location']}, Status: {activity['status']}, Description: {activity['description']}"
        activity_embedding = await chunk_service.gemini_embedder.aio.models.embed_content(
            model="gemini-embedding-2",
            contents=activity_string,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )

        await activity_repo.update_activity_embedding(activity_id, activity_embedding.embeddings[0].values)

    return JSONResponse({"status": "success", "activity": activity_string})


@router.get("/dataset")
async def get_dataset():
    dataset = await prepare_dataset()
    return JSONResponse({"dataset": dataset})