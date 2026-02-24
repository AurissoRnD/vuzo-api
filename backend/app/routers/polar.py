import hashlib
import hmac
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.config import get_settings
from app.models.database import get_http_client
from app.dependencies import get_current_user_id
from app.services.billing_service import add_credits

router = APIRouter()

POLAR_API_BASE = "https://api.polar.sh/v1"


_TIER_MAP = {"10": "polar_product_10", "30": "polar_product_30", "50": "polar_product_50"}


class CheckoutRequest(BaseModel):
    tier: Optional[str] = None    # "10" | "30" | "50"  — fixed preset tiers
    amount: Optional[float] = None  # custom amount in USD (min $10); uses the PWYW product


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a Polar checkout session for credit top-up.

    Preset tiers:  pass tier="10"|"30"|"50". Backend resolves the product ID from config.
    Custom amount: pass amount=<float> (min $10). Backend uses the PWYW product from config.
    Product IDs are never sent to or stored in the frontend.
    """
    settings = get_settings()
    if not settings.polar_access_token:
        raise HTTPException(status_code=503, detail="Polar payments not configured")

    if body.tier is None and body.amount is None:
        raise HTTPException(status_code=400, detail="Provide either 'tier' or 'amount'")

    if body.tier is not None and body.tier not in _TIER_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid tier '{body.tier}'. Must be one of: {list(_TIER_MAP)}")

    if body.amount is not None and body.amount < 10:
        raise HTTPException(status_code=400, detail="Minimum top-up amount is $10")

    # Resolve product ID from backend config — never exposed to the client
    if body.tier is not None:
        product_id: str = getattr(settings, _TIER_MAP[body.tier], "")
        if not product_id:
            raise HTTPException(status_code=503, detail=f"Polar product not configured for tier ${body.tier}")
    else:
        product_id = settings.polar_product_custom
        if not product_id:
            raise HTTPException(status_code=503, detail="Polar custom-amount product not configured")

    client = get_http_client()

    payload: dict = {
        "product_id": product_id,
        "customer_external_id": user_id,
    }

    # Polar expects amount in cents for variable-price ("Pay what you want") products
    if body.amount is not None:
        payload["amount"] = int(body.amount * 100)

    resp = await client.post(
        f"{POLAR_API_BASE}/checkouts/",
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.polar_access_token}",
            "Content-Type": "application/json",
        },
    )

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Polar checkout failed: {resp.text}")

    checkout_url = resp.json().get("url", "")
    if not checkout_url:
        raise HTTPException(status_code=502, detail="Polar did not return a checkout URL")

    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/webhooks/polar")
async def polar_webhook(request: Request):
    """
    Receive Polar webhook events.
    Verifies the signature, then processes order.created events
    to credit the user's balance.
    """
    settings = get_settings()
    body_bytes = await request.body()

    if settings.polar_webhook_secret:
        signature = request.headers.get("webhook-signature", "")
        if not _verify_polar_signature(body_bytes, signature, settings.polar_webhook_secret):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("type", "")

    if event_type == "order.created":
        order = payload.get("data", {})

        # Only process purchases of the 4 Vuzo top-up products.
        # Ignore any other products in the same Polar organisation.
        product_id = order.get("product", {}).get("id", "")
        vuzo_product_ids = {
            settings.polar_product_10,
            settings.polar_product_30,
            settings.polar_product_50,
            settings.polar_product_custom,
        }
        if product_id not in vuzo_product_ids:
            return {"received": True}

        customer = order.get("customer", {})
        user_id = customer.get("external_id")
        amount_cents = order.get("amount", 0)
        amount_usd = amount_cents / 100.0

        if user_id and amount_usd > 0:
            add_credits(
                user_id=user_id,
                amount=amount_usd,
                description=f"Polar payment: ${amount_usd:.2f}",
            )

    return {"received": True}


def _verify_polar_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify a Polar webhook signature (Standard Webhooks spec)."""
    if not signature:
        return False

    try:
        parts = signature.split(",")
        sig_map = {}
        for part in parts:
            k, v = part.strip().split("=", 1)
            sig_map[k] = v

        timestamp = sig_map.get("t", "")
        v1_sig = sig_map.get("v1", "")

        if not timestamp or not v1_sig:
            return False

        signed_content = f"{timestamp}.{body.decode('utf-8')}"
        import base64
        secret_bytes = base64.b64decode(secret)
        expected = hmac.new(
            secret_bytes,
            signed_content.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_b64 = base64.b64encode(expected).decode("utf-8")

        return hmac.compare_digest(v1_sig, expected_b64)
    except Exception:
        return False
