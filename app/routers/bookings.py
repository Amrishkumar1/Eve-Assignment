from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Booking, BookingStatus, CentreTest, DiagnosticCentre, User
from app.schemas import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["Bookings"])

def booking_to_response(booking: Booking):
    return BookingResponse(id=booking.id, user_id=booking.user_id, centre_id=booking.centre_test.centre_id, test_id=booking.centre_test.test_id, appointment_at=booking.appointment_at, amount=booking.amount, status=booking.status)

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    centre = db.get(DiagnosticCentre, payload.centre_id)
    if centre is None or not centre.is_active:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")
    centre_test = db.query(CentreTest).filter(CentreTest.centre_id == payload.centre_id, CentreTest.test_id == payload.test_id).first()
    if centre_test is None:
        raise HTTPException(status_code=404, detail="Test is not offered by this centre")
    booking = Booking(user_id=user.id, centre_test_id=centre_test.id, appointment_at=payload.appointment_at, amount=centre_test.price, status=BookingStatus.PENDING)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking_to_response(booking)

@router.get("/", response_model=list[BookingResponse])
def list_my_bookings(limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bookings = db.query(Booking).options(joinedload(Booking.centre_test)).filter(Booking.user_id == user.id).order_by(Booking.id.desc()).offset(offset).limit(limit).all()
    return [booking_to_response(b) for b in bookings]

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    booking = db.query(Booking).options(joinedload(Booking.centre_test)).filter(Booking.id == booking_id).first()
    if booking is None or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking_to_response(booking)

@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    booking = db.query(Booking).options(joinedload(Booking.centre_test)).filter(Booking.id == booking_id).first()
    if booking is None or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=409, detail="Only pending bookings can be cancelled")
    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking_to_response(booking)
