from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.common import models
from backend.common.database import get_db
from backend.common.schemas import MessageResponse, UserResponse
from backend.services.auth.router import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


class BasicProfilePayload(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    gender: Optional[int] = None
    work: Optional[str] = None
    date_of_birth: Optional[date] = None
    height: Optional[float] = None
    weight: Optional[float] = None


class ProfileUpdatePayload(BaseModel):
    name: Optional[str] = None
    gender: Optional[int] = None
    work: Optional[str] = None
    date_of_birth: Optional[date] = None


class MetricsUpdatePayload(BaseModel):
    weight: Optional[float] = None
    height: Optional[float] = None
    upper_pressure: Optional[int] = None
    lower_pressure: Optional[int] = None
    daily_steps: Optional[int] = None
    heart_rate: Optional[int] = None


class WorkUpdatePayload(BaseModel):
    work: str


WORK_ID_MAP = {
    "Accountant": 0,
    "Doctor": 1,
    "Engineer": 2,
    "Lawyer": 3,
    "Manager": 4,
    "Nurse": 5,
    "Sales Representative": 6,
    "Salesperson": 7,
    "Scientist": 8,
    "Software Engineer": 9,
    "Teacher": 10,
}

WORK_DEFAULTS = {
    "Accountant": (7.891892, 58.108108, 4.594595),
    "Doctor": (6.647887, 55.352113, 6.732394),
    "Engineer": (8.412698, 51.857143, 3.888889),
    "Lawyer": (7.893617, 70.425532, 5.06383),
    "Manager": (7.0, 55.0, 5.0),
    "Nurse": (7.369863, 78.589041, 5.547945),
    "Sales Representative": (4.0, 30.0, 8.0),
    "Salesperson": (6.0, 45.0, 7.0),
    "Scientist": (5.0, 41.0, 7.0),
    "Software Engineer": (6.5, 48.0, 6.0),
    "Teacher": (6.975, 45.625, 4.525),
}


def _ensure_user(db: Session, email: str) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/basic", response_model=MessageResponse)
def save_basic_profile(payload: BasicProfilePayload, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()

    if user:
        for field, value in payload.dict(exclude_none=True).items():
            setattr(user, field, value)
    else:
        user = models.User(**payload.dict())
        db.add(user)

    db.commit()
    return MessageResponse(message="Data saved successfully")


@router.get("/{email}", response_model=UserResponse)
def get_user(email: str, db: Session = Depends(get_db)):
    return _ensure_user(db, email)


@router.get("/me/profile", response_model=UserResponse)
def get_my_profile(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.patch("/{email}", response_model=UserResponse)
def update_profile(email: str, payload: ProfileUpdatePayload, db: Session = Depends(get_db)):
    user = _ensure_user(db, email)

    update_data = payload.dict(exclude_none=True)
    if "date_of_birth" in update_data:
        birth_date = update_data["date_of_birth"]
        today = date.today()
        update_data["age"] = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.patch("/{email}/metrics", response_model=UserResponse)
def update_metrics(email: str, payload: MetricsUpdatePayload, db: Session = Depends(get_db)):
    user = _ensure_user(db, email)
    for field, value in payload.dict(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{email}/work", response_model=UserResponse)
def update_work(email: str, payload: WorkUpdatePayload, db: Session = Depends(get_db)):
    user = _ensure_user(db, email)
    if payload.work not in WORK_ID_MAP:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown work type")

    user.work = payload.work
    user.work_id = WORK_ID_MAP[payload.work]

    defaults = WORK_DEFAULTS[payload.work]

    work_entry = db.query(models.Work).filter(models.Work.email == user.email).first()
    if work_entry:
        work_entry.quality_of_sleep, work_entry.physical_activity_level, work_entry.stress_level = defaults
        work_entry.work_id = user.work_id
    else:
        db.add(
            models.Work(
                email=user.email,
                work_id=user.work_id,
                quality_of_sleep=defaults[0],
                physical_activity_level=defaults[1],
                stress_level=defaults[2],
            )
        )

    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: models.User = Depends(get_current_user)):
    return current_user
