import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UtcDateTime, UUIDMixin


class BookingStatus(StrEnum):
    PENDING = "pending"        # created, awaiting payment
    CONFIRMED = "confirmed"    # paid, not yet started
    ACTIVE = "active"          # running on the station
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"        # never redeemed before the window closed


class Plan(UUIDMixin, TimestampMixin, Base):
    """Tariff plan. Replaces the legacy `plan1`/`plan2`/`plan3` tables."""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)

    # Real, dimensioned units.
    power_cap_w: Mapped[int] = mapped_column(Integer, nullable=False)
    energy_cap_wh: Mapped[int] = mapped_column(Integer, nullable=False)
    max_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    price_kobo: Mapped[int] = mapped_column(Integer, nullable=False)

    # Customer-facing guidance, carried over from the prototype's plan→device
    # mapping (Starter/Lamps, Premium/Phones, Plus/Laptops, Pro Plus/all).
    recommended_devices: Mapped[str | None] = mapped_column(String(160), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Plan {self.slug}>"


class Booking(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_booking_window_valid"),
        # Drives the availability query.
        Index("ix_booking_outlet_window", "outlet_id", "starts_at", "ends_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    outlet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outlets.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )

    starts_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)

    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, name="booking_status"),
        default=BookingStatus.PENDING,
        nullable=False,
        index=True,
    )

    outlet: Mapped["object"] = relationship("Outlet", lazy="selectin")
    plan: Mapped[Plan] = relationship(lazy="selectin")

    #: Statuses that occupy an outlet for availability purposes.
    BLOCKING = (BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.ACTIVE)

    def __repr__(self) -> str:
        return f"<Booking {self.id} {self.status.value}>"
