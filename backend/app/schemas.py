from typing import Optional

from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: str
    status: str
    filename: str


class Segment(BaseModel):
    start: float
    end: float
    text: str


class AudioStatusResponse(BaseModel):
    id: str
    name: Optional[str] = None
    filename: Optional[str] = None
    status: str
    progress: float
    error: Optional[str] = None
    duration_sec: Optional[float] = None
    created_at: Optional[str] = None
    transcript: Optional[str] = None
    segments: Optional[list[Segment]] = None


class RenameRequest(BaseModel):
    name: str


class SessionListItem(BaseModel):
    id: str
    name: str
    filename: str
    status: str
    duration_sec: Optional[float] = None
    created_at: str


class ReportResponse(BaseModel):
    id: str
    report: Optional[str] = None
    error: Optional[str] = None


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    error: Optional[str] = None
