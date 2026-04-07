from dataclasses import dataclass
import uuid
from src.service.chunk_service import ChunkService
from src.service.activity_service import ActivityService

@dataclass
class AgentConfig:
    chunk_service: ChunkService
    student_id: uuid.UUID
    activity_service: ActivityService
    student_name: str