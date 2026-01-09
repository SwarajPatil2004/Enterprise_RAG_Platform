from pydantic import BaseModel, Field
from typing import List, Optional, Literal

Role = Literal["admin", "member"]

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class User(BaseModel):
    user_id: int
    username: str
    tenant_id: int
    role: Role

class UploadDocRequest(BaseModel):
    title: str
    roles_allowed: List[Role] = Field(default_factory=lambda: ["member"])
    sensitive: bool = False

class ChatRequest(BaseModel):
    question: str

class Citation(BaseModel):
    doc_id: int
    title: str
    chunk_id: int
    snippet: str

class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]