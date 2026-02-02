"""
认证路由模块;

处理登录、Token 获取和用户管理;
"""
from datetime import timedelta
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.api.v1 import dependencies
from app.core import security
from app.core.config import settings
from app.core.database import get_session
from app.models import User

router = APIRouter()

@router.post("/login/access-token")
def login_access_token(
    session: Session = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 兼容的 Token 登录接口;
    """
    # 1. Check Admin (Priority)
    if form_data.username == settings.security.ADMIN_USER:
        if form_data.password == settings.security.ADMIN_PASSWORD: # Simple Env Check
             access_token_expires = timedelta(minutes=settings.security.ACCESS_TOKEN_EXPIRE_MINUTES)
             return {
                "access_token": security.create_access_token(
                    data={"sub": form_data.username, "role": "admin"}, expires_delta=access_token_expires
                ),
                "token_type": "bearer",
            }
    
    # 2. Check DB User
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.security.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            data={"sub": user.username, "role": "user"}, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }




@router.get("/users/me")
def read_users_me(
    current_user: dict = Depends(dependencies.get_current_user),
) -> Any:
    """
    获取当前用户信息;
    """
    return current_user
