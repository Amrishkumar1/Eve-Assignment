from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Booking, BookingStatus, Payment, PaymentStatus, User
from app.schemas import PaymentCreate, PaymentResponse, PaymentWebhook

router = APIRouter(prefix="/payments", tags=["Payments"])

def process_payment_event(db: Session, booking: Booking, event_id: str, payment_status: PaymentStatus, amount):
    existing = db.query(Payment).filter(Payment.provider_event_id == event_id).first()
    if existing:
        if existing.booking_id != booking.id or existing.status != payment_status or existing.amount != amount:
            raise HTTPException(status_code=409, detail="Event ID was already used with different data")
        return existing
    if booking.amount != amount:
        raise HTTPException(status_code=400, detail="Payment amount does not match booking")
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=409, detail="Cancelled booking cannot be paid")
    if booking.status in (BookingStatus.CONFIRMED, BookingStatus.FAILED):
        raise HTTPException(status_code=409, detail="Booking has already reached a final payment state")
    payment = Payment(booking_id=booking.id, status=payment_status, amount=amount, provider_event_id=event_id)
    db.add(payment)
    booking.status = BookingStatus.CONFIRMED if payment_status == PaymentStatus.SUCCESS else BookingStatus.FAILED
    db.commit()
    db.refresh(payment)
    return payment

@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_mock_payment(payload: PaymentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if booking is None or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    payment = process_payment_event(db, booking, f"mock-payment-{booking.id}", payload.simulate_status, booking.amount)
    return payment

@router.post("/webhook/", response_model=PaymentResponse)
def payment_webhook(payload: PaymentWebhook, db: Session = Depends(get_db), x_webhook_secret: str | None = Header(default=None)):
    if not settings.jwt_secret_key or x_webhook_secret != settings.jwt_secret_key:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return process_payment_event(db, booking, payload.event_id, payload.status, payload.amount)
