"""
src/api/electricity/router.py
==============================
Electricity department endpoints.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.department.database.database import get_db
from src.department.database.models import ElectricityMeter, User
from src.payment.mock_payment_engine import svc_complete, svc_initiate
from src.api.shared.schemas import SuccessResponse
from src.api.shared.utils import save_request

router = APIRouter(prefix="/api/v1/electricity", tags=["Electricity"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ElectricityPayBillRequest(BaseModel):
    user_id:        str
    meter_number:   str
    billing_period: str
    amount:         float
    payment_method: str
    gateway:        str = "mock"


class ElectricityTransferRequest(BaseModel):
    old_customer_id: str
    new_customer_id: str
    meter_number:    str
    identity_proof:  str
    ownership_proof: str
    consent_doc:     str
    effective_date:  str


class ElectricityMeterChangeRequest(BaseModel):
    user_id:          str
    meter_number:     str
    reason:           str
    new_meter_number: Optional[str] = None


class ElectricityConnectionRequest(BaseModel):
    customer_name:    str
    customer_id:      str
    address:          str
    load_requirement: str
    identity_proof:   str
    address_proof:    str


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/bills/{user_id}")
async def electricity_get_bills(user_id: str, db: Session = Depends(get_db)):
    """Return pending bills for a user's electricity meter."""
    meters = db.query(ElectricityMeter).join(User).filter(User.username == user_id).all()
    bills  = []
    for m in meters:
        if m.outstanding_amount > 0:
            bills.append({
                "id":         f"BILL-ELEC-{m.meter_number}",
                "dept":       "electricity",
                "consumerNo": m.meter_number,
                "amountDue":  m.outstanding_amount,
                "billMonth":  datetime.utcnow().strftime("%Y-%m"),
                "dueDate":    (datetime.utcnow() + timedelta(days=10)).strftime("%Y-%m-%d"),
                "status":     "UNPAID",
            })
    return {"userId": user_id, "bills": bills}


@router.post("/pay-bill", response_model=SuccessResponse)
async def electricity_pay_bill(req: ElectricityPayBillRequest, db: Session = Depends(get_db)):
    internal_id = str(uuid.uuid4())

    pay_result = await svc_initiate(
        internal_id=internal_id,
        user_id=req.user_id,
        bill_id=f"BILL-ELEC-{req.meter_number}-{req.billing_period}",
        department="electricity",
        amount=req.amount,
        method=req.payment_method,
        gateway=req.gateway,
        db=db,
        consumer_number=req.meter_number,
        billing_period=req.billing_period,
    )

    complete_result = {}
    if pay_result.get("isMock"):
        complete_result = await svc_complete(
            payment_id=internal_id,
            order_id=pay_result["orderId"],
            gateway="mock",
            gateway_payment_id=f"pay_mock_{uuid.uuid4().hex[:10]}",
            db=db,
        )

    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="electricity", stype="ELECTRICITY_PAY_BILL",
        status_str="DELIVERED" if pay_result.get("isMock") else "SUBMITTED",
        payload={
            "user_id": req.user_id, "meter_number": req.meter_number,
            "billing_period": req.billing_period, "amount": req.amount,
            "payment_method": req.payment_method,
        },
        payment_id=internal_id,
    )

    return SuccessResponse(
        success=True,
        service_request_id=row.service_request_id,
        department="electricity",
        status=row.status,
        message="Bill payment processed",
        data=complete_result.get("receipt") or pay_result,
    )


@router.post("/transfer-service", response_model=SuccessResponse)
async def electricity_transfer_service(req: ElectricityTransferRequest, db: Session = Depends(get_db)):
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="electricity", stype="ELECTRICITY_SERVICE_TRANSFER",
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="electricity", status=row.status,
        message="Transfer request submitted. Awaiting department approval.",
    )


@router.post("/meter-change", response_model=SuccessResponse)
async def electricity_meter_change(req: ElectricityMeterChangeRequest, db: Session = Depends(get_db)):
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="electricity", stype="ELECTRICITY_METER_CHANGE",
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="electricity", status=row.status,
        message="Meter change request submitted",
    )


@router.post("/new-connection", response_model=SuccessResponse)
async def electricity_new_connection(req: ElectricityConnectionRequest, db: Session = Depends(get_db)):
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="electricity", stype="ELECTRICITY_CONNECTION_REQUEST",
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="electricity", status=row.status,
        message="New connection request submitted",
    )
