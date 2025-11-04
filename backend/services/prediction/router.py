from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Dict

import joblib
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.common import models
from backend.common.config import settings
from backend.common.database import get_db
from backend.common.schemas import MessageResponse

router = APIRouter(prefix="/predictions", tags=["predictions"])

ML_DIR = settings.ml_model_dir
MODEL_PATH = ML_DIR / "xgb_model_Test.pkl"
SCALER_PATH = ML_DIR / "minmax_scaler_split.pkl"


def _ensure_artifact(path: Path) -> Path:
    if not path.exists():
        raise RuntimeError(f"Missing ML artifact: {path}")
    return path


model = joblib.load(_ensure_artifact(MODEL_PATH))
scaler = joblib.load(_ensure_artifact(SCALER_PATH))

PREDICTION_MAPPING: Dict[int, str] = {
    0: "Insomnia",
    1: "Normal",
    2: "Sleep Apnea",
}


class PredictionRequest(BaseModel):
    email: EmailStr


class PredictionSaveRequest(BaseModel):
    email: EmailStr
    prediction_result: int


class PredictionResponse(BaseModel):
    prediction: str


class WeeklyPredictionResponse(BaseModel):
    weekly_prediction: str


class WeeklyPredictionSaveRequest(BaseModel):
    email: EmailStr
    prediction_result: int


class MonthlyPredictionRequest(BaseModel):
    email: EmailStr


class MonthlyPredictionResponse(BaseModel):
    monthly_prediction: str


@router.post("/run", response_model=PredictionResponse)
def run_prediction(payload: PredictionRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    sleep_record = db.query(models.SleepRecord).filter(models.SleepRecord.email == payload.email).first()
    work_data = db.query(models.Work).filter(models.Work.email == payload.email).first()

    if not sleep_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incomplete data for prediction (missing sleep record)")
    if not work_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incomplete data for prediction (missing work data)")

    age = user.age or 0
    gender = user.gender or 0
    occupation = work_data.work_id or 0
    bmi_category = 0
    quality_of_sleep = work_data.quality_of_sleep or 0
    physical_activity_level = work_data.physical_activity_level or 0
    stress_level = work_data.stress_level or 0
    heart_rate = user.heart_rate or 0
    daily_step = user.daily_steps or 0
    systolic = user.upper_pressure or 0
    diastolic = user.lower_pressure or 0
    sleep_duration = sleep_record.duration or 0
    additional_feature = 0

    numerical_features = [
        age,
        sleep_duration,
        quality_of_sleep,
        physical_activity_level,
        stress_level,
        heart_rate,
        daily_step,
        systolic,
        diastolic,
        additional_feature,
    ]

    complete_features = np.zeros((1, 12))
    complete_features[0, :10] = numerical_features
    scaled_features = scaler.transform(complete_features).flatten()

    features = np.array(
        [
            gender,
            scaled_features[0],
            occupation,
            scaled_features[1],
            scaled_features[2],
            scaled_features[3],
            scaled_features[4],
            bmi_category,
            scaled_features[5],
            scaled_features[6],
            scaled_features[7],
            scaled_features[8],
        ]
    ).reshape(1, -1)

    prediction_value = int(model.predict(features)[0])
    prediction_label = PREDICTION_MAPPING.get(prediction_value, "Unknown")

    today = date.today()
    daily_record = (
        db.query(models.Daily)
        .filter(models.Daily.email == payload.email, models.Daily.date == today)
        .first()
    )

    if daily_record:
        daily_record.prediction_result = prediction_value
        daily_record.upper_pressure = systolic
        daily_record.lower_pressure = diastolic
        daily_record.daily_steps = daily_step
        daily_record.heart_rate = heart_rate
        daily_record.duration = sleep_duration
    else:
        db.add(
            models.Daily(
                email=payload.email,
                date=today,
                upper_pressure=systolic,
                lower_pressure=diastolic,
                daily_steps=daily_step,
                heart_rate=heart_rate,
                duration=sleep_duration,
                prediction_result=prediction_value,
            )
        )

    db.commit()
    return PredictionResponse(prediction=prediction_label)


@router.post("/save", response_model=MessageResponse)
def save_prediction(payload: PredictionSaveRequest, db: Session = Depends(get_db)):
    today = date.today()
    daily_record = (
        db.query(models.Daily)
        .filter(models.Daily.email == payload.email, models.Daily.date == today)
        .first()
    )

    if daily_record:
        daily_record.prediction_result = payload.prediction_result
    else:
        db.add(
            models.Daily(
                email=payload.email,
                date=today,
                prediction_result=payload.prediction_result,
            )
        )

    db.commit()
    return MessageResponse(message="Prediction saved successfully")


@router.post("/weekly", response_model=WeeklyPredictionResponse)
def weekly_prediction(payload: PredictionRequest, db: Session = Depends(get_db)):
    today = date.today()
    seven_days_ago = today - timedelta(days=7)

    weekly_data = (
        db.query(models.Daily)
        .filter(
            models.Daily.email == payload.email,
            models.Daily.date >= seven_days_ago,
            models.Daily.date <= today,
        )
        .all()
    )

    if not weekly_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tidak ada data harian untuk seminggu terakhir.")

    counts = {0: 0, 1: 0, 2: 0}
    for record in weekly_data:
        if record.prediction_result is not None:
            counts[record.prediction_result] = counts.get(record.prediction_result, 0) + 1

    if counts[1] > counts[0] + counts[2]:
        result = "Normal"
    else:
        result = "Insomnia" if counts[0] >= counts[2] else "Sleep Apnea"

    return WeeklyPredictionResponse(weekly_prediction=result)


@router.post("/weekly/save", response_model=MessageResponse)
def save_weekly_prediction(payload: WeeklyPredictionSaveRequest, db: Session = Depends(get_db)):
    if payload.prediction_result not in PREDICTION_MAPPING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid prediction result")

    prediction = models.WeeklyPrediction(
        email=payload.email,
        prediction_result=PREDICTION_MAPPING[payload.prediction_result],
    )
    db.add(prediction)
    db.commit()
    return MessageResponse(message="Prediction saved successfully")


@router.post("/monthly", response_model=MonthlyPredictionResponse)
def monthly_prediction(payload: MonthlyPredictionRequest, db: Session = Depends(get_db)):
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    monthly_data = (
        db.query(models.Daily)
        .filter(
            models.Daily.email == payload.email,
            func.date(models.Daily.date) >= thirty_days_ago,
            func.date(models.Daily.date) <= today,
        )
        .all()
    )

    if not monthly_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tidak ada data harian untuk 30 hari terakhir.")

    counts = {0: 0, 1: 0, 2: 0}
    for record in monthly_data:
        if record.prediction_result is not None:
            counts[record.prediction_result] = counts.get(record.prediction_result, 0) + 1

    if counts[1] > counts[0] + counts[2]:
        result = "Normal"
    else:
        result = "Insomnia" if counts[0] >= counts[2] else "Sleep Apnea"

    return MonthlyPredictionResponse(monthly_prediction=result)


@router.post("/monthly/save", response_model=MessageResponse)
def save_monthly_prediction(payload: PredictionSaveRequest, db: Session = Depends(get_db)):
    if payload.prediction_result not in PREDICTION_MAPPING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid prediction result")

    prediction = models.MonthlyPrediction(
        email=payload.email,
        prediction_result=PREDICTION_MAPPING[payload.prediction_result],
    )
    db.add(prediction)
    db.commit()
    return MessageResponse(message="Monthly prediction saved successfully")
