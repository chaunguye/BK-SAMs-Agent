from fastapi import HTTPException
import os
from typing import Optional
import uuid
from fastapi import Header
from dotenv import load_dotenv
import jwt

load_dotenv()

class StudentContext:
    def __init__(self, student_id: str, student_name: Optional[str] = None):
        self.student_id = student_id
        self.student_name = student_name

async def get_student_context(authorization: Optional[str] = Header(None)):
    if authorization is None:
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        student_id = payload.get("sub")
        student_name = payload.get("student_name")
        if student_id is None:
            return None
        return StudentContext(student_id=student_id, student_name=student_name)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except (jwt.PyJWTError, ValueError):
        return None

def verify_jwt (authorization: Optional[str] = Header(None)) -> Optional[StudentContext]:
    if authorization is None:
        raise HTTPException(status_code=401, detail="Authorization header missing. Please log in.")
    scheme, token = authorization.split()
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization scheme. Please use Bearer token.")
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        student_id = payload.get("sub")
        student_name = payload.get("student_name")
        if student_id is None:
            raise HTTPException(status_code=401, detail="Invalid token. Please try in again.")
        return StudentContext(student_id=student_id, student_name=student_name)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token. Please try in again.")