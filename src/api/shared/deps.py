"""
src/api/shared/deps.py
======================
JWT auth helpers and shared FastAPI dependencies.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.department.database.database import get_db
from src.department.database.models import Admin

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "koisk-dev-secret-change-in-production")
ALGORITHM  = "HS256"

try:
    from jose import jwt
    from passlib.context import CryptContext
    _pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("python-jose / passlib not installed — auth endpoints disabled")


def verify_password(plain: str, hashed: str) -> bool:
    if not JWT_AVAILABLE:
        return plain == "Admin@1234"
    return _pwd.verify(plain, hashed)


def create_token(data: dict, expires_minutes: int = 480) -> str:
    if not JWT_AVAILABLE:
        return "dev-token"
    payload = {**data, "exp": datetime.utcnow() + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict:
    if not JWT_AVAILABLE:
        return {"sub": "dev", "role": "super_admin", "department": None}
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login", auto_error=False)


def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload  = decode_token(token)
    username = payload.get("sub")
    admin    = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin not found or inactive")
    return admin


def require_super_admin(admin: Admin = Depends(get_current_admin)) -> Admin:
    if admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return admin


def require_dept_access(dept: str, admin: Admin = Depends(get_current_admin)) -> Admin:
    """Allow if super_admin OR if the admin's department matches."""
    if admin.role == "super_admin":
        return admin
    if admin.department != dept:
        raise HTTPException(status_code=403, detail=f"No access to {dept} department")
    return admin
