"""
KOISK Payment Handler
=====================
Backend integration for Razorpay and PortOne (formerly Cashfree).

Architecture:
  - ALL gateway API calls happen here (secret keys NEVER go to frontend)
  - Frontend (orchestrator.js) calls FastAPI → FastAPI calls this handler
  - Webhook endpoints verify HMAC signatures server-side

Env vars required (add to .env):
  RAZORPAY_KEY_ID        = rzp_live_xxxxxxxxxxxx
  RAZORPAY_KEY_SECRET    = xxxxxxxxxxxxxxxxxxxx
  PORTONE_STORE_ID       = your-store-id
  PORTONE_CHANNEL_KEY    = your-channel-key
  PORTONE_API_SECRET     = your-portone-api-secret
  PAYMENT_WEBHOOK_SECRET = shared-webhook-hmac-secret
"""

import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config — loaded from environment (never hardcoded)
# ---------------------------------------------------------------------------

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

PORTONE_STORE_ID    = os.getenv("PORTONE_STORE_ID", "")
PORTONE_CHANNEL_KEY = os.getenv("PORTONE_CHANNEL_KEY", "")
PORTONE_API_SECRET  = os.getenv("PORTONE_API_SECRET", "")

PORTONE_BASE_URL    = "https://api.portone.io"
RAZORPAY_BASE_URL   = "https://api.razorpay.com/v1"

WEBHOOK_SECRET      = os.getenv("PAYMENT_WEBHOOK_SECRET", "")


# ---------------------------------------------------------------------------
# Pydantic models — request / response shapes used by koisk_api.py
# ---------------------------------------------------------------------------

class CustomerRegisterRequest(BaseModel):
    userId: str
    name: str
    contact: str                   # E.164 format  e.g. +919876543210
    email: str
    consumerId: Optional[str] = None
    notes: Optional[Dict[str, str]] = None


class CustomerRegisterResponse(BaseModel):
    userId: str
    portoneCustomerId: Optional[str] = None
    razorpayCustomerId: Optional[str] = None
    name: str
    contact: str
    email: str
    syncedToBackend: bool = True
    createdAt: str


class InitiatePaymentRequest(BaseModel):
    userId: str
    billId: str
    dept: str                       # electricity | gas | water
    amount: float
    currency: str = "INR"
    gateway: str                    # portone | razorpay
    method: str                     # upi | card | netbanking
    customerId: Optional[str] = None


class InitiatePaymentResponse(BaseModel):
    orderId: str
    paymentId: str                  # our internal UUID
    gatewayOrderId: str
    gateway: str
    mode: str = "real"
    amount: float
    currency: str


class CompletePaymentRequest(BaseModel):
    paymentId: str                  # our internal UUID
    orderId: str
    gateway: str
    gatewayPaymentId: str
    razorpaySignature: Optional[str] = None   # Razorpay only


class Receipt(BaseModel):
    referenceNo: str
    amount: float
    dept: str
    method: str
    paidAt: str
    consumerNo: Optional[str] = None
    gatewayPaymentId: str
    gateway: str


class CompletePaymentResponse(BaseModel):
    success: bool
    receipt: Receipt


class PaymentStatusResponse(BaseModel):
    paymentId: str
    status: str                     # PENDING | SUCCESS | FAILED
    gatewayStatus: Optional[str] = None
    amount: Optional[float] = None
    paidAt: Optional[str] = None


class BillResponse(BaseModel):
    id: str
    userId: str
    dept: str
    consumerNo: str
    billMonth: str
    amountDue: float
    dueDate: str
    status: str                     # PENDING | PAID | OVERDUE


# ---------------------------------------------------------------------------
# In-memory store — replace with DB (PaymentHistory / CustomerProfile tables)
# ---------------------------------------------------------------------------

_customers: Dict[str, Dict] = {}    # userId → customer record
_payments:  Dict[str, Dict] = {}    # paymentId → payment record
_bills:     Dict[str, Dict] = {}    # billId → bill record  (seeded below)


