from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DialogueRequest(BaseModel):
    session_id: str
    user_input: str


class DialogueResponse(BaseModel):
    session_id: str
    agent_response: str
    next_action: Optional[Dict[str, Any]] = None


class ContentCreationRequest(BaseModel):
    topic: str
    user_preferences: str


class ContentCreationResponse(BaseModel):
    draft_content: str
    status: str
    error_message: Optional[str] = None


class QualityControlRequest(BaseModel):
    topic: str
    draft_content: str


class QualityControlResponse(BaseModel):
    final_post: str
    qa_report: Dict[str, Any]
    status: str
