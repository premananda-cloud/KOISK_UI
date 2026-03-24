"""
src/api/shared/schemas.py
=========================
Common Pydantic response models shared across all routers.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ServiceStatusResponse(BaseModel):
    service_request_id: str
    department:         str
    service_type:       str
    status:             str
    payload:            Dict[str, Any] = {}
    created_at:         datetime
    updated_at:         datetime
    completed_at:       Optional[datetime] = None
    error_code:         Optional[str]      = None
    error_message:      Optional[str]      = None
    payment_id:         Optional[str]      = None


class SuccessResponse(BaseModel):
    success:            bool
    service_request_id: str
    department:         str
    status:             str
    message:            Optional[str]           = None
    data:               Optional[Dict[str, Any]] = None
