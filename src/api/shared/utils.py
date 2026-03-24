"""
src/api/shared/utils.py
=======================
Shared DB helpers used by all department routers.
"""

import logging
from typing import Dict, Optional

from sqlalchemy.orm import Session

from src.department.database.models import ServiceRequest as ServiceRequestModel
from src.api.shared.schemas import ServiceStatusResponse

logger = logging.getLogger(__name__)


def save_request(
    db:         Session,
    req_id:     str,
    dept:       str,
    stype:      str,
    status_str: str,
    payload:    Dict,
    user_id:    Optional[int] = None,
    payment_id: Optional[str] = None,
) -> ServiceRequestModel:
    row = ServiceRequestModel(
        service_request_id=req_id,
        department=dept,
        service_type=stype,
        status=status_str,
        payload=payload,
        user_id=user_id,
        payment_id=payment_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(f"[DB] Saved request {req_id}  dept={dept}  type={stype}  status={status_str}")
    return row


def to_response(row: ServiceRequestModel) -> ServiceStatusResponse:
    return ServiceStatusResponse(
        service_request_id=row.service_request_id,
        department=row.department,
        service_type=row.service_type,
        status=row.status,
        payload=row.payload or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
        error_code=row.error_code,
        error_message=row.error_message,
        payment_id=row.payment_id,
    )
