"""
Payment routes for koisk_api.py
================================
Add these imports and routes to your existing koisk_api.py.

STEP 1 — add to imports at the top of koisk_api.py:

    from fastapi import Request, BackgroundTasks
    from payment.payment_handler import (
        CustomerRegisterRequest, CustomerRegisterResponse,
        InitiatePaymentRequest,  InitiatePaymentResponse,
        CompletePaymentRequest,  CompletePaymentResponse,
        PaymentStatusResponse,   BillResponse,
        register_customer,   initiate_payment,
        complete_payment,    get_payment_status,
        get_payment_history, get_bills,
        verify_razorpay_webhook, handle_razorpay_webhook,
        verify_portone_webhook,  handle_portone_webhook,
    )

STEP 2 — paste the routes below into koisk_api.py
(just before the error handler section at the bottom).
"""

# ── paste below into koisk_api.py ─────────────────────────────────────────────

@app.post("/api/v1/payments/customer/register",
          response_model=CustomerRegisterResponse, tags=["Payments"])
async def payment_register_customer(req: CustomerRegisterRequest):
    """
    Register user on Razorpay AND PortOne.
    Call this in a BackgroundTask right after user registration.
    Returns both customer IDs — store them on the user record.
    """
    try:
        return await register_customer(req)
    except Exception as e:
        logger.error(f"[/payments/customer/register] {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/payments/initiate",
          response_model=InitiatePaymentResponse, tags=["Payments"])
async def payment_initiate(req: InitiatePaymentRequest):
    """
    Creates a gateway order.
    Frontend uses the returned orderId to open the Razorpay / PortOne SDK modal.
    """
    try:
        return await initiate_payment(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[/payments/initiate] {e}")
        raise HTTPException(status_code=502, detail="Gateway error — please retry")


@app.post("/api/v1/payments/complete",
          response_model=CompletePaymentResponse, tags=["Payments"])
async def payment_complete(req: CompletePaymentRequest):
    """
    Verifies and finalises a payment server-side after the SDK fires onSuccess.
    Razorpay: validates HMAC signature.
    PortOne:  server-to-server status check.
    Returns a receipt on success.
    """
    try:
        return await complete_payment(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[/payments/complete] {e}")
        raise HTTPException(status_code=502, detail="Could not verify payment")


@app.get("/api/v1/payments/status/{payment_id}",
         response_model=PaymentStatusResponse, tags=["Payments"])
async def payment_status(payment_id: str):
    """Poll payment status — used by receipt page."""
    try:
        return await get_payment_status(payment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/payments/history/{user_id}", tags=["Payments"])
async def payment_history(user_id: str):
    """Payment history for a user."""
    return await get_payment_history(user_id)


@app.get("/api/v1/{dept}/bills",
         response_model=list[BillResponse], tags=["Payments"])
async def dept_bills(dept: str, userId: str):
    """Pending bills for a user and department (electricity | gas | water)."""
    if dept not in ("electricity", "gas", "water"):
        raise HTTPException(status_code=400, detail=f"Unknown department: {dept}")
    return await get_bills(userId, dept)


# ── Webhooks ──────────────────────────────────────────────────────────────────

@app.post("/webhooks/razorpay", include_in_schema=False)
async def webhook_razorpay(request: Request):
    """
    Set this URL in Razorpay Dashboard → Webhooks.
    Set PAYMENT_WEBHOOK_SECRET env var to your Razorpay webhook secret.
    """
    body = await request.body()
    sig  = request.headers.get("X-Razorpay-Signature", "")
    if not verify_razorpay_webhook(body, sig):
        raise HTTPException(status_code=400, detail="Invalid signature")
    try:
        payload = await request.json()
        return await handle_razorpay_webhook(payload.get("event", ""), payload)
    except Exception as e:
        logger.error(f"[webhook/razorpay] {e}")
        return {"received": True}   # always 200 — prevents Razorpay retries


@app.post("/webhooks/portone", include_in_schema=False)
async def webhook_portone(request: Request):
    """
    Set this URL in PortOne Console → Store → Webhooks.
    """
    body = await request.body()
    sig  = request.headers.get("X-Portone-Signature", "")
    if not verify_portone_webhook(body, sig):
        raise HTTPException(status_code=400, detail="Invalid signature")
    try:
        payload    = await request.json()
        event_type = payload.get("type", payload.get("status", ""))
        return await handle_portone_webhook(event_type, payload)
    except Exception as e:
        logger.error(f"[webhook/portone] {e}")
        return {"received": True}
