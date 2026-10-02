
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app import models
from app.routers import auth, centres, bookings, payments


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="EVE Healthcare Diagnostic Booking API",
    version="1.0.0",
    description=(
        "SDE Intern assignment: diagnostic bookings "
        "and simulated payments."
    ),
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(centres.router)
app.include_router(bookings.router)
app.include_router(payments.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
