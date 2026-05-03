"""
CardTransaction one-time top-up payment routes.

POST /v1/billing/checkout-sct  → generates hosted-checkout URL
GET|POST /v1/billing/sct-callback  → confirms payment, credits user, redirects to /thank-you
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.config import get_settings
from app.dependencies import get_current_user_id
from app.models.database import get_supabase
from app.services.billing_service import add_credits, get_balance
from app.services.ws_manager import manager as ws_manager

def _already_credited(user_id: str, idempotency_key: str) -> bool:
    """Check if we've already processed this payment by searching for the key in transaction descriptions."""
    sb = get_supabase()
    result = (
        sb.table("credit_transactions")
        .select("id")
        .eq("user_id", user_id)
        .ilike("description", f"%({idempotency_key})%")
        .limit(1)
        .execute()
    )
    return bool(result.data)
from app.services.cardtransaction_service import (
    PACKAGES,
    VALID_AMOUNTS,
    generate_payment_link,
    get_package,
    get_plan_code_for_amount,
    get_request_code,
    is_test_mode_request,
)
from app.utils.pending_payments import get_pending, remove_pending, save_pending

router = APIRouter()


class SctCheckoutRequest(BaseModel):
    amount: int


class PackageCheckoutRequest(BaseModel):
    package: str  # "starter" | "popular" | "pro"


class SctCheckoutResponse(BaseModel):
    url: str


def _get_user_email(user_id: str) -> str:
    sb = get_supabase()
    result = sb.table("users").select("email").eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return result.data[0].get("email", "") or ""


@router.post("/billing/checkout-sct", response_model=SctCheckoutResponse)
async def create_sct_checkout(
    body: SctCheckoutRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    if body.amount not in VALID_AMOUNTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid amount ${body.amount}. Must be one of: {VALID_AMOUNTS}",
        )

    plan_code = get_plan_code_for_amount(body.amount)
    is_test = is_test_mode_request(dict(request.headers))

    email = _get_user_email(user_id)
    if not email:
        raise HTTPException(status_code=400, detail="User has no email on file")

    settings = get_settings()
    callback_url = f"{settings.backend_url.rstrip('/')}/v1/billing/sct-callback"

    meta_data = {
        "user_id": user_id,
        "amount": body.amount,
        "sct_mode": "test" if is_test else "live",
    }

    result = await generate_payment_link(
        email=email,
        plan_code=plan_code,
        meta_data=meta_data,
        callback_url=callback_url,
        is_test=is_test,
    )

    request_code = result.get("request_code", "")
    if request_code:
        save_pending(request_code, {
            "user_id": user_id,
            "amount": float(body.amount),
            "is_test": is_test,
        })

    return SctCheckoutResponse(url=result["url"])


