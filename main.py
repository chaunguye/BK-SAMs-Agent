from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from src.service.chunk_service import get_chunk_service
from src.repository.chunk_repo import get_chunk_repo
import logfire
from src.api import chat, rag
from src.database.database_connect import get_db_pool
from fastapi.middleware.cors import CORSMiddleware


import asyncio

app = FastAPI()
app.include_router(rag.router)
app.include_router(chat.router)

origins = ["https://bk-sams-fe.vercel.app", "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,   # Allows cookies and auth headers
    allow_methods=["*"],      # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],      # Allows all headers
)

logfire.configure()
logfire.instrument_pydantic_ai()
logfire.instrument_fastapi(app)

# Background preload of DB pool at startup
@app.on_event("startup")
async def preload_db_pool():
    try:
        await get_db_pool()
        print("[Startup] Database pool preloaded.")
    except Exception as e:
        print(f"[Warning] DB pool preload failed: {e}")

@app.get("/")
def read_root():
    return {"message": "Welcome to BK-SAMs Agent API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}



# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
