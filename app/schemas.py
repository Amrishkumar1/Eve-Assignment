from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.models import BookingStatus, PaymentStatus

class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CentreTestCreate(BaseModel):
    test_name: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

class CentreCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    location: str = Field(min_length=2, max_length=255)
    tests: list[CentreTestCreate] = Field(min_length=1)

class TestAtCentreResponse(BaseModel):
    test_id: int
    test_name: str
    description: str | None
    price: Decimal

class CentreResponse(BaseModel):
    id: int
    name: str
    location: str
    tests: list[TestAtCentreResponse]

class BookingCreate(BaseModel):
    centre_id: int = Field(gt=0)
    test_id: int = Field(gt=0)
    appointment_at: datetime

    @field_validator("appointment_at")
    @classmethod
    def appointment_must_be_future(cls, value: datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("appointment_at must include a timezone, e.g. +05:30 or Z")
        if value <= datetime.now(timezone.utc):
            raise ValueError("appointment_at must be in the future")
        return value

class BookingResponse(BaseModel):
    id: int
    user_id: int
    centre_id: int
    test_id: int
    appointment_at: datetime
    amount: Decimal
    status: BookingStatus
    model_config = ConfigDict(from_attributes=True)

class PaymentCreate(BaseModel):
    booking_id: int = Field(gt=0)
    simulate_status: PaymentStatus = PaymentStatus.SUCCESS

class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    status: PaymentStatus
    amount: Decimal
    provider_event_id: str
    model_config = ConfigDict(from_attributes=True)

class PaymentWebhook(BaseModel):
    event_id: str = Field(min_length=1, max_length=180)
    booking_id: int = Field(gt=0)
    status: PaymentStatus
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
