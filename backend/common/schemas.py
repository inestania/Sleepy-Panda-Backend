from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: EmailStr
    exp: int


class MessageResponse(BaseModel):
    message: str


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    gender: Optional[int] = None
    work: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    upper_pressure: Optional[int] = None
    lower_pressure: Optional[int] = None
    daily_steps: Optional[int] = None
    heart_rate: Optional[int] = None


class UserResponse(UserBase):
    class Config:
        orm_mode = True


class SleepRecordResponse(BaseModel):
    date: str
    duration: str
    time: str


class SleepStatsResponse(BaseModel):
    daily_sleep_durations: list[float]
    daily_sleep_start_times: dict[int, list[str]]
    daily_wake_times: dict[int, list[str]]
    avg_duration: str
    avg_sleep_time: str
    avg_wake_time: str
    total_duration: str


class SleepMonthlyStatsResponse(BaseModel):
    weekly_sleep_durations: list[float]
    weekly_sleep_start_times: dict[int, list[str]]
    weekly_wake_times: dict[int, list[str]]
    daily_sleep_durations: list[float]
    avg_duration: str
    avg_sleep_time: str
    avg_wake_time: str
    total_duration: str