@router.post("/billing/checkout-package", response_model=SctCheckoutResponse)
async def create_package_checkout(
    body: PackageCheckoutRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """
    Initiate a package purchase checkout via CardTransaction.
    Payment amount differs from credit amount (bonus credits on higher tiers).
    """
    pkg = get_package(body.package)
    is_test = is_test_mode_request(dict(request.headers))
    email = _get_user_email(user_id)

    settings = get_settings()
    callback_url = f"{settings.backend_url.rstrip('/')}/v1/billing/sct-callback"

    meta_data = {
        "user_id": user_id,
        "amount": pkg["payment"],
        "credits_amount": pkg["credits"],
        "package": body.package,
        "redirect_url": settings.web_app_url.rstrip("/"),
        "sct_mode": "test" if is_test else "live",
    }

    result = await generate_payment_link(
        email=email,
        plan_code=pkg["plan_code"],
        meta_data=meta_data,
        callback_url=callback_url,
        is_test=is_test,
    )

    request_code = result.get("request_code", "")
    if request_code:
        save_pending(request_code, {
            "user_id": user_id,
            "amount": float(pkg["payment"]),
            "credits_amount": float(pkg["credits"]),
            "package": body.package,
            "is_test": is_test,
            "redirect_url": settings.web_app_url.rstrip("/"),
        })

    return SctCheckoutResponse(url=result["url"])


@router.get("/billing/packages")
async def list_packages():
    """Return available packages with payment and credit amounts."""
    return [
        {
            "id": k,
            "label": v["label"],
            "payment": v["payment"],
            "credits": v["credits"],
        }
        for k, v in PACKAGES.items()
    ]


async def _handle_callback(request: Request) -> RedirectResponse:
    settings = get_settings()
    frontend = settings.frontend_url.rstrip("/")

    params: dict = dict(request.query_params)
    if request.method == "POST":
        try:
            form = await request.form()
            for k, v in form.items():
                params.setdefault(k, v)
        except Exception:
            pass

    request_code = params.get("t") or params.get("request_code")
    if not request_code:
        return RedirectResponse(
            url=f"{frontend}/thank-you?status=error&message=missing_request_code",
            status_code=303,
        )

    sct = await get_request_code(request_code)

    user_id: Optional[str] = None
    amount: Optional[float] = None
    is_test = False
    transaction_code = params.get("transaction_code") or ""

    if sct.get("success"):
        meta = sct.get("meta_data") or {}
        user_id = meta.get("user_id") or user_id
        amount = float(meta.get("amount") or 0) or amount
        is_test = (meta.get("sct_mode") == "test") or is_test
        payment = sct.get("payment_data") or {}
        transaction_code = transaction_code or payment.get("invoice_number") or ""

    credits_amount: Optional[float] = None
    redirect_url: Optional[str] = None
    package_name: Optional[str] = None

    pending = get_pending(request_code) if (user_id is None or amount is None) else None
    if pending:
        user_id = user_id or pending.get("user_id")
        amount = amount or pending.get("amount")
        is_test = is_test or bool(pending.get("is_test"))
        credits_amount = pending.get("credits_amount")
        redirect_url = pending.get("redirect_url")
        package_name = (pending.get("package") or "").strip().lower() or None
    else:
        # Also check meta_data for credits_amount (package purchases)
        if sct.get("success"):
            meta = sct.get("meta_data") or {}
            credits_amount = float(meta.get("credits_amount") or 0) or None
            redirect_url = meta.get("redirect_url")
            package_name = (meta.get("package") or "").strip().lower() or None

    # Use credit amount if set (package purchase), otherwise credit the payment amount
    to_credit = credits_amount if credits_amount and credits_amount > 0 else amount
    destination = (redirect_url or frontend).rstrip("/")
    # Package checkouts (starter/popular/pro) should always return to the web app URL.
    if package_name in PACKAGES:
        destination = settings.web_app_url.rstrip("/")

    if not user_id or not amount or amount <= 0:
        return RedirectResponse(
            url=f"{frontend}/thank-you?status=error&message=incomplete_payment_data",
            status_code=303,
        )

    idempotency_key = transaction_code or request_code
    if _already_credited(user_id, idempotency_key):
        remove_pending(request_code)
        mode_param = "&mode=test" if is_test else ""
        return RedirectResponse(
            url=f"{destination}/thank-you?txn={idempotency_key}{mode_param}",
            status_code=303,
        )

    package_label = package_name or ""
    label = f"Package purchase ({package_label}): paid ${amount:.2f}, credited ${to_credit:.2f}" if package_label else f"CardTransaction payment: ${to_credit:.2f}"
    if transaction_code:
        label += f" ({transaction_code})"
    if is_test:
        label += " [test]"
    # For package purchases, record actual payment separately from credits issued
    recorded_payment = float(amount) if to_credit != amount else None
    add_credits(user_id=user_id, amount=to_credit, description=label, payment_amount=recorded_payment)

    # Push instant balance update to app if WebSocket is connected
    if ws_manager.is_connected(user_id):
        new_balance = get_balance(user_id)
        await ws_manager.send(user_id, {
            "type": "topup",
            "amount": round(amount, 2),
            "balance": round(new_balance, 6),
            "message": f"Top-up of ${amount:.2f} received. New balance: ${new_balance:.2f}",
        })

    remove_pending(request_code)

    txn_param = transaction_code or request_code
    mode_param = "&mode=test" if is_test else ""
    return RedirectResponse(
        url=f"{destination}/thank-you?txn={txn_param}{mode_param}",
        status_code=303,
    )


@router.get("/billing/sct-callback")
async def sct_callback_get(request: Request):
    return await _handle_callback(request)


@router.post("/billing/sct-callback")
async def sct_callback_post(request: Request):
    return await _handle_callback(request)
