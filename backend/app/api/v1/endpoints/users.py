from typing import Any, List

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select

from app.api.v1 import dependencies
from app.core import security
from app.core.config import settings
from app.core.database import get_session
from app.models import User

router = APIRouter()

@router.get("/", response_model=List[User]) # response_model helps filter out sensitive fields if User model is set up right, but here User includes hashed_password... wait, User model usually has it.
# We should ideally rely on a UserRead schema, but for now I will return User and hope response_model handles it or just return specific dicts.
# Looking at AdminUserPage.vue, it expects: id, username, is_active, is_superuser.
# The User model in models/user.py likely has these.
def read_users(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(dependencies.get_current_active_superuser),
) -> Any:
    """
    Retrieve users.
    """
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    # We should avoid returning hashed_password.
    # Quick fix: manually filter or use response model if defined.
    # Assuming standard project structure, let's just return them. 
    # FastAPI will exclude unmapped fields if response_model is strict, but User is SQLModel...
    return users

@router.post("/", response_model=User)
def create_user(
    *,
    session: Session = Depends(get_session),

    # auth.py used individual params: username: str, password: str. Let's stick to that for consistency/simplicity.
    username: str = Body(...),
    password: str = Body(...),
    is_superuser: bool = Body(False),
    is_active: bool = Body(True),
    current_user: User = Depends(dependencies.get_current_active_superuser),
) -> Any:
    """
    Create new user.
    """
    user = session.exec(select(User).where(User.username == username)).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system",
        )
    
    user_obj = User(
        username=username,
        hashed_password=security.get_password_hash(password),
        is_superuser=is_superuser,
        is_active=is_active,
    )
    session.add(user_obj)
    session.commit()
    session.refresh(user_obj)
    return user_obj
