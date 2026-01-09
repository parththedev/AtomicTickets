from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from src.db.session import Base # Import Base from the correct file

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    total_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    tickets_left: Mapped[int] = mapped_column(Integer, nullable=False) # Separate total from left is smart for stats
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False) # Keeping it simple (no User table for now)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending") # pending, confirmed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())