from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from typing import Optional
import uuid
from fastapi import Header
from dotenv import load_dotenv
import jwt
import logfire

load_dotenv()

security = HTTPBearer()

class StudentContext:
    def __init__(self, student_id: uuid.UUID, student_name: Optional[str] = None):
        self.student_id = student_id
        self.student_name = student_name

async def get_student_context(authorization: Optional[str] = Header(None, alias="Authorization")) -> Optional[StudentContext]:
    if authorization is None:
        logfire.info("No Authorization header provided. Returning None for student context.")
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        student_id = payload.get("user_id")
        student_info = payload.get("user_info", {}) 
        first_name = student_info.get("first_name")
        last_name = student_info.get("last_name")
        student_name = f"{last_name} {first_name}".strip() if first_name or last_name else None
        if student_id is None:
            return None
        return StudentContext(student_id=student_id, student_name=student_name)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except (jwt.PyJWTError, ValueError):
        return None

def verify_jwt (credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[StudentContext]:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        student_id = payload.get("user_id")
        user_info = payload.get("user_info")
        first_name = user_info.get("first_name") if user_info else None
        last_name = user_info.get("last_name") if user_info else None
        student_name = f"{last_name} {first_name}".strip() if first_name or last_name else None
        if student_id is None:
            raise HTTPException(status_code=401, detail="Invalid token. Please try in again.")
        return StudentContext(student_id=student_id, student_name=student_name)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token. Please try in again.")

def get_student_context_by_token(token: str):
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        student_id = payload.get("user_id")
        user_info = payload.get("user_info")
        first_name = user_info.get("first_name") if user_info else None
        last_name = user_info.get("last_name") if user_info else None
        student_name = f"{last_name} {first_name}".strip() if first_name or last_name else None
        
        if student_id is None:
            return None
        return StudentContext(student_id=student_id, student_name=student_name)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except (jwt.PyJWTError, ValueError):
        return None