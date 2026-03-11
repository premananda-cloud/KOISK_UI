"""
src/api/municipal/router.py
============================
Municipal department endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.department.database.database import get_db
from src.department.database.models import MunicipalConsumer, User
from src.payment.mock_payment_engine import svc_complete, svc_initiate
from src.api.shared.schemas import SuccessResponse
from src.api.shared.utils import save_request

router = APIRouter(prefix="/api/v1/municipal", tags=["Municipal"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class MunicipalPropertyTaxRequest(BaseModel):
    user_id:         str
    consumer_number: str
    property_id:     str
    tax_year:        str
    amount:          float
    payment_method:  str
    gateway:         str = "mock"


class MunicipalTradeLicenseRequest(BaseModel):
    applicant_id:        str
    applicant_name:      str
    business_name:       str
    business_type:       str
    address:             str
    ward_number:         str
    identity_proof:      str
    address_proof:       str
    is_renewal:          bool = False
    existing_license_no: Optional[str] = None


class MunicipalBirthCertRequest(BaseModel):
    applicant_id:   str
    child_name:     str
    dob:            str
    place_of_birth: str
    father_name:    str
    mother_name:    str
    hospital_name:  Optional[str] = None
    identity_proof: str


class MunicipalDeathCertRequest(BaseModel):
    applicant_id:        str
    deceased_name:       str
    date_of_death:       str
    place_of_death:      str
    cause_of_death:      str
    informant_name:      str
    identity_proof:      str
    medical_certificate: str


class MunicipalBuildingPlanRequest(BaseModel):
    applicant_id:         str
    applicant_name:       str
    property_id:          str
    plot_area:            float
    built_up_area:        float
    floors:               int
    building_type:        str
    architect_name:       str
    identity_proof:       str
    land_ownership_proof: str
    blueprint_ref:        str


class MunicipalComplaintRequest(BaseModel):
    consumer_id:        str
    complaint_category: str
    location:           str
    ward_number:        str
    description:        str
    severity:           str = "Medium"
    photo_ref:          Optional[str] = None


class MunicipalGrievanceRequest(BaseModel):
    citizen_id:  str
    subject:     str
    description: str
    dept_ref:    Optional[str] = None
    attachment:  Optional[str] = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/bills/{user_id}")
async def municipal_get_bills(user_id: str, db: Session = Depends(get_db)):
    consumers = db.query(MunicipalConsumer).join(User).filter(User.username == user_id).all()
    bills = []
    for c in consumers:
        if c.outstanding_amount > 0:
            bills.append({
                "id":         f"BILL-MUNI-{c.consumer_number}",
                "dept":       "municipal",
                "consumerNo": c.consumer_number,
                "propertyId": c.property_id,
                "wardNumber": c.ward_number,
                "amountDue":  c.outstanding_amount,
                "taxYear":    f"{datetime.utcnow().year}-{datetime.utcnow().year + 1}",
                "status":     "UNPAID",
            })
    return {"userId": user_id, "bills": bills}


@router.post("/property-tax", response_model=SuccessResponse)
async def municipal_property_tax(req: MunicipalPropertyTaxRequest, db: Session = Depends(get_db)):
    internal_id = str(uuid.uuid4())
    pay_result = await svc_initiate(
        internal_id=internal_id, user_id=req.user_id,
        bill_id=f"BILL-MUNI-{req.property_id}-{req.tax_year}",
        department="municipal", amount=req.amount,
        method=req.payment_method, gateway=req.gateway, db=db,
        consumer_number=req.consumer_number, billing_period=req.tax_year,
    )
    complete_result = {}
    if pay_result.get("isMock"):
        complete_result = await svc_complete(
            payment_id=internal_id, order_id=pay_result["orderId"],
            gateway="mock", gateway_payment_id=f"pay_mock_{uuid.uuid4().hex[:10]}", db=db,
        )
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="municipal", stype="MUNICIPAL_PROPERTY_TAX_PAYMENT",
        status_str="DELIVERED" if pay_result.get("isMock") else "SUBMITTED",
        payload=req.dict(), payment_id=internal_id,
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="municipal", status=row.status,
        message="Property tax payment processed",
        data=complete_result.get("receipt") or pay_result,
    )


@router.post("/trade-license", response_model=SuccessResponse)
async def municipal_trade_license(req: MunicipalTradeLicenseRequest, db: Session = Depends(get_db)):
    stype = "MUNICIPAL_TRADE_LICENSE_RENEWAL" if req.is_renewal else "MUNICIPAL_TRADE_LICENSE_NEW"
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="municipal", stype=stype,
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="municipal", status=row.status,
        message=f"Trade license {'renewal' if req.is_renewal else 'application'} submitted",
    )


@router.post("/birth-certificate", response_model=SuccessResponse)
async def municipal_birth_certificate(req: MunicipalBirthCertRequest, db: Session = Depends(get_db)):
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="municipal", stype="MUNICIPAL_BIRTH_CERTIFICATE",
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="municipal", status=row.status,
        message="Birth certificate request submitted",
    )


@router.post("/death-certificate", response_model=SuccessResponse)
async def municipal_death_certificate(req: MunicipalDeathCertRequest, db: Session = Depends(get_db)):
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="municipal", stype="MUNICIPAL_DEATH_CERTIFICATE",
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="municipal", status=row.status,
        message="Death certificate request submitted",
    )


@router.post("/building-plan", response_model=SuccessResponse)
async def municipal_building_plan(req: MunicipalBuildingPlanRequest, db: Session = Depends(get_db)):
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="municipal", stype="MUNICIPAL_BUILDING_PLAN_APPROVAL",
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="municipal", status=row.status,
        message="Building plan approval request submitted",
    )


@router.post("/complaint", response_model=SuccessResponse)
async def municipal_complaint(req: MunicipalComplaintRequest, db: Session = Depends(get_db)):
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="municipal", stype="MUNICIPAL_SANITATION_COMPLAINT",
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="municipal", status=row.status,
        message="Complaint registered successfully",
    )


@router.post("/grievance", response_model=SuccessResponse)
async def municipal_grievance(req: MunicipalGrievanceRequest, db: Session = Depends(get_db)):
    row = save_request(
        db=db, req_id=str(uuid.uuid4()),
        dept="municipal", stype="MUNICIPAL_GENERAL_GRIEVANCE",
        status_str="SUBMITTED", payload=req.dict(),
    )
    return SuccessResponse(
        success=True, service_request_id=row.service_request_id,
        department="municipal", status=row.status,
        message="Grievance submitted — you will receive a response within 7 working days",
    )
