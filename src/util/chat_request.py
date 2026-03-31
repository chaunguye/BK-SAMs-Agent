from dataclasses import dataclass
import uuid
from datetime import datetime

from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str

@dataclass
class ActivityDetails:
    id: uuid.UUID
    name: str
    location: str
    status: str
    description: str
    start_time: datetime
    end_time: datetime