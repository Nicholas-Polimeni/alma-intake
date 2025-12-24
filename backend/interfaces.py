from pydantic import BaseModel, EmailStr
from enum import Enum
from datetime import datetime
from typing import Optional


class LeadState(str, Enum):
    PENDING = "PENDING"
    REACHED_OUT = "REACHED_OUT"

class Lead(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    resume_s3_key: str
    resume_url: Optional[str] = None
    state: LeadState
    created_at: datetime
    updated_at: datetime

class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr

class LeadStateUpdate(BaseModel):
    state: LeadState

class LeadListResponse(BaseModel):
    leads: list[Lead]
    total: int
    skip: int
    limit: int
