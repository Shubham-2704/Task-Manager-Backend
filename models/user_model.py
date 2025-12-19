from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timezone 

class Timestamps(BaseModel):
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    profileImageUrl: Optional[str] = None
    adminInviteToken: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    profileImageUrl: Optional[str]
    role: str
    token: str

class UserUpdate(BaseModel):
    profileImageUrl: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    newPassword: str
