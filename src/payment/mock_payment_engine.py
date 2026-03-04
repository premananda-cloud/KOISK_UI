"""
payment/mock_payment_engine.py
================================
Simulates the full payment lifecycle (initiate → complete → receipt)
for ALL departments — no real gateway keys required.

Used automatically when:
  - MOCK_PAYMENT=true in env  (explicit)
  - RAZORPAY_KEY_SECRET and PORTONE_API_SECRET are both empty (implicit)

Reference format per department:
  PAY-ELEC-YYYYMMDD-NNNN
  PAY-WAT-YYYYMMDD-NNNN
  PAY-MUNI-YYYYMMDD-NNNN
"""

import hashlib
import hmac
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────

MOCK_PAYMENT       = os.getenv("MOCK_PAYMENT", "true").lower() == "true"
RAZORPAY_SECRET    = os.getenv("RAZORPAY_KEY_SECRET", "")
PORTONE_SECRET     = os.getenv("PORTONE_API_SECRET", "")
WEBHOOK_SECRET     = os.getenv("PAYMENT_WEBHOOK_SECRET", "koisk-dev-secret")

# Auto-enable mock when no gateway keys are present
IS_MOCK = MOCK_PAYMENT or (not RAZORPAY_SECRET and not PORTONE_SECRET)

# Simulated failure rate — 1 in 20 for demo realism
MOCK_FAILURE_RATE  = float(os.getenv("MOCK_FAILURE_RATE", "0.05"))

# ─── Department prefixes ──────────────────────────────────────────────────────

_DEPT_PREFIX = {
    "electricity": "ELEC",
    "water":       "WAT",
    "municipal":   "MUNI",
}

_ref_counter: Dict[str, int] = {}


def make_reference_no(department: str) -> str:
    """Generate a human-readable payment reference number."""
    prefix = _DEPT_PREFIX.get(department, "PAY")
    today  = datetime.utcnow().strftime("%Y%m%d")
    key    = f"{prefix}{today}"
    _ref_counter[key] = _ref_counter.get(key, 0) + 1
    return f"PAY-{prefix}-{today}-{_ref_counter[key]:04d}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Mock Gateway Responses ───────────────────────────────────────────────────

def mock_create_order(
    internal_id: str,
    amount: float,
    department: str,
    method: str,
) -> Dict[str, Any]:
    """
    Simulate creating a gateway order.
    Returns the same shape as PortOne/Razorpay so the real adapter is a drop-in.
    """
    order_id = f"mock_order_{uuid.uuid4().hex[:12]}"
    logger.info(f"[MockGateway] Order created: {order_id}  dept={department}  amount=₹{amount}")
    return {
        "order_id":   order_id,
        "payment_id": internal_id,     # PortOne-style
        "id":         order_id,        # Razorpay-style alias
        "amount":     int(amount * 100),
        "currency":   "INR",
        "status":     "created",
        "gateway":    "mock",
        "expires_at": None,
    }


def mock_verify_payment(
    order_id: str,
    gateway_payment_id: str,
    amount: float,
    department: str,
) -> Dict[str, Any]:
    """
    Simulate server-side payment verification.
    Raises ValueError on simulated failure (1 in 20 by default).
    """
    import random
    if random.random() < MOCK_FAILURE_RATE:
        raise ValueError(
            f"[Mock] Payment declined by issuing bank (simulated failure — "
            f"rate={MOCK_FAILURE_RATE:.0%})"
        )

    reference_no = make_reference_no(department)
    paid_at      = _now_iso()
    logger.info(f"[MockGateway] Payment verified: {gateway_payment_id}  ref={reference_no}")
    return {
        "verified":     True,
        "reference_no": reference_no,
        "paid_at":      paid_at,
        "status":       "paid",
        "gateway":      "mock",
    }


# ─── HMAC helpers (used even in mock mode for webhook tests) ──────────────────

def make_mock_signature(body: bytes) -> str:
    """Generate a webhook signature so you can test the webhook endpoint locally."""
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    if not secret:
        logger.warning("[HMAC] No secret configured — skipping verification")
        return True
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ─── Payment service functions ────────────────────────────────────────────────

