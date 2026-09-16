from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(subject=str(user.id)),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    email = payload.email.lower()

    existing = (
        await db.execute(select(User).where(func.lower(User.email) == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(
        email=email,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    return _token_for(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = (
        await db.execute(select(User).where(func.lower(User.email) == payload.email.lower()))
    ).scalar_one_or_none()

    # Same response whether the email is unknown or the password is wrong, so
    # the endpoint is not a user-enumeration oracle.
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    return _token_for(user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
