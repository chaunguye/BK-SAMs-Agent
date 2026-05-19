import tempfile

from google.genai import types

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from fastapi import UploadFile, BackgroundTasks, HTTPException
import boto3
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
    
    chunk_service = get_chunk_service()
    document = await chunk_service.get_document_by_activity_id(activity_id)

    if document is not None:
        await chunk_service.delete_document_by_activity_id(activity_id)

    # Generate unique document ID and S3 key
    doc_id = str(uuid.uuid4())
    s3_key = f"documents/{doc_id}_{file.filename}"

    # Upload file to S3
    s3_bucket = os.getenv("AWS_S3_BUCKET")
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )
    file_content = await file.read()
    s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body=file_content)

    # Insert document to database (store S3 key as file path)
    chunkRepo = await get_chunk_repo()
    await chunkRepo.insert_document(doc_id, s3_key, suffix, student_context.student_name, file.filename, activity_id)

    # Process document in background (Parsing, chunking, embedding, storing chunks)
    background_tasks.add_task(get_chunk_service().process, s3_key, doc_id)

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

@router.get("")
async def get_uploaded_document(activity_id: str,
                                student_context: StudentContext = Depends(verify_jwt)):
    if student_context is None:
        raise HTTPException(status_code=401, detail="Unauthorized. Guest cannot access documents.")

    chunkService = get_chunk_service()
    document = await chunkService.get_document_by_activity_id(activity_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return JSONResponse({"file_name": document["file_name"], "file_type": document["file_type"], "author": document["author"], "created_at": str(document["created_at"]), "updated_at": str(document["updated_at"]), "file_size": document["file_size"]})

@router.delete("")
async def delete_uploaded_document(activity_id: str,
                                   student_context: StudentContext = Depends(verify_jwt)):
    if student_context is None:
        raise HTTPException(status_code=401, detail="Unauthorized. Guest cannot delete documents.")

    chunk_service = get_chunk_service()
    await chunk_service.delete_document_by_activity_id(activity_id)
    return JSONResponse({"status": "deleted"})

@router.get("/activity")
async def get_activity(activity_id: str,
                       student_context: StudentContext = Depends(verify_jwt)):
    if student_context is None:
        raise HTTPException(status_code=401, detail="Unauthorized. Guest cannot access activities.")

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

def cleanup_local_file(file_path: str):
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"[Cleanup] Đã xóa file tạm cục bộ: {file_path}")
        except Exception as e:
            print(f"[Cleanup Lỗi] Không thể xóa file {file_path}: {e}")

@router.get("/download")
async def download_activity_document(
    activity_id: str,
    background_tasks: BackgroundTasks,
    student_context: StudentContext = Depends(verify_jwt)):

    if student_context is None:
        raise HTTPException(status_code=401, detail="Unauthorized. Guest cannot download documents.")
    
    chunkService = get_chunk_service()
    document = await chunkService.get_document_by_activity_id(activity_id)
    
    if not document or not document.get("file_path"):
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu cho hoạt động này.")

    s3_key = document["file_path"]
    original_name = document["file_name"] # Original filename
    
    file_extension = os.path.splitext(original_name)[1]

    try:
        temp_fd, temp_path = tempfile.mkstemp(suffix=file_extension)
        os.close(temp_fd) 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khởi tạo file temp trên server hệ thống: {e}")

    # 3. Tải file từ AWS S3 về file tạm vừa tạo
    s3_bucket = os.getenv("AWS_S3_BUCKET")
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )
    try:
        s3_client.download_file(s3_bucket, s3_key, temp_path)
    except Exception as e:
        cleanup_local_file(temp_path)
        if e.response['Error']['Code'] == "404":
            raise HTTPException(status_code=404, detail="File không tồn tại trên hệ thống lưu trữ S3.")
        raise HTTPException(status_code=500, detail="Lỗi khi tải file từ S3 về máy chủ.")

    # 4. Đăng ký tác vụ dọn dẹp file vào BackgroundTasks
    # FastAPI sẽ chạy hàm này NGAY SAU KHI data được gửi trả về cho client thành công
    background_tasks.add_task(cleanup_local_file, temp_path)

    # 5. Trả file về cho người dùng 
    return FileResponse(
        path=temp_path,
        media_type="application/octet-stream", # Ép trình duyệt phải download thay vì preview
        filename=original_name # Tên file hiển thị khi user tải về máy
    )

@router.put("")
async def update_uploaded_document(activity_id: str, file: UploadFile, background_tasks: BackgroundTasks, 
                                  student_context: StudentContext = Depends(verify_jwt)):
    if student_context is None:
        raise HTTPException(status_code=401, detail="Unauthorized. Guest cannot update documents.")
    # To be implemented: Update document record and re-process the document (delete old chunks, insert new chunks)
    return JSONResponse({"status": "update endpoint to be implemented"})