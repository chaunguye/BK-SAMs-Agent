from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from src.service.chunk_service import get_chunk_service
from src.repository.chunk_repo import get_chunk_repo
import logfire
from src.api import chat, rag



app = FastAPI()
app.include_router(rag.router)
app.include_router(chat.router)

logfire.configure()
logfire.instrument_pydantic_ai()
logfire.instrument_fastapi(app)

@app.get("/")
def read_root():
    return {"message": "Welcome to BK-SAMs Agent API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
