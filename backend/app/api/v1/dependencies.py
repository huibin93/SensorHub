"""
API 依赖注入模块;
"""
from typing import Generator, Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.api.v1.endpoints import dictionaries # Hack to ensure models are loaded? No, use app.models
from app.models import User
# from app.core.security import SecurityConfig # Removed incorrect import

# OAuth2 Scheme
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

def get_current_user(
    session: Session = Depends(get_session),
    token: str = Depends(reusable_oauth2)
) -> Dict[str, Any]:
    """
    获取当前用户;
    
    验证 JWT Token 并从数据库查询用户(包括admin);
    返回包含 username 和 is_superuser 的字典;
    """
    try:
        payload = jwt.decode(
            token, settings.security.SECRET_KEY, algorithms=[settings.security.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    # 统一从数据库查询用户(包括admin)
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return {
        "username": user.username,
        "is_superuser": user.is_superuser,
        "id": user.id
    }


def get_current_active_superuser(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    仅允许管理员访问;
    """
    if not current_user["is_superuser"]:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
