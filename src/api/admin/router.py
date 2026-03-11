"""
src/api/admin/router.py
=======================
Admin auth, request management, merchant setup, and kiosk-config endpoints.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.department.database.database import get_db
from src.department.database.models import Admin, Payment, ServiceRequest as ServiceRequestModel, KioskConfig
from src.api.shared.deps import (
    verify_password, create_token,
    get_current_admin, require_super_admin,
)
from src.api.shared.utils import to_response

router = APIRouter(tags=["Admin"])


# ─── Auth ─────────────────────────────────────────────────────────────────────

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         str
    department:   Optional[str]
    admin_id:     int


@router.post("/admin/login", response_model=AdminLoginResponse)
async def admin_login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   Session = Depends(get_db),
):
    """Authenticate an admin/department officer and return a JWT."""
    admin = db.query(Admin).filter(Admin.username == form.username).first()
    if not admin or not verify_password(form.password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_token({"sub": admin.username, "role": admin.role, "department": admin.department})
    admin.last_login = datetime.utcnow()
    db.commit()

    return AdminLoginResponse(
        access_token=token, role=admin.role,
        department=admin.department, admin_id=admin.id,
    )


# ─── Service Request Management ───────────────────────────────────────────────

@router.get("/admin/requests")
async def admin_list_all_requests(
    department: Optional[str] = None,
    status:     Optional[str] = None,
    limit:      int = 50,
    offset:     int = 0,
    admin:      Admin = Depends(get_current_admin),
    db:         Session = Depends(get_db),
):
    """List all service requests. Dept-admin sees only their department."""
    q = db.query(ServiceRequestModel)

    if admin.role != "super_admin" and admin.department:
        q = q.filter(ServiceRequestModel.department == admin.department)
    elif department:
        q = q.filter(ServiceRequestModel.department == department)

    if status:
        q = q.filter(ServiceRequestModel.status == status.upper())

    total = q.count()
    rows  = q.order_by(ServiceRequestModel.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total":    total,
        "limit":    limit,
        "offset":   offset,
        "requests": [to_response(r) for r in rows],
    }


@router.get("/admin/requests/{request_id}")
async def admin_get_request(
    request_id: str,
    admin:      Admin = Depends(get_current_admin),
    db:         Session = Depends(get_db),
):
    row = db.query(ServiceRequestModel).filter(
        ServiceRequestModel.service_request_id == request_id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")
    if admin.role != "super_admin" and admin.department and row.department != admin.department:
        raise HTTPException(status_code=403, detail="Access denied")
    return to_response(row)


class AdminUpdateStatusBody(BaseModel):
    status:        str
    note:          Optional[str] = None
    error_code:    Optional[str] = None
    error_message: Optional[str] = None


@router.patch("/admin/requests/{request_id}/status")
async def admin_update_request_status(
    request_id: str,
    body:       AdminUpdateStatusBody,
    admin:      Admin = Depends(get_current_admin),
    db:         Session = Depends(get_db),
):
    """Approve, deny, mark in-progress, or deliver a service request."""
    row = db.query(ServiceRequestModel).filter(
        ServiceRequestModel.service_request_id == request_id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")
    if admin.role != "super_admin" and admin.department and row.department != admin.department:
        raise HTTPException(status_code=403, detail="Access denied")

    row.status           = body.status.upper()
    row.handled_by_admin = admin.id
    row.updated_at       = datetime.utcnow()
    if body.error_code:
        row.error_code    = body.error_code
    if body.error_message:
        row.error_message = body.error_message
    if row.status in ("DELIVERED", "FAILED", "CANCELLED"):
        row.completed_at = datetime.utcnow()

    db.commit()
    return {"success": True, "service_request_id": request_id, "new_status": row.status}


@router.get("/admin/payments")
async def admin_list_payments(
    department: Optional[str] = None,
    status:     Optional[str] = None,
    limit:      int = 50,
    offset:     int = 0,
    admin:      Admin = Depends(get_current_admin),
    db:         Session = Depends(get_db),
):
    """View payment records. Scoped to admin's department automatically."""
    q = db.query(Payment)
    if admin.role != "super_admin" and admin.department:
        q = q.filter(Payment.department == admin.department)
    elif department:
        q = q.filter(Payment.department == department)
    if status:
        q = q.filter(Payment.status == status.lower())

    total = q.count()
    rows  = q.order_by(Payment.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total":    total,
        "payments": [
            {
                "id":          r.id,
                "userId":      r.user_id,
                "dept":        r.department,
                "amount":      float(r.amount),
                "status":      r.status,
                "gateway":     r.gateway,
                "method":      r.payment_method,
                "referenceNo": r.reference_no,
                "consumerNo":  r.consumer_number,
                "paidAt":      r.paid_at.isoformat() if r.paid_at else None,
                "createdAt":   r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


# ─── Merchant Setup ───────────────────────────────────────────────────────────

class MerchantSetupBody(BaseModel):
    gateway:     str
    merchant_id: str
    channel_key: Optional[str] = None
    api_key:     Optional[str] = None
    notes:       Optional[str] = None


@router.post("/admin/merchant/setup")
async def admin_merchant_setup(
    body:  MerchantSetupBody,
    admin: Admin = Depends(get_current_admin),
    db:    Session = Depends(get_db),
):
    """
    Store merchant payment gateway config for this admin/department.
    Super-admins can configure org-wide; dept-admins configure their own department.
    """
    config = {
        "gateway":        body.gateway,
        "merchant_id":    body.merchant_id,
        "channel_key":    body.channel_key,
        "notes":          body.notes,
        "configured_at":  datetime.utcnow().isoformat(),
    }
    if body.api_key:
        config["api_key_hint"] = f"****{body.api_key[-4:]}"

    admin.merchant_config = config
    admin.role = "merchant" if admin.role == "department_admin" else admin.role
    db.commit()

    return {
        "success":     True,
        "admin_id":    admin.id,
        "department":  admin.department,
        "gateway":     body.gateway,
        "merchant_id": body.merchant_id,
        "message":     "Merchant payment config saved successfully",
    }


@router.get("/admin/merchant/config")
async def admin_get_merchant_config(
    admin: Admin = Depends(get_current_admin),
):
    """Return the merchant's stored payment configuration (api keys obfuscated)."""
    cfg = admin.merchant_config or {}
    return {
        "admin_id":      admin.id,
        "department":    admin.department,
        "role":          admin.role,
        "gateway":       cfg.get("gateway"),
        "merchant_id":   cfg.get("merchant_id"),
        "channel_key":   cfg.get("channel_key"),
        "configured_at": cfg.get("configured_at"),
    }


# ─── Kiosk Config ─────────────────────────────────────────────────────────────

class KioskConfigSetRequest(BaseModel):
    department:          str
    razorpay_key_id:     Optional[str]  = None
    razorpay_key_secret: Optional[str]  = None
    razorpay_mode:       Optional[str]  = "test"
    is_active:           Optional[bool] = None
    settings:            Optional[Dict[str, Any]] = None


class KioskConfigResponse(BaseModel):
    department:           str
    razorpay_key_id_hint: Optional[str]
    razorpay_mode:        Optional[str]
    is_active:            bool
    settings:             Dict[str, Any]
    configured_at:        Optional[str]


def _cfg_to_response(cfg: KioskConfig) -> KioskConfigResponse:
    return KioskConfigResponse(
        department           = cfg.department,
        razorpay_key_id_hint = cfg.razorpay_key_id_hint,
        razorpay_mode        = cfg.razorpay_mode,
        is_active            = cfg.is_active,
        settings             = cfg.settings or {},
        configured_at        = cfg.updated_at.isoformat() if cfg.updated_at else None,
    )


@router.post("/admin/kiosk-config", response_model=KioskConfigResponse)
async def admin_set_kiosk_config(
    body:  KioskConfigSetRequest,
    admin: Admin = Depends(require_super_admin),
    db:    Session = Depends(get_db),
):
    """
    Set or update Razorpay keys and kiosk settings for a department.
    Only super_admins may call this endpoint.
    """
    valid_departments = {"water", "electricity", "municipal", "global"}
    if body.department not in valid_departments:
        raise HTTPException(
            status_code=400,
            detail=f"department must be one of {sorted(valid_departments)}",
        )

    cfg = db.query(KioskConfig).filter(KioskConfig.department == body.department).first()
    if not cfg:
        cfg = KioskConfig(department=body.department)
        db.add(cfg)

    if body.razorpay_key_id is not None:
        cfg.razorpay_key_id      = body.razorpay_key_id
        cfg.razorpay_key_id_hint = (
            f"****{body.razorpay_key_id[-4:]}"
            if len(body.razorpay_key_id) >= 4
            else body.razorpay_key_id
        )

    if body.razorpay_key_secret is not None:
        cfg.razorpay_key_secret = body.razorpay_key_secret

    if body.razorpay_mode is not None:
        if body.razorpay_mode not in ("test", "live"):
            raise HTTPException(status_code=400, detail="razorpay_mode must be 'test' or 'live'")
        cfg.razorpay_mode = body.razorpay_mode

    if body.is_active is not None:
        cfg.is_active = body.is_active

    if body.settings:
        cfg.settings = {**(cfg.settings or {}), **body.settings}

    cfg.configured_by_admin = admin.id
    cfg.updated_at          = datetime.utcnow()
    db.commit()
    db.refresh(cfg)

    return _cfg_to_response(cfg)


@router.get("/admin/kiosk-config")
async def admin_get_kiosk_config(
    admin: Admin = Depends(require_super_admin),
    db:    Session = Depends(get_db),
):
    """Return all department kiosk configs (Razorpay keys obfuscated)."""
    rows = db.query(KioskConfig).order_by(KioskConfig.department).all()
    return {"configs": [_cfg_to_response(r) for r in rows]}


@router.get("/admin/kiosk-config/{department}", response_model=KioskConfigResponse)
async def admin_get_kiosk_config_dept(
    department: str,
    admin:      Admin = Depends(require_super_admin),
    db:         Session = Depends(get_db),
):
    """Get config for a single department."""
    cfg = db.query(KioskConfig).filter(KioskConfig.department == department).first()
    if not cfg:
        raise HTTPException(status_code=404, detail=f"No config found for department '{department}'")
    return _cfg_to_response(cfg)