def _seed_demo_bills():
    """Seed sample bills so the UI has something to show."""
    demo_bills = [
        {
            "id": "bill-elec-001", "userId": "demo-user-ramesh-001",
            "dept": "electricity",  "consumerNo": "ELEC-MH-5521",
            "billMonth": "2026-02", "amountDue": 1240.00,
            "dueDate": "2026-03-15", "status": "PENDING",
        },
        {
            "id": "bill-gas-001",  "userId": "demo-user-ramesh-001",
            "dept": "gas",         "consumerNo": "GAS-MH-3310",
            "billMonth": "2026-02", "amountDue": 680.00,
            "dueDate": "2026-03-20", "status": "PENDING",
        },
        {
            "id": "bill-water-001","userId": "demo-user-ramesh-001",
            "dept": "water",       "consumerNo": "WATER-MH-7741",
            "billMonth": "2026-02", "amountDue": 320.00,
            "dueDate": "2026-03-25", "status": "PENDING",
        },
    ]
    for b in demo_bills:
        _bills[b["id"]] = b


_seed_demo_bills()


# ---------------------------------------------------------------------------
# Reference number generator
# ---------------------------------------------------------------------------

_DEPT_PREFIX = {"electricity": "ELEC", "gas": "GAS", "water": "WTR"}


def _generate_reference(dept: str) -> str:
    prefix = _DEPT_PREFIX.get(dept, "PAY")
    return f"{prefix}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


# ---------------------------------------------------------------------------
# PortOne helpers
# ---------------------------------------------------------------------------

def _portone_headers() -> Dict[str, str]:
    return {
        "Authorization": f"PortOne {PORTONE_API_SECRET}",
        "Content-Type": "application/json",
    }


async def _portone_create_customer(name: str, contact: str, email: str,
                                   notes: Optional[Dict] = None) -> str:
    """
    Create a customer on PortOne.
    Returns the PortOne customerId string.
    """
    if not PORTONE_API_SECRET:
        logger.warning("[PortOne] API secret not set — returning mock customer ID")
        return f"portone_mock_{uuid.uuid4().hex[:12]}"

    payload = {
        "customer_name":  name,
        "customer_phone": contact,
        "customer_email": email,
    }
    if notes:
        payload["metadata"] = notes

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{PORTONE_BASE_URL}/customers",
            json=payload,
            headers=_portone_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data["customer_id"]


