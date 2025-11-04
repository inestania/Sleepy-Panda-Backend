from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.common import models
from backend.common.config import settings
from backend.common.database import get_db
from backend.common.schemas import MessageResponse, Token
from backend.common.security import create_access_token, decode_access_token, get_password_hash, verify_password

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
_otp_store: Dict[str, Dict[str, datetime]] = {}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OtpRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str


def send_email_otp(destination: str, otp: str) -> None:
    sender = settings.require(settings.email_sender, "EMAIL_SENDER is not configured.")
    password = settings.require(settings.email_password, "EMAIL_PASSWORD is not configured.")

    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = destination
    message["Subject"] = "Your OTP Code"
    message.attach(MIMEText(f"Your OTP code is {otp}. It is valid for 5 minutes.", "plain"))

    with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, destination, message.as_string())


@router.post("/register", response_model=Token)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    db_user = models.User(email=payload.email, hashed_password=get_password_hash(payload.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    token = create_access_token({"sub": db_user.email})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": user.email})
    return Token(access_token=token)


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password tidak valid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": user.email})
    return Token(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
def logout(_: str = Depends(oauth2_scheme)):
    # Stateless JWT logout - handled client-side by discarding token
    return MessageResponse(message="Logout successful")


@router.post("/request-otp", response_model=MessageResponse)
def request_otp(payload: OtpRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    otp = secrets.token_hex(3)
    expiry = datetime.utcnow() + timedelta(minutes=5)
    _otp_store[payload.email] = {"otp": otp, "expiry": expiry}

    send_email_otp(payload.email, otp)
    return MessageResponse(message="OTP sent to your email")


@router.post("/verify-otp", response_model=MessageResponse)
def verify_otp(payload: VerifyOtpRequest):
    data = _otp_store.get(payload.email)
    if not data or data["otp"] != payload.otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")
    if data["expiry"] < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired")
    return MessageResponse(message="OTP verified")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return MessageResponse(message="Password successfully reset")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    try:
        payload = decode_access_token(token)
    except HTTPException:
       
        raise
    except JWTError as exc: 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    return user
