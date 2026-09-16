from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class UserRole(StrEnum):
    CUSTOMER = "customer"
    TECHNICIAN = "technician"
    OPERATOR = "operator"
    ADMIN = "admin"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # bcrypt output is 60 chars; 255 leaves room to migrate to argon2 later.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"), default=UserRole.CUSTOMER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
