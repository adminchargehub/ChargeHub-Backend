import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if creds is None:
        raise _CREDENTIALS_ERROR

    payload = decode_access_token(creds.credentials)
    if payload is None:
        raise _CREDENTIALS_ERROR

    subject = payload.get("sub")
    if not subject:
        raise _CREDENTIALS_ERROR
    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise _CREDENTIALS_ERROR from None

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    """Route dependency enforcing RBAC, e.g. `Depends(require_roles(UserRole.ADMIN))`."""

    async def _check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return user

    return _check
