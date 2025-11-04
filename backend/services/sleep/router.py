from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from backend.common import models
from backend.common.database import get_db
from backend.common.schemas import MessageResponse, SleepMonthlyStatsResponse, SleepRecordResponse, SleepStatsResponse

router = APIRouter(prefix="/sleep", tags=["sleep"])


class SleepRecordPayload(BaseModel):
    email: EmailStr
    sleep_time: datetime
    wake_time: datetime


@router.post("/records", response_model=MessageResponse)
def save_sleep_record(payload: SleepRecordPayload, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    sleep_time = payload.sleep_time
    wake_time = payload.wake_time
    if sleep_time >= wake_time:
        wake_time += timedelta(days=1)

    duration = (wake_time - sleep_time).total_seconds() / 3600

    existing_record = (
        db.query(models.SleepRecord)
        .filter(
            models.SleepRecord.email == user.email,
            extract("year", models.SleepRecord.sleep_time) == sleep_time.year,
            extract("month", models.SleepRecord.sleep_time) == sleep_time.month,
            extract("day", models.SleepRecord.sleep_time) == sleep_time.day,
        )
        .first()
    )

    if existing_record:
        if sleep_time > existing_record.sleep_time:
            existing_record.sleep_time = sleep_time
            existing_record.wake_time = wake_time
            existing_record.duration = duration
            db.commit()
            db.refresh(existing_record)
            return MessageResponse(message="Sleep record updated successfully")
        return MessageResponse(message="Older sleep record ignored; existing record is more recent")

    new_record = models.SleepRecord(
        email=user.email,
        sleep_time=sleep_time,
        wake_time=wake_time,
        duration=duration,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return MessageResponse(message="Sleep record saved successfully")


@router.get("/records/{email}", response_model=List[SleepRecordResponse])
def list_sleep_records(email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    sleep_records = (
        db.query(models.SleepRecord)
        .filter(models.SleepRecord.email == email)
        .order_by(models.SleepRecord.sleep_time.desc())
        .all()
    )
    if not sleep_records:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sleep records found")

    latest_per_day: Dict[datetime.date, models.SleepRecord] = {}
    for record in sleep_records:
        record_date = record.sleep_time.date()
        latest_per_day.setdefault(record_date, record)

    response: List[SleepRecordResponse] = []
    for record in latest_per_day.values():
        duration = record.wake_time - record.sleep_time
        formatted_duration = f"{duration.seconds // 3600} jam {duration.seconds % 3600 // 60} menit"
        formatted_time = f"{record.sleep_time.strftime('%H:%M')} - {record.wake_time.strftime('%H:%M')}"
        formatted_date = record.sleep_time.strftime('%d %B %Y')
        response.append(
            SleepRecordResponse(
                date=formatted_date,
                duration=formatted_duration,
                time=formatted_time,
            )
        )
    return response


@router.get("/weekly/{email}", response_model=SleepStatsResponse)
def get_weekly_stats(
    email: str,
    start_date: datetime = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: datetime = Query(..., description="End date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
):
    end_date_inclusive = end_date + timedelta(days=2)
    sleep_records = (
        db.query(models.SleepRecord)
        .filter(
            models.SleepRecord.email == email,
            models.SleepRecord.sleep_time >= start_date,
            models.SleepRecord.wake_time <= end_date_inclusive,
        )
        .order_by(models.SleepRecord.sleep_time.desc())
        .all()
    )

    if not sleep_records:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sleep records found for the week")

    latest_per_day: Dict[datetime.date, models.SleepRecord] = {}
    for record in sleep_records:
        record_date = record.sleep_time.date()
        latest_per_day.setdefault(record_date, record)

    daily_sleep_durations = {i: timedelta() for i in range(7)}
    daily_sleep_start_times: Dict[int, list[str]] = {i: [] for i in range(7)}
    daily_wake_times: Dict[int, list[str]] = {i: [] for i in range(7)}

    for record in latest_per_day.values():
        adjusted_wake = record.wake_time
        if adjusted_wake < record.sleep_time:
            adjusted_wake += timedelta(days=1)

        duration = adjusted_wake - record.sleep_time
        day_of_week = record.sleep_time.weekday()
        daily_sleep_durations[day_of_week] += duration
        daily_sleep_start_times[day_of_week].append(record.sleep_time.strftime("%H:%M"))
        daily_wake_times[day_of_week].append(adjusted_wake.strftime("%H:%M"))

    daily_hours = [round(daily_sleep_durations[i].total_seconds() / 3600, 2) for i in range(7)]
    total_duration = sum(daily_hours)

    avg_duration = total_duration / len(latest_per_day)
    avg_sleep_time = sum(
        (
            timedelta(hours=int(time[:2]), minutes=int(time[3:]))
            for times in daily_sleep_start_times.values()
            for time in times
        ),
        timedelta(),
    ) / len(latest_per_day)
    avg_wake_time = sum(
        (
            timedelta(hours=int(time[:2]), minutes=int(time[3:]))
            for times in daily_wake_times.values()
            for time in times
        ),
        timedelta(),
    ) / len(latest_per_day)

    return SleepStatsResponse(
        daily_sleep_durations=daily_hours,
        daily_sleep_start_times=daily_sleep_start_times,
        daily_wake_times=daily_wake_times,
        avg_duration=f"{int(avg_duration)} jam {int((avg_duration * 60) % 60)} menit",
        avg_sleep_time=(datetime.min + avg_sleep_time).strftime("%H:%M"),
        avg_wake_time=(datetime.min + avg_wake_time).strftime("%H:%M"),
        total_duration=f"{int(total_duration)} jam {int((total_duration * 60) % 60)} menit",
    )


@router.get("/monthly/{email}", response_model=SleepMonthlyStatsResponse)
def get_monthly_stats(email: str, month: int, year: int, db: Session = Depends(get_db)):
    start_date = datetime(year, month, 1)
    next_month = start_date.replace(day=28) + timedelta(days=4)
    end_date = next_month - timedelta(days=next_month.day)

    sleep_records = (
        db.query(models.SleepRecord)
        .filter(
            models.SleepRecord.email == email,
            models.SleepRecord.sleep_time >= start_date,
            models.SleepRecord.wake_time < end_date + timedelta(days=1),
        )
        .order_by(models.SleepRecord.sleep_time.desc())
        .all()
    )

    if not sleep_records:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sleep records found for the month")

    latest_per_day: Dict[datetime.date, models.SleepRecord] = {}
    for record in sleep_records:
        record_date = record.sleep_time.date()
        latest_per_day.setdefault(record_date, record)

    weekly_sleep_durations = {i: timedelta() for i in range(4)}
    weekly_sleep_start_times: Dict[int, list[str]] = {i: [] for i in range(4)}
    weekly_wake_times: Dict[int, list[str]] = {i: [] for i in range(4)}

    days_in_month = (end_date - start_date).days + 1
    daily_sleep_durations = [0.0] * days_in_month

    for record in latest_per_day.values():
        adjusted_wake = record.wake_time
        if adjusted_wake < record.sleep_time:
            adjusted_wake += timedelta(days=1)

        duration = adjusted_wake - record.sleep_time
        day_of_month = (record.sleep_time - start_date).days
        daily_sleep_durations[day_of_month] = round(duration.total_seconds() / 3600, 2)

        week_of_month = min(day_of_month // 7, 3)
        weekly_sleep_durations[week_of_month] += duration
        weekly_sleep_start_times[week_of_month].append(record.sleep_time.strftime("%H:%M"))
        weekly_wake_times[week_of_month].append(adjusted_wake.strftime("%H:%M"))

    weekly_hours = [round(weekly_sleep_durations[i].total_seconds() / 3600, 2) for i in range(4)]
    total_duration = sum(weekly_hours)
    avg_duration = total_duration / len(latest_per_day)

    sleep_minutes = []
    for times in weekly_sleep_start_times.values():
        for time in times:
            hours, minutes = map(int, time.split(":"))
            if hours < 12:
                hours += 24
            sleep_minutes.append(hours * 60 + minutes)

    avg_sleep_minutes = sum(sleep_minutes) / len(sleep_minutes)
    avg_sleep_hours = int(avg_sleep_minutes // 60)
    avg_sleep_minute = int(avg_sleep_minutes % 60)

    wake_minutes = []
    for times in weekly_wake_times.values():
        for time in times:
            hours, minutes = map(int, time.split(":"))
            wake_minutes.append(hours * 60 + minutes)

    avg_wake_minutes = sum(wake_minutes) / len(wake_minutes)
    avg_wake_hours = int(avg_wake_minutes // 60)
    avg_wake_minute = int(avg_wake_minutes % 60)

    return SleepMonthlyStatsResponse(
        weekly_sleep_durations=weekly_hours,
        weekly_sleep_start_times=weekly_sleep_start_times,
        weekly_wake_times=weekly_wake_times,
        daily_sleep_durations=daily_sleep_durations,
        avg_duration=f"{int(avg_duration)} jam {int((avg_duration * 60) % 60)} menit",
        avg_sleep_time=f"{avg_sleep_hours:02d}:{avg_sleep_minute:02d}",
        avg_wake_time=f"{avg_wake_hours:02d}:{avg_wake_minute:02d}",
        total_duration=f"{int(total_duration)} jam {int((total_duration * 60) % 60)} menit",
    )
