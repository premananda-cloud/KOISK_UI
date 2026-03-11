"""
src/api/water/router.py
=======================
Water department endpoints.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.department.database.database import get_db
from src.department.database.models import WaterConsumer, User
from src.payment.mock_payment_engine import svc_complete, svc_initiate
from src.api.shared.schemas import SuccessResponse
from src.api.shared.utils import save_request

router = APIRouter(prefix="/api/v1/water", tags=["Water"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class WaterPayBillRequest(BaseModel):
    user_id:         str
    consumer_number: str
    billing_period:  str
    amount:          float
    payment_method:  str
    gateway:         str = "mock"


class WaterConnectionRequest(BaseModel):
    applicant_name: str
    applicant_id:   str
    address:        str
    property_type:  str
    identity_proof: str
    address_proof:  str


class WaterLeakComplaintRequest(BaseModel):
    consumer_id:     str
    consumer_number: str
    complaint_type:  str
    location:        str
    severity:        str
    description:     Optional[str] = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/bills/{user_id}")
async def water_get_bills(user_id: str, db: Session = Depends(get_db)):
    consumers = db.query(WaterConsumer).join(User).filter(User.username == user_id).all()
    bills = []
    for c in consumers:
        if c.outstanding_amount > 0:
            bills.append({
                "id":         f"BILL-WATER-{c.consumer_number}",
                "dept":       "water",
                "consumerNo": c.consumer_number,
                "amountDue":  c.outstanding_amount,
                "billMonth":  datetime.utcnow().strftime("%Y-%m"),
                "dueDate":    (datetime.utcnow() + timedelta(days=10)).strftime("%Y-%m-%d"),
                "status":     "UNPAID",
            })
    return {"userId": user_id, "bills": bills}


@router.post("/pay-bill", response_model=SuccessResponse)
async def water_pay_bill(req: WaterPayBillRequest, db: Session = Depends(get_db)):
    internal_id = str(uuid.uuid4())

    pay_result = await svc_initiate(
        internal_id=internal_id, user_id=req.user_id,
        bill_id=f"BILL-WATER-{req.consumer_number}-{req.billing_period}",
        department="water", amount=req.amount,
        method=req.payment_method, gateway=req.gateway, db=db,
        consumer_number=req.consumer_number, billing_period=req.billing_period,
    )

    complete_result = {}
    if pay_result.get("isMock"):
        complete_result = await svc_complete(
            payment_id=internal_id, order_id=pay_result["orderId"],
            gateway="mock", gateway_payment_id=f"pay_mock_{uuid.uuid4().hex[:10]}", db=db,
        )

    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="water", stype="WATER_PAY_BILL",
        status_str="DELIVERED" if pay_result.get("isMock") else "SUBMITTED",
        payload=req.dict(), payment_id=internal_id,
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="water", status=row.status,
        message="Water bill payment processed",
        data=complete_result.get("receipt") or pay_result,
    )


@router.post("/new-connection", response_model=SuccessResponse)
async def water_new_connection(req: WaterConnectionRequest, db: Session = Depends(get_db)):
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="water", stype="WATER_CONNECTION_REQUEST",
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="water", status=row.status,
        message="Connection request submitted",
    )


@router.post("/leak-complaint", response_model=SuccessResponse)
async def water_leak_complaint(req: WaterLeakComplaintRequest, db: Session = Depends(get_db)):
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="water", stype="WATER_LEAK_COMPLAINT",
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="water", status=row.status,
        message="Leak complaint submitted. Team will attend shortly.",
    )