async def svc_initiate(
    *,
    internal_id: str,
    user_id: str,
    bill_id: str,
    department: str,
    amount: float,
    currency: str = "INR",
    method: str,
    gateway: str,
    db,                 # SQLAlchemy Session
    consumer_number: Optional[str] = None,
    billing_period:  Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a payment order (mock or real gateway).
    Inserts a 'pending' row into the payments table.
    Returns orderId for the frontend SDK.
    """
    from .payment_handler import (
        portone_create_payment, razorpay_create_order
    )
    from ..department.database.models import Payment

    if IS_MOCK or gateway == "mock":
        gw_result    = mock_create_order(internal_id, amount, department, method)
        gateway_used = "mock"
        order_id     = gw_result["order_id"]
    elif gateway == "portone":
        gw_result    = await portone_create_payment(
            internal_id=internal_id, amount=amount,
            currency=currency, customer_id=user_id, dept=department
        )
        gateway_used = "portone"
        order_id     = gw_result.get("payment_id", internal_id)
    elif gateway == "razorpay":
        gw_result    = await razorpay_create_order(
            amount=amount, currency=currency,
            receipt=f"koisk_{department}_{internal_id[:8]}",
            notes={"dept": department, "user_id": user_id}
        )
        gateway_used = "razorpay"
        order_id     = gw_result["id"]
    else:
        raise ValueError(f"Unknown gateway: {gateway!r}")

    # Persist pending payment
    payment = Payment(
        id=internal_id,
        user_id=user_id,
        bill_id=bill_id,
        department=department,
        amount=Decimal(str(amount)),
        currency=currency,
        gateway=gateway_used,
        gateway_order_id=order_id,
        payment_method=method,
        consumer_number=consumer_number,
        billing_period=billing_period,
        status="pending",
    )
    db.add(payment)
    db.commit()

    logger.info(f"[initiate] dept={department} gateway={gateway_used} order={order_id} internal={internal_id}")

    return {
        "success":      True,
        "orderId":      order_id,
        "paymentId":    internal_id,
        "gateway":      gateway_used,
        "gatewayData":  gw_result,
        "isMock":       IS_MOCK or gateway_used == "mock",
        "message":      "Payment order created",
        "timestamp":    _now_iso(),
    }


async def svc_complete(
    *,
    payment_id: str,
    order_id: str,
    gateway: str,
    gateway_payment_id: str,
    razorpay_signature: Optional[str] = None,
    db,
) -> Dict[str, Any]:
    """
    Verify payment server-side and mark as paid.
    Works with mock, PortOne, and Razorpay.
    """
    from ..department.database.models import Payment
    from .payment_handler import (
        razorpay_verify_signature, razorpay_get_payment,
        portone_get_payment
    )

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise ValueError(f"Payment {payment_id} not found")

    if payment.status == "paid":
        return _receipt_response(payment)

    # ── Mock verification ─────────────────────────────────────────────────────
    if IS_MOCK or gateway == "mock":
        result = mock_verify_payment(
            order_id=order_id,
            gateway_payment_id=gateway_payment_id or f"pay_mock_{uuid.uuid4().hex[:10]}",
            amount=float(payment.amount),
            department=payment.department,
        )

    # ── Razorpay ──────────────────────────────────────────────────────────────
    elif gateway == "razorpay":
        if not razorpay_signature:
            raise ValueError("razorpaySignature required for Razorpay payments")
        if not razorpay_verify_signature(order_id, gateway_payment_id, razorpay_signature):
            payment.status = "failed"
            payment.error_message = "Signature verification failed"
            db.commit()
            raise ValueError("Razorpay HMAC verification failed")
        rz = await razorpay_get_payment(gateway_payment_id)
        if rz.get("status") != "captured":
            raise ValueError(f"Razorpay status={rz.get('status')!r}, expected 'captured'")
        result = {
            "verified":     True,
            "reference_no": make_reference_no(payment.department),
            "paid_at":      _now_iso(),
            "status":       "paid",
        }

    # ── PortOne ───────────────────────────────────────────────────────────────
    elif gateway == "portone":
        po     = await portone_get_payment(gateway_payment_id)
        status = po.get("status", "").lower()
        if status not in ("paid", "virtual_account_issued", "partial_paid"):
            raise ValueError(f"PortOne status={status!r}, expected 'paid'")
        result = {
            "verified":     True,
            "reference_no": make_reference_no(payment.department),
            "paid_at":      _now_iso(),
            "status":       "paid",
        }
    else:
        raise ValueError(f"Unknown gateway: {gateway!r}")

    # ── Mark paid ─────────────────────────────────────────────────────────────
    payment.status             = "paid"
    payment.gateway_payment_id = gateway_payment_id
    payment.reference_no       = result["reference_no"]
    payment.paid_at            = datetime.utcnow()
    db.commit()

    logger.info(f"[complete] {payment_id} → PAID  ref={result['reference_no']}")
    return _receipt_response(payment)


def _receipt_response(payment) -> Dict[str, Any]:
    return {
        "success":  True,
        "status":   "SUCCESS",
        "receipt": {
            "referenceNo": payment.reference_no,
            "amount":      float(payment.amount),
            "dept":        payment.department,
            "method":      payment.payment_method,
            "paidAt":      payment.paid_at.isoformat() if payment.paid_at else _now_iso(),
            "consumerNo":  payment.consumer_number,
            "billingPeriod": payment.billing_period,
        },
        "message":   "Payment verified successfully",
        "timestamp": _now_iso(),
    }
