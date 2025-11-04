from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.common import models
from backend.common.database import get_db
from backend.common.schemas import MessageResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackPayload(BaseModel):
    email: EmailStr
    feedback: str


@router.post("", response_model=MessageResponse)
def submit_feedback(payload: FeedbackPayload, db: Session = Depends(get_db)):
    entry = models.Feedback(email=payload.email, feedback=payload.feedback, created_at=datetime.utcnow())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return MessageResponse(message="Feedback submitted successfully")
