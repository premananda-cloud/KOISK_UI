"""
src/api/kiosk/router.py
=======================
Kiosk department catalogue, OTP session management, and session validation.
"""

import hashlib
import logging
import os
import random
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.department.database.database import get_db
from src.department.database.models import KioskConfig, KioskSession
from src.payment.payment_handler import (
    RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,
    create_razorpay_customer_with_key,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Kiosk"])

# ─── Constants ────────────────────────────────────────────────────────────────

OTP_EXPIRY_SECONDS  = int(os.getenv("OTP_EXPIRY_SECS",  "300"))
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECS", "1800"))
MAX_OTP_ATTEMPTS    = 3

# ─── OTP helpers ──────────────────────────────────────────────────────────────

def _generate_otp() -> str:
    return f"{random.SystemRandom().randint(0, 999999):06d}"


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def _new_session_token() -> str:
    return secrets.token_urlsafe(32)


def _send_otp_sms(phone: str, otp: str) -> None:
    """Stub — replace with real SMS provider (Twilio / MSG91 / Fast2SMS)."""
    logger.info(f"[OTP] ☎  Sending OTP {otp} to {phone}  (integrate SMS provider here)")


def _get_dept_razorpay_keys(db: Session, department: str) -> tuple[str, str]:
    cfg = db.query(KioskConfig).filter(KioskConfig.department == department).first()
    if cfg and cfg.razorpay_key_id and cfg.razorpay_key_secret:
        return cfg.razorpay_key_id, cfg.razorpay_key_secret
    return RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET


# ─── Department Catalogue ─────────────────────────────────────────────────────

_DEPARTMENT_CATALOGUE: Dict[str, Dict] = {
    "water": {
        "label":       "Water",
        "icon":        "💧",
        "description": "Water supply & utilities",
        "services": [
            {"id": "WATER_PAY_BILL",                  "label": "Pay Bill",             "has_payment": True},
            {"id": "WATER_CONNECTION_REQUEST",         "label": "New Connection",        "has_payment": False},
            {"id": "WATER_METER_CHANGE",               "label": "Meter Change",          "has_payment": False},
            {"id": "WATER_LEAK_COMPLAINT",             "label": "Report Leak",           "has_payment": False},
            {"id": "WATER_METER_READING_SUBMISSION",   "label": "Submit Meter Reading",  "has_payment": False},
            {"id": "WATER_COMPLAINT_GRIEVANCE",        "label": "Complaint / Grievance", "has_payment": False},
        ],
    },
    "electricity": {
        "label":       "Electricity",
        "icon":        "⚡",
        "description": "Electricity supply & metering",
        "services": [
            {"id": "ELECTRICITY_PAY_BILL",                "label": "Pay Bill",             "has_payment": True},
            {"id": "ELECTRICITY_CONNECTION_REQUEST",       "label": "New Connection",        "has_payment": False},
            {"id": "ELECTRICITY_METER_CHANGE",             "label": "Meter Change",          "has_payment": False},
            {"id": "ELECTRICITY_SERVICE_TRANSFER",         "label": "Transfer Service",      "has_payment": False},
            {"id": "ELECTRICITY_METER_READING_SUBMISSION", "label": "Submit Meter Reading",  "has_payment": False},
            {"id": "ELECTRICITY_COMPLAINT",                "label": "Complaint / Grievance", "has_payment": False},
        ],
    },
    "municipal": {
        "label":       "Municipal",
        "icon":        "🏛️",
        "description": "Municipal services & certificates",
        "services": [
            {"id": "MUNICIPAL_PROPERTY_TAX_PAYMENT",  "label": "Pay Property Tax",       "has_payment": True},
            {"id": "MUNICIPAL_TRADE_LICENSE_NEW",      "label": "New Trade License",      "has_payment": False},
            {"id": "MUNICIPAL_TRADE_LICENSE_RENEWAL",  "label": "Renew Trade License",    "has_payment": False},
            {"id": "MUNICIPAL_BIRTH_CERTIFICATE",      "label": "Birth Certificate",      "has_payment": False},
            {"id": "MUNICIPAL_DEATH_CERTIFICATE",      "label": "Death Certificate",      "has_payment": False},
            {"id": "MUNICIPAL_BUILDING_PLAN_APPROVAL", "label": "Building Plan Approval", "has_payment": False},
            {"id": "MUNICIPAL_SANITATION_COMPLAINT",   "label": "Sanitation Complaint",   "has_payment": False},
            {"id": "MUNICIPAL_GENERAL_GRIEVANCE",      "label": "General Grievance",      "has_payment": False},
        ],
    },
}


@router.get("/kiosk/departments")
async def kiosk_list_departments(db: Session = Depends(get_db)):
    """
    Return all active departments and their service lists.
    Active status comes from kiosk_config; defaults to True if no config row exists yet.
    """
    configs    = {row.department: row for row in db.query(KioskConfig).all()}
    global_cfg = configs.get("global")
    result     = []

    for dept_key, catalogue in _DEPARTMENT_CATALOGUE.items():
        cfg     = configs.get(dept_key)
        is_active = cfg.is_active if cfg else True
        result.append({
            "id":                  dept_key,
            "label":               catalogue["label"],
            "icon":                catalogue["icon"],
            "description":         catalogue["description"],
            "is_active":           is_active,
            "razorpay_configured": bool(cfg and cfg.razorpay_key_id),
            "razorpay_mode":       cfg.razorpay_mode if cfg else "test",
            "services":            catalogue["services"] if is_active else [],
        })

    return {
        "departments":   result,
        "kiosk_settings": global_cfg.settings if global_cfg else {},
    }


# ─── Session Schemas ──────────────────────────────────────────────────────────

class KioskSessionStartRequest(BaseModel):
    full_name:    str
    phone_number: str
    email:        Optional[str] = None
    kiosk_id:     Optional[str] = None


class KioskSessionStartResponse(BaseModel):
    session_id:        int
    is_returning_user: bool
    otp_sent:          bool
    message:           str


class KioskOTPVerifyRequest(BaseModel):
    session_id: int
    otp_code:   str


class KioskOTPVerifyResponse(BaseModel):
    success:              bool
    session_token:        str
    razorpay_customer_id: Optional[str]
    full_name:            str
    is_returning_user:    bool
    message:              str


class KioskSessionEndRequest(BaseModel):
    session_token: str


# ─── Session Routes ───────────────────────────────────────────────────────────

@router.post("/kiosk/session/start", response_model=KioskSessionStartResponse)
async def kiosk_session_start(req: KioskSessionStartRequest, db: Session = Depends(get_db)):
    """
    Step 1 of the user flow.
    Looks up existing session by phone number to determine returning vs new user.
    Sends OTP via SMS (stubbed — replace with real provider).
    """
    existing = (
        db.query(KioskSession)
        .filter(
            KioskSession.phone_number == req.phone_number,
            KioskSession.is_verified  == True,  # noqa: E712
        )
        .order_by(KioskSession.started_at.desc())
        .first()
    )

    otp = _generate_otp()

    if existing:
        session = KioskSession(
            full_name            = req.full_name or existing.full_name,
            phone_number         = req.phone_number,
            email                = req.email or existing.email,
            otp_code             = _hash_otp(otp),
            otp_sent_at          = datetime.utcnow(),
            otp_attempts         = 0,
            is_verified          = False,
            razorpay_customer_id = existing.razorpay_customer_id,
            is_returning_user    = True,
            kiosk_id             = req.kiosk_id,
        )
    else:
        session = KioskSession(
            full_name         = req.full_name,
            phone_number      = req.phone_number,
            email             = req.email,
            otp_code          = _hash_otp(otp),
            otp_sent_at       = datetime.utcnow(),
            otp_attempts      = 0,
            is_verified       = False,
            is_returning_user = False,
            kiosk_id          = req.kiosk_id,
        )

    db.add(session)
    db.commit()
    db.refresh(session)
    _send_otp_sms(req.phone_number, otp)

    return KioskSessionStartResponse(
        session_id        = session.id,
        is_returning_user = session.is_returning_user,
        otp_sent          = True,
        message           = (
            "Welcome back! OTP sent to your registered number."
            if session.is_returning_user else
            "OTP sent to your phone number."
        ),
    )


@router.post("/kiosk/session/verify-otp", response_model=KioskOTPVerifyResponse)
async def kiosk_session_verify_otp(req: KioskOTPVerifyRequest, db: Session = Depends(get_db)):
    """
    Step 2 of the user flow.
    Validates OTP, creates Razorpay customer for new users, issues session_token.
    """
    session = db.query(KioskSession).filter(KioskSession.id == req.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.is_verified:
        raise HTTPException(status_code=400, detail="Session already verified")

    if session.otp_sent_at:
        age = (datetime.utcnow() - session.otp_sent_at).total_seconds()
        if age > OTP_EXPIRY_SECONDS:
            raise HTTPException(status_code=400, detail="OTP has expired. Please restart.")

    if session.otp_attempts >= MAX_OTP_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Please restart the session.")

    if session.otp_code != _hash_otp(req.otp_code):
        session.otp_attempts += 1
        db.commit()
        remaining = MAX_OTP_ATTEMPTS - session.otp_attempts
        raise HTTPException(status_code=400, detail=f"Incorrect OTP. {remaining} attempt(s) remaining.")

    # OTP correct — create Razorpay customer if new user
    razorpay_customer_id = session.razorpay_customer_id

    if not razorpay_customer_id:
        key_id, key_secret = "", ""
        for dept in ("water", "electricity", "municipal"):
            key_id, key_secret = _get_dept_razorpay_keys(db, dept)
            if key_id:
                break
        try:
            razorpay_customer_id = await create_razorpay_customer_with_key(
                name       = session.full_name,
                contact    = session.phone_number,
                email      = session.email or "",
                key_id     = key_id,
                key_secret = key_secret,
                notes      = {"source": "koisk_kiosk", "phone": session.phone_number},
            )
            logger.info(f"[kiosk] Razorpay customer created: {razorpay_customer_id}")
        except ValueError as exc:
            logger.error(f"[kiosk] Razorpay customer creation failed: {exc}")
            razorpay_customer_id = None

    token      = _new_session_token()
    expires_at = datetime.utcnow() + timedelta(seconds=SESSION_TTL_SECONDS)

    session.is_verified          = True
    session.otp_verified_at      = datetime.utcnow()
    session.razorpay_customer_id = razorpay_customer_id
    session.session_token        = token
    session.session_expires_at   = expires_at
    db.commit()

    return KioskOTPVerifyResponse(
        success              = True,
        session_token        = token,
        razorpay_customer_id = razorpay_customer_id,
        full_name            = session.full_name,
        is_returning_user    = session.is_returning_user,
        message              = "Identity verified. Welcome to SUVIDHA Kiosk.",
    )


@router.post("/kiosk/session/end")
async def kiosk_session_end(req: KioskSessionEndRequest, db: Session = Depends(get_db)):
    """Called when user taps Done / Exit. Invalidates session token."""
    session = db.query(KioskSession).filter(KioskSession.session_token == req.session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.ended_at      = datetime.utcnow()
    session.session_token = None
    db.commit()
    return {"success": True, "message": "Session ended. Goodbye!"}


@router.get("/kiosk/session/validate")
async def kiosk_session_validate(session_token: str, db: Session = Depends(get_db)):
    """Lightweight token check called before any service request."""
    session = (
        db.query(KioskSession)
        .filter(
            KioskSession.session_token == session_token,
            KioskSession.is_verified   == True,  # noqa: E712
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    if session.ended_at:
        raise HTTPException(status_code=401, detail="Session has ended")
    if session.session_expires_at and datetime.utcnow() > session.session_expires_at:
        raise HTTPException(status_code=401, detail="Session has expired")

    return {
        "valid":                True,
        "full_name":            session.full_name,
        "phone_number":         session.phone_number,
        "razorpay_customer_id": session.razorpay_customer_id,
        "is_returning_user":    session.is_returning_user,
        "session_expires_at":   session.session_expires_at.isoformat(),
    }
