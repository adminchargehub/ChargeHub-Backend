import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    """A timestamp that is always timezone-aware UTC on the way in and out.

    PostgreSQL `timestamptz` round-trips tzinfo; SQLite does not, and returns a
    naive datetime. Without this, the same code silently compares aware and
    naive datetimes depending on the backend and raises TypeError. Legacy rows
    migrated from the 2017 MySQL schema are naive too, so we normalise rather
    than trust the driver.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime rejected — pass an aware UTC datetime")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def utcnow() -> datetime:
    """Always timezone-aware UTC.

    The legacy platform compared naive local-time strings with PHP date()
    output, which is why session expiry was only ever approximately right.
    Every timestamp in this schema is tz-aware and stored as UTC.
    """
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
