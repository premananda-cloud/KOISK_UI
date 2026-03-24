"""
municipal/municipal_services.py
================================
KOISK Municipal Department Services
Follows the same ServiceRequest state-machine pattern as
Electricity_Services.py and Water_Services_Complete.py.

Services:
  1. Property Tax Payment
  2. New Water/Property Connection Application
  3. Trade License (New / Renewal)
  4. Birth Certificate Request
  5. Death Certificate Request
  6. Building Plan Approval
  7. Solid Waste / Sanitation Complaint
  8. General Grievance
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


# ─── Enums ────────────────────────────────────────────────────────────────────

class ServiceStatus(Enum):
    DRAFT        = "DRAFT"
    SUBMITTED    = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PENDING      = "PENDING"
    APPROVED     = "APPROVED"
    DENIED       = "DENIED"
    IN_PROGRESS  = "IN_PROGRESS"
    DELIVERED    = "DELIVERED"
    FAILED       = "FAILED"
    CANCELLED    = "CANCELLED"


class MunicipalServiceType(Enum):
    PROPERTY_TAX_PAYMENT     = "MUNICIPAL_PROPERTY_TAX_PAYMENT"
    TRADE_LICENSE_NEW        = "MUNICIPAL_TRADE_LICENSE_NEW"
    TRADE_LICENSE_RENEWAL    = "MUNICIPAL_TRADE_LICENSE_RENEWAL"
    BIRTH_CERTIFICATE        = "MUNICIPAL_BIRTH_CERTIFICATE"
    DEATH_CERTIFICATE        = "MUNICIPAL_DEATH_CERTIFICATE"
    BUILDING_PLAN_APPROVAL   = "MUNICIPAL_BUILDING_PLAN_APPROVAL"
    SANITATION_COMPLAINT     = "MUNICIPAL_SANITATION_COMPLAINT"
    GENERAL_GRIEVANCE        = "MUNICIPAL_GENERAL_GRIEVANCE"
    NEW_CONNECTION_REQUEST   = "MUNICIPAL_NEW_CONNECTION_REQUEST"


class PropertyType(Enum):
    RESIDENTIAL  = "Residential"
    COMMERCIAL   = "Commercial"
    INDUSTRIAL   = "Industrial"
    VACANT_LAND  = "Vacant Land"


class ComplaintCategory(Enum):
    GARBAGE_NOT_COLLECTED = "Garbage not collected"
    DRAIN_BLOCKED         = "Drain blocked"
    STREET_LIGHT_FAULT    = "Street light fault"
    ROAD_DAMAGE           = "Road damage"
    ILLEGAL_CONSTRUCTION  = "Illegal construction"
    NOISE_POLLUTION       = "Noise pollution"
    OTHER                 = "Other"


class ErrorCode(Enum):
    INVALID_DATA             = "INVALID_DATA"
    CONSUMER_NOT_FOUND       = "CONSUMER_NOT_FOUND"
    ACCOUNT_INACTIVE         = "ACCOUNT_INACTIVE"
    DUPLICATE_REQUEST        = "DUPLICATE_REQUEST"
    DOCUMENT_INVALID         = "DOCUMENT_INVALID"
    APPLICANT_UNVERIFIED     = "APPLICANT_UNVERIFIED"
    PAYMENT_FAILED           = "PAYMENT_FAILED"
    INTERNAL_ERROR           = "INTERNAL_ERROR"
    PROPERTY_NOT_FOUND       = "PROPERTY_NOT_FOUND"
    TAX_ALREADY_PAID         = "TAX_ALREADY_PAID"
    LICENSE_NOT_FOUND        = "LICENSE_NOT_FOUND"
    ZONE_RESTRICTED          = "ZONE_RESTRICTED"


# ─── Core ServiceRequest ─────────────────────────────────────────────────────

@dataclass
class ServiceRequest:
    service_request_id: str = field(default_factory=lambda: str(uuid4()))
    service_type:       str = ""
    status:             ServiceStatus = ServiceStatus.DRAFT
    payload:            Dict[str, Any] = field(default_factory=dict)
    user_id:            Optional[str] = None
    department:         str = "municipal"
    created_at:         datetime = field(default_factory=datetime.utcnow)
    updated_at:         datetime = field(default_factory=datetime.utcnow)
    completed_at:       Optional[datetime] = None
    error_code:         Optional[str] = None
    error_message:      Optional[str] = None
    status_history:     List[Dict] = field(default_factory=list)
    payment_id:         Optional[str] = None

    def __post_init__(self):
        self._add_history(self.status, "Request created")

    def _add_history(self, status: ServiceStatus, reason: str, meta: Dict = None):
        self.status_history.append({
            "status":    status.value,
            "reason":    reason,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata":  meta or {},
        })

    def update_status(self, new_status: ServiceStatus, reason: str, meta: Dict = None):
        old = self.status
        if not self._valid_transition(old, new_status):
            raise ValueError(f"Invalid transition: {old.value} → {new_status.value}")
        self.status     = new_status
        self.updated_at = datetime.utcnow()
        if new_status in (ServiceStatus.DELIVERED, ServiceStatus.FAILED, ServiceStatus.CANCELLED):
            self.completed_at = datetime.utcnow()
        self._add_history(new_status, reason, meta)

    @staticmethod
    def _valid_transition(f: ServiceStatus, t: ServiceStatus) -> bool:
        allowed = {
            ServiceStatus.DRAFT:        {ServiceStatus.SUBMITTED, ServiceStatus.CANCELLED},
            ServiceStatus.SUBMITTED:    {ServiceStatus.ACKNOWLEDGED, ServiceStatus.FAILED, ServiceStatus.CANCELLED},
            ServiceStatus.ACKNOWLEDGED: {ServiceStatus.PENDING, ServiceStatus.IN_PROGRESS, ServiceStatus.FAILED},
            ServiceStatus.PENDING:      {ServiceStatus.APPROVED, ServiceStatus.DENIED, ServiceStatus.IN_PROGRESS},
            ServiceStatus.APPROVED:     {ServiceStatus.IN_PROGRESS, ServiceStatus.DELIVERED},
            ServiceStatus.IN_PROGRESS:  {ServiceStatus.DELIVERED, ServiceStatus.FAILED},
            ServiceStatus.DENIED:       {ServiceStatus.CANCELLED},
        }
        return t in allowed.get(f, set())

    def to_dict(self, include_history: bool = False) -> Dict[str, Any]:
        d = {
            "service_request_id": self.service_request_id,
            "service_type":       self.service_type,
            "department":         self.department,
            "status":             self.status.value,
            "payload":            self.payload,
            "user_id":            self.user_id,
            "created_at":         self.created_at.isoformat(),
            "updated_at":         self.updated_at.isoformat(),
            "completed_at":       self.completed_at.isoformat() if self.completed_at else None,
            "error_code":         self.error_code,
            "error_message":      self.error_message,
            "payment_id":         self.payment_id,
        }
        if include_history:
            d["status_history"] = self.status_history
        return d


# ─── 1. Property Tax Payment ──────────────────────────────────────────────────

class PropertyTaxPaymentService:
    """Pay annual or arrear property tax for a residential/commercial property."""

    def create_request(
        self,
        consumer_number: str,
        property_id:     str,
        user_id:         str,
        tax_year:        str,           # e.g. "2025-2026"
        amount:          Decimal,
        payment_method:  str,
    ) -> ServiceRequest:
        if not consumer_number or not property_id:
            raise ValueError("consumer_number and property_id are required")
        if amount <= 0:
            raise ValueError("Amount must be positive")

        req = ServiceRequest(
            service_type=MunicipalServiceType.PROPERTY_TAX_PAYMENT.value,
            user_id=user_id,
            payload={
                "consumer_number": consumer_number,
                "property_id":     property_id,
                "tax_year":        tax_year,
                "amount":          str(amount),
                "payment_method":  payment_method,
            }
        )
        req.update_status(ServiceStatus.SUBMITTED, "Property tax payment request submitted")
        logger.info(f"[PropertyTax] {req.service_request_id} submitted  prop={property_id}")
        return req

    def process_payment(self, req: ServiceRequest, payment_id: str) -> ServiceRequest:
        req.payment_id = payment_id
        req.update_status(ServiceStatus.ACKNOWLEDGED, "Payment received by system")
        req.update_status(ServiceStatus.DELIVERED, "Tax receipt generated",
                          {"receipt_type": "property_tax", "tax_year": req.payload.get("tax_year")})
        return req

    def generate_receipt(self, req: ServiceRequest) -> Dict[str, Any]:
        return {
            "receipt_type":    "Property Tax Receipt",
            "property_id":     req.payload.get("property_id"),
            "consumer_number": req.payload.get("consumer_number"),
            "tax_year":        req.payload.get("tax_year"),
            "amount_paid":     req.payload.get("amount"),
            "payment_method":  req.payload.get("payment_method"),
            "payment_id":      req.payment_id,
            "generated_at":    datetime.utcnow().isoformat(),
        }


# ─── 2. Trade License ─────────────────────────────────────────────────────────

class TradeLicenseService:
    """New trade license application or annual renewal."""

    def create_request(
        self,
        applicant_id:    str,
        applicant_name:  str,
        business_name:   str,
        business_type:   str,      # Retail | Food | Manufacturing | Services
        address:         str,
        ward_number:     str,
        identity_proof:  str,
        address_proof:   str,
        is_renewal:      bool = False,
        existing_license_no: Optional[str] = None,
    ) -> ServiceRequest:
        stype = (MunicipalServiceType.TRADE_LICENSE_RENEWAL.value if is_renewal
                 else MunicipalServiceType.TRADE_LICENSE_NEW.value)
        req = ServiceRequest(
            service_type=stype,
            user_id=applicant_id,
            payload={
                "applicant_id":        applicant_id,
                "applicant_name":      applicant_name,
                "business_name":       business_name,
                "business_type":       business_type,
                "address":             address,
                "ward_number":         ward_number,
                "identity_proof":      identity_proof,
                "address_proof":       address_proof,
                "is_renewal":          is_renewal,
                "existing_license_no": existing_license_no,
            }
        )
        req.update_status(ServiceStatus.SUBMITTED, "Trade license application submitted")
        logger.info(f"[TradeLicense] {req.service_request_id} {'renewal' if is_renewal else 'new'}")
        return req

    def acknowledge(self, req: ServiceRequest) -> ServiceRequest:
        req.update_status(ServiceStatus.ACKNOWLEDGED, "Application received — inspection scheduled")
        return req

    def approve(self, req: ServiceRequest, officer_id: str, license_no: str) -> ServiceRequest:
        req.payload["issued_license_no"] = license_no
        req.payload["approved_by"]       = officer_id
        req.update_status(ServiceStatus.APPROVED, f"Trade license approved by {officer_id}")
        return req

    def deny(self, req: ServiceRequest, reason: str) -> ServiceRequest:
        req.error_message = reason
        req.update_status(ServiceStatus.DENIED, f"Application denied: {reason}")
        return req

    def deliver(self, req: ServiceRequest) -> ServiceRequest:
        req.update_status(ServiceStatus.DELIVERED, "License document issued")
        return req


# ─── 3. Birth Certificate ─────────────────────────────────────────────────────

class BirthCertificateService:

    def create_request(
        self,
        applicant_id:  str,
        child_name:    str,
        dob:           str,         # YYYY-MM-DD
        place_of_birth: str,
        father_name:   str,
        mother_name:   str,
        hospital_name: Optional[str],
        identity_proof: str,
    ) -> ServiceRequest:
        req = ServiceRequest(
            service_type=MunicipalServiceType.BIRTH_CERTIFICATE.value,
            user_id=applicant_id,
            payload={
                "applicant_id":   applicant_id,
                "child_name":     child_name,
                "dob":            dob,
                "place_of_birth": place_of_birth,
                "father_name":    father_name,
                "mother_name":    mother_name,
                "hospital_name":  hospital_name,
                "identity_proof": identity_proof,
            }
        )
        req.update_status(ServiceStatus.SUBMITTED, "Birth certificate request submitted")
        logger.info(f"[BirthCert] {req.service_request_id}")
        return req

    def process(self, req: ServiceRequest, officer_id: str, cert_number: str) -> ServiceRequest:
        req.payload["certificate_number"] = cert_number
        req.payload["processed_by"]       = officer_id
        req.update_status(ServiceStatus.ACKNOWLEDGED, "Records verified")
        req.update_status(ServiceStatus.DELIVERED, "Certificate issued", {"cert_no": cert_number})
        return req


# ─── 4. Death Certificate ─────────────────────────────────────────────────────

class DeathCertificateService:

    def create_request(
        self,
        applicant_id:    str,
        deceased_name:   str,
        date_of_death:   str,        # YYYY-MM-DD
        place_of_death:  str,
        cause_of_death:  str,
        informant_name:  str,
        identity_proof:  str,
        medical_certificate: str,
    ) -> ServiceRequest:
        req = ServiceRequest(
            service_type=MunicipalServiceType.DEATH_CERTIFICATE.value,
            user_id=applicant_id,
            payload={
                "applicant_id":       applicant_id,
                "deceased_name":      deceased_name,
                "date_of_death":      date_of_death,
                "place_of_death":     place_of_death,
                "cause_of_death":     cause_of_death,
                "informant_name":     informant_name,
                "identity_proof":     identity_proof,
                "medical_certificate": medical_certificate,
            }
        )
        req.update_status(ServiceStatus.SUBMITTED, "Death certificate request submitted")
        return req

    def process(self, req: ServiceRequest, officer_id: str, cert_number: str) -> ServiceRequest:
        req.payload["certificate_number"] = cert_number
        req.payload["processed_by"]       = officer_id
        req.update_status(ServiceStatus.ACKNOWLEDGED, "Medical records verified")
        req.update_status(ServiceStatus.DELIVERED, "Certificate issued", {"cert_no": cert_number})
        return req


# ─── 5. Building Plan Approval ────────────────────────────────────────────────

class BuildingPlanApprovalService:

    def create_request(
        self,
        applicant_id:   str,
        applicant_name: str,
        property_id:    str,
        plot_area:      float,
        built_up_area:  float,
        floors:         int,
        building_type:  str,         # Residential|Commercial|Industrial
        architect_name: str,
        identity_proof: str,
        land_ownership_proof: str,
        blueprint_ref:  str,
    ) -> ServiceRequest:
        req = ServiceRequest(
            service_type=MunicipalServiceType.BUILDING_PLAN_APPROVAL.value,
            user_id=applicant_id,
            payload={
                "applicant_id":        applicant_id,
                "applicant_name":      applicant_name,
                "property_id":         property_id,
                "plot_area_sqm":       plot_area,
                "built_up_area_sqm":   built_up_area,
                "floors":              floors,
                "building_type":       building_type,
                "architect_name":      architect_name,
                "identity_proof":      identity_proof,
                "land_ownership_proof": land_ownership_proof,
                "blueprint_ref":       blueprint_ref,
            }
        )
        req.update_status(ServiceStatus.SUBMITTED, "Building plan approval request submitted")
        logger.info(f"[BuildingPlan] {req.service_request_id} prop={property_id}")
        return req

    def schedule_inspection(self, req: ServiceRequest, inspection_date: str) -> ServiceRequest:
        req.payload["inspection_date"] = inspection_date
        req.update_status(ServiceStatus.PENDING, f"Site inspection scheduled for {inspection_date}")
        return req

    def approve(self, req: ServiceRequest, officer_id: str, approval_no: str) -> ServiceRequest:
        req.payload["approval_number"] = approval_no
        req.payload["approved_by"]     = officer_id
        req.update_status(ServiceStatus.APPROVED, f"Building plan approved — ref {approval_no}")
        req.update_status(ServiceStatus.DELIVERED, "Approval letter issued")
        return req

    def deny(self, req: ServiceRequest, reason: str) -> ServiceRequest:
        req.error_message = reason
        req.update_status(ServiceStatus.DENIED, f"Plan rejected: {reason}")
        return req


# ─── 6. Sanitation / Waste Complaint ─────────────────────────────────────────

class SanitationComplaintService:

    def create_request(
        self,
        consumer_id:       str,
        complaint_category: str,      # Use ComplaintCategory enum value
        location:          str,
        ward_number:       str,
        description:       str,
        severity:          str = "Medium",   # Low|Medium|High|Critical
        photo_ref:         Optional[str] = None,
    ) -> ServiceRequest:
        req = ServiceRequest(
            service_type=MunicipalServiceType.SANITATION_COMPLAINT.value,
            user_id=consumer_id,
            payload={
                "consumer_id":        consumer_id,
                "complaint_category": complaint_category,
                "location":           location,
                "ward_number":        ward_number,
                "description":        description,
                "severity":           severity,
                "photo_ref":          photo_ref,
            }
        )
        req.update_status(ServiceStatus.SUBMITTED, "Complaint registered")
        logger.info(f"[Sanitation] {req.service_request_id} ward={ward_number} cat={complaint_category}")
        return req

    def assign(self, req: ServiceRequest, field_officer_id: str) -> ServiceRequest:
        req.payload["assigned_to"] = field_officer_id
        req.update_status(ServiceStatus.IN_PROGRESS, f"Assigned to field officer {field_officer_id}")
        return req

    def resolve(self, req: ServiceRequest, resolution_notes: str) -> ServiceRequest:
        req.payload["resolution_notes"] = resolution_notes
        req.update_status(ServiceStatus.DELIVERED, "Complaint resolved")
        return req


# ─── 7. General Grievance ─────────────────────────────────────────────────────

class GeneralGrievanceService:

    def create_request(
        self,
        citizen_id:  str,
        subject:     str,
        description: str,
        dept_ref:    Optional[str] = None,   # which sub-department it concerns
        attachment:  Optional[str] = None,
    ) -> ServiceRequest:
        req = ServiceRequest(
            service_type=MunicipalServiceType.GENERAL_GRIEVANCE.value,
            user_id=citizen_id,
            payload={
                "citizen_id":  citizen_id,
                "subject":     subject,
                "description": description,
                "dept_ref":    dept_ref,
                "attachment":  attachment,
            }
        )
        req.update_status(ServiceStatus.SUBMITTED, "Grievance registered")
        return req

    def acknowledge(self, req: ServiceRequest, ticket_no: str) -> ServiceRequest:
        req.payload["ticket_number"] = ticket_no
        req.update_status(ServiceStatus.ACKNOWLEDGED, f"Grievance ticket issued: {ticket_no}")
        return req

    def resolve(self, req: ServiceRequest, response: str, officer_id: str) -> ServiceRequest:
        req.payload["resolution"]   = response
        req.payload["resolved_by"]  = officer_id
        req.update_status(ServiceStatus.DELIVERED, "Grievance resolved")
        return req