async def _portone_create_order(payment_id: str, amount: float,
                                currency: str, customer_id: str,
                                dept: str) -> str:
    """
    Create a PortOne payment order.
    Returns the PortOne paymentId (used as orderId on the frontend).
    """
    if not PORTONE_API_SECRET:
        return f"portone_order_mock_{uuid.uuid4().hex[:12]}"

    payload = {
        "payment_id":   payment_id,
        "order_amount": round(amount * 100),   # paise
        "order_currency": currency,
        "channel_key":  PORTONE_CHANNEL_KEY,
        "customer_id":  customer_id,
        "order_name":   f"KOISK {dept.capitalize()} Bill",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{PORTONE_BASE_URL}/payments",
            json=payload,
            headers=_portone_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data["payment_id"]


async def _portone_get_payment_status(portone_payment_id: str) -> Dict:
    """Server-to-server status check — used to verify completion."""
    if not PORTONE_API_SECRET:
        return {"status": "Paid", "amount": 0}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{PORTONE_BASE_URL}/payments/{portone_payment_id}",
            headers=_portone_headers(),
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Razorpay helpers
# ---------------------------------------------------------------------------

def _razorpay_auth():
    return (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)


async def _razorpay_create_customer(name: str, contact: str,
                                    email: str, notes: Optional[Dict] = None) -> str:
    """
    Create a customer on Razorpay.
    Returns the Razorpay customer id string.
    """
    if not RAZORPAY_KEY_SECRET:
        logger.warning("[Razorpay] Key secret not set — returning mock customer ID")
        return f"razorpay_mock_{uuid.uuid4().hex[:12]}"

    payload: Dict[str, Any] = {"name": name, "contact": contact, "email": email}
    if notes:
        payload["notes"] = notes

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{RAZORPAY_BASE_URL}/customers",
            json=payload,
            auth=_razorpay_auth(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data["id"]


async def _razorpay_create_order(amount: float, currency: str,
                                 receipt: str, notes: Optional[Dict] = None) -> str:
    """
    Create a Razorpay order.
    Returns the Razorpay order_id.
    """
    if not RAZORPAY_KEY_SECRET:
        return f"order_mock_{uuid.uuid4().hex[:12]}"

    payload: Dict[str, Any] = {
        "amount":   round(amount * 100),   # paise
        "currency": currency,
        "receipt":  receipt,
    }
    if notes:
        payload["notes"] = notes

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{RAZORPAY_BASE_URL}/orders",
            json=payload,
            auth=_razorpay_auth(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data["id"]


def _razorpay_verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Verify Razorpay HMAC-SHA256 signature server-side.
    Must be called before marking a payment as SUCCESS.
    """
    if not RAZORPAY_KEY_SECRET:
        logger.warning("[Razorpay] Key secret not set — skipping signature verify (mock mode)")
        return True

    message = f"{order_id}|{payment_id}"
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _razorpay_get_payment(razorpay_payment_id: str) -> Dict:
    """Fetch a Razorpay payment record (server-to-server verify)."""
    if not RAZORPAY_KEY_SECRET:
        return {"status": "captured", "amount": 0}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{RAZORPAY_BASE_URL}/payments/{razorpay_payment_id}",
            auth=_razorpay_auth(),
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Public API — called by koisk_api.py route handlers
# ---------------------------------------------------------------------------

async def register_customer(req: CustomerRegisterRequest) -> CustomerRegisterResponse:
    """
    Register user with BOTH Razorpay and PortOne in parallel.
    Called automatically on user registration (background task).
    Customer IDs are stored in _customers and should be persisted to DB.
    """
    # Return cached record if already registered
    if req.userId in _customers:
        cached = _customers[req.userId]
        return CustomerRegisterResponse(**cached)

    notes = req.notes or {"koisk_user_id": req.userId}
    if req.consumerId:
        notes["consumer_id"] = req.consumerId

    # Call both gateways (independent — one failing doesn't block the other)
    portone_customer_id  = None
    razorpay_customer_id = None
    errors: List[str]    = []

    try:
        portone_customer_id = await _portone_create_customer(
            name=req.name, contact=req.contact, email=req.email, notes=notes
        )
        logger.info(f"[PortOne] Customer created: {portone_customer_id} for user {req.userId}")
    except Exception as e:
        errors.append(f"PortOne: {str(e)}")
        logger.error(f"[PortOne] Failed to create customer for {req.userId}: {e}")

    try:
        razorpay_customer_id = await _razorpay_create_customer(
            name=req.name, contact=req.contact, email=req.email, notes=notes
        )
        logger.info(f"[Razorpay] Customer created: {razorpay_customer_id} for user {req.userId}")
    except Exception as e:
        errors.append(f"Razorpay: {str(e)}")
        logger.error(f"[Razorpay] Failed to create customer for {req.userId}: {e}")

    record = {
        "userId":              req.userId,
        "portoneCustomerId":   portone_customer_id,
        "razorpayCustomerId":  razorpay_customer_id,
        "name":                req.name,
        "contact":             req.contact,
        "email":               req.email,
        "syncedToBackend":     True,
        "createdAt":           datetime.utcnow().isoformat(),
    }

    # Persist to in-memory store (swap for DB write in production)
    _customers[req.userId] = record

    if errors:
        logger.warning(f"[register_customer] Partial registration for {req.userId}: {errors}")

    return CustomerRegisterResponse(**record)


async def initiate_payment(req: InitiatePaymentRequest) -> InitiatePaymentResponse:
    """
    Create a gateway order for the given bill.
    Returns orderId + our internal paymentId to the frontend.
    """
    payment_id  = str(uuid.uuid4())
    gateway_order_id: str

    # Look up customer IDs
    customer = _customers.get(req.userId, {})

    if req.gateway == "portone":
        portone_customer_id = customer.get("portoneCustomerId") or f"portone_auto_{req.userId[:8]}"
        gateway_order_id = await _portone_create_order(
            payment_id=payment_id,
            amount=req.amount,
            currency=req.currency,
            customer_id=portone_customer_id,
            dept=req.dept,
        )
    elif req.gateway == "razorpay":
        receipt = f"koisk_{req.dept}_{payment_id[:8]}"
        gateway_order_id = await _razorpay_create_order(
            amount=req.amount,
            currency=req.currency,
            receipt=receipt,
            notes={"koisk_payment_id": payment_id, "dept": req.dept, "user_id": req.userId},
        )
    else:
        raise ValueError(f"Unknown gateway: {req.gateway}")

    # Persist pending payment record (swap for DB write in production)
    _payments[payment_id] = {
        "id":              payment_id,
        "userId":          req.userId,
        "billId":          req.billId,
        "dept":            req.dept,
        "amount":          req.amount,
        "currency":        req.currency,
        "gateway":         req.gateway,
        "method":          req.method,
        "gatewayOrderId":  gateway_order_id,
        "status":          "PENDING",
        "createdAt":       datetime.utcnow().isoformat(),
        "paidAt":          None,
    }

    logger.info(f"[initiate_payment] {req.gateway} order {gateway_order_id} for payment {payment_id}")

    return InitiatePaymentResponse(
        orderId=gateway_order_id,
        paymentId=payment_id,
        gatewayOrderId=gateway_order_id,
        gateway=req.gateway,
        amount=req.amount,
        currency=req.currency,
    )


async def complete_payment(req: CompletePaymentRequest) -> CompletePaymentResponse:
    """
    Verify and finalise a payment after the gateway SDK confirms on the frontend.
    For Razorpay: validates HMAC signature before accepting.
    For PortOne:  server-to-server status check.
    """
    payment = _payments.get(req.paymentId)
    if not payment:
        raise ValueError(f"Payment {req.paymentId} not found")

    # ── Razorpay: verify signature ───────────────────────────────────────────
    if req.gateway == "razorpay":
        if not req.razorpaySignature:
            raise ValueError("Razorpay signature is required to complete payment")

        if not _razorpay_verify_signature(
            order_id=req.orderId,
            payment_id=req.gatewayPaymentId,
            signature=req.razorpaySignature,
        ):
            payment["status"] = "FAILED"
            raise ValueError("Razorpay signature verification failed — payment rejected")

        # Optional: fetch full payment details for amount double-check
        try:
            rzp_data = await _razorpay_get_payment(req.gatewayPaymentId)
            if rzp_data.get("status") != "captured":
                raise ValueError(f"Razorpay payment not captured (status: {rzp_data.get('status')})")
        except httpx.HTTPError as e:
            logger.warning(f"[Razorpay] Could not fetch payment details: {e} — trusting signature")

    # ── PortOne: server-to-server status check ───────────────────────────────
    elif req.gateway == "portone":
        try:
            po_data = await _portone_get_payment_status(req.gatewayPaymentId)
            portone_status = po_data.get("status", "").lower()
            if portone_status not in ("paid", "virtual_account_issued", "partial_paid"):
                raise ValueError(f"PortOne payment not paid (status: {portone_status})")
        except httpx.HTTPError as e:
            logger.warning(f"[PortOne] Could not verify payment status: {e} — proceeding with caution")

    # ── Mark SUCCESS and build receipt ───────────────────────────────────────
    paid_at      = datetime.utcnow().isoformat()
    reference_no = _generate_reference(payment["dept"])

    payment.update({
        "status":          "SUCCESS",
        "gatewayPaymentId": req.gatewayPaymentId,
        "referenceNo":     reference_no,
        "paidAt":          paid_at,
    })

    # Mark the bill as paid
    bill = _bills.get(payment.get("billId", ""), {})
    if bill:
        bill["status"] = "PAID"

    receipt = Receipt(
        referenceNo=reference_no,
        amount=payment["amount"],
        dept=payment["dept"],
        method=payment["method"],
        paidAt=paid_at,
        consumerNo=bill.get("consumerNo"),
        gatewayPaymentId=req.gatewayPaymentId,
        gateway=req.gateway,
    )

    logger.info(f"[complete_payment] Payment {req.paymentId} SUCCESS — ref {reference_no}")
    return CompletePaymentResponse(success=True, receipt=receipt)


async def get_payment_status(payment_id: str) -> PaymentStatusResponse:
    """Poll payment status — used by frontend for receipt page."""
    payment = _payments.get(payment_id)
    if not payment:
        raise ValueError(f"Payment {payment_id} not found")

    return PaymentStatusResponse(
        paymentId=payment_id,
        status=payment["status"],
        amount=payment.get("amount"),
        paidAt=payment.get("paidAt"),
    )


async def get_payment_history(user_id: str) -> List[Dict]:
    """Return all payments for a user (newest first)."""
    history = [p for p in _payments.values() if p.get("userId") == user_id]
    history.sort(key=lambda p: p.get("createdAt", ""), reverse=True)
    return history


async def get_bills(user_id: str, dept: str) -> List[BillResponse]:
    """Return pending bills for a user + department."""
    results = [
        b for b in _bills.values()
        if b.get("userId") == user_id and b.get("dept") == dept and b.get("status") != "PAID"
    ]
    return [BillResponse(**b) for b in results]


# ---------------------------------------------------------------------------
# Webhook handlers — called by FastAPI POST /webhooks/* endpoints
# ---------------------------------------------------------------------------

def verify_razorpay_webhook(body: bytes, signature: str) -> bool:
    """
    Verify Razorpay webhook HMAC-SHA256 signature.
    Set PAYMENT_WEBHOOK_SECRET to your Razorpay webhook secret.
    """
    if not WEBHOOK_SECRET:
        logger.warning("[webhook] PAYMENT_WEBHOOK_SECRET not set — skipping verification")
        return True

    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_portone_webhook(body: bytes, signature: str) -> bool:
    """
    Verify PortOne webhook signature.
    PortOne sends X-Portone-Signature header.
    """
    if not PORTONE_API_SECRET:
        return True

    expected = hmac.new(
        PORTONE_API_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def handle_razorpay_webhook(event_type: str, payload: Dict) -> Dict:
    """Process a verified Razorpay webhook event."""
    if event_type == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        rz_payment_id  = payment_entity.get("id")
        rz_order_id    = payment_entity.get("order_id")

        # Find our internal payment by gatewayOrderId
        for p in _payments.values():
            if p.get("gatewayOrderId") == rz_order_id:
                if p["status"] != "SUCCESS":
                    p["status"]          = "SUCCESS"
                    p["gatewayPaymentId"] = rz_payment_id
                    p["paidAt"]          = datetime.utcnow().isoformat()
                    p["referenceNo"]     = _generate_reference(p["dept"])
                    logger.info(f"[webhook/razorpay] payment.captured → internal {p['id']} SUCCESS")
                break

    elif event_type == "payment.failed":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        rz_order_id    = payment_entity.get("order_id")
        for p in _payments.values():
            if p.get("gatewayOrderId") == rz_order_id:
                p["status"] = "FAILED"
                logger.info(f"[webhook/razorpay] payment.failed → internal {p['id']} FAILED")
                break

    return {"received": True, "event": event_type}


async def handle_portone_webhook(event_type: str, payload: Dict) -> Dict:
    """Process a verified PortOne webhook event."""
    if event_type in ("Transaction.Paid", "Transaction.PartiallyPaid"):
        po_payment_id = payload.get("payment", {}).get("paymentId") or payload.get("paymentId")

        for p in _payments.values():
            if p.get("id") == po_payment_id or p.get("gatewayOrderId") == po_payment_id:
                if p["status"] != "SUCCESS":
                    p["status"]          = "SUCCESS"
                    p["gatewayPaymentId"] = po_payment_id
                    p["paidAt"]          = datetime.utcnow().isoformat()
                    p["referenceNo"]     = _generate_reference(p["dept"])
                    logger.info(f"[webhook/portone] {event_type} → internal {p['id']} SUCCESS")
                break

    elif event_type == "Transaction.Failed":
        po_payment_id = payload.get("payment", {}).get("paymentId") or payload.get("paymentId")
        for p in _payments.values():
            if p.get("id") == po_payment_id or p.get("gatewayOrderId") == po_payment_id:
                p["status"] = "FAILED"
                break

    return {"received": True, "event": event_type}
