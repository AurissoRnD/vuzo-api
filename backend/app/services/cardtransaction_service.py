"""
Thin wrapper around the CardTransaction REST API.
Handles gen-payment-link and get-request-code for one-time credit top-ups.
"""

import json
from typing import Any

from fastapi import HTTPException

from app.config import get_settings
from app.models.database import get_http_client

# Packages: payment ≠ credits (bonus credits on higher tiers)
PACKAGES: dict[str, dict] = {
    "starter": {"payment": 19,  "credits": 10.0,  "plan_key": "sct_plan_starter", "label": "Starter"},
    "popular": {"payment": 50,  "credits": 55.0,  "plan_key": "sct_plan_popular", "label": "Popular"},
    "pro":     {"payment": 100, "credits": 115.0, "plan_key": "sct_plan_pro",     "label": "Pro"},
}


def get_package(package: str) -> dict:
    pkg = PACKAGES.get(package)
    if not pkg:
        raise HTTPException(status_code=400, detail=f"Invalid package '{package}'. Must be one of: {list(PACKAGES)}")
    settings = get_settings()
    plan_code = getattr(settings, pkg["plan_key"], "")
    if not plan_code:
        raise HTTPException(status_code=503, detail=f"Plan not configured for package '{package}'")
    return {**pkg, "plan_code": plan_code}


_PLAN_BY_AMOUNT = {
    10: "sct_plan_10",
    25: "sct_plan_25",
    50: "sct_plan_50",
    100: "sct_plan_100",
    150: "sct_plan_150",
    200: "sct_plan_200",
    300: "sct_plan_300",
}

VALID_AMOUNTS = sorted(_PLAN_BY_AMOUNT.keys())


def get_plan_code_for_amount(amount: int) -> str:
    if amount not in _PLAN_BY_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid amount ${amount}. Must be one of: {VALID_AMOUNTS}",
        )
    settings = get_settings()
    plan_code = getattr(settings, _PLAN_BY_AMOUNT[amount], "")
    if not plan_code:
        raise HTTPException(
            status_code=503,
            detail=f"CardTransaction plan code not configured for ${amount}",
        )
    return plan_code


def is_test_mode_request(headers: dict) -> bool:
    settings = get_settings()
    mode_header = headers.get("x-mode", "")
    if not mode_header:
        return False

    accepted_keys = [key for key in [settings.test_mode_key, settings.sct_test_mode_key] if key]
    if not accepted_keys:
        raise HTTPException(status_code=503, detail="Test mode is not configured")

    if mode_header in accepted_keys:
        return True

    raise HTTPException(status_code=403, detail="Unauthorized: Invalid test mode credentials")


def _resolve_mode(is_test: bool) -> str:
    if not is_test:
        return ""
    return get_settings().sct_test_mode_key or ""


def _is_success(payload: dict) -> bool:
    val = payload.get("success")
    return val == "1" or val == 1 or val is True


def _shared_headers() -> dict:
    return {
        "Authorization": f"Bearer {get_settings().sct_api_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


async def generate_payment_link(
    *,
    email: str,
    plan_code: str,
    meta_data: dict,
    callback_url: str,
    is_test: bool,
) -> dict:
    settings = get_settings()
    if not settings.sct_api_key or not settings.sct_project_code or not settings.sct_merchant_code:
        raise HTTPException(status_code=503, detail="CardTransaction not configured")

    mode_value = _resolve_mode(is_test)
    body = {
        "email": email,
        "project_code": settings.sct_project_code,
        "plan_code": plan_code,
        "merchant_code": settings.sct_merchant_code,
        "mode": mode_value,
        "meta_data": json.dumps(meta_data),
        "callback_url": callback_url,
    }

    print(f"[SCT] gen-payment-link | is_test={is_test} | mode='{mode_value}' | plan_code={plan_code}")

    client = get_http_client()
    resp = await client.post(
        f"{settings.sct_api_url}/api/gen-payment-link",
        data=body,
        headers=_shared_headers(),
    )

    print(f"[SCT] gen-payment-link response: {resp.status_code} | {resp.text[:300]}")

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"CardTransaction gen-payment-link failed: {resp.text}",
        )

    payload = resp.json()
    if not _is_success(payload):
        raise HTTPException(
            status_code=502,
            detail=payload.get("message") or "CardTransaction declined the request",
        )

    return {
        "url": payload.get("data", ""),
        "request_code": payload.get("request_code", ""),
    }


async def get_request_code(request_code: str) -> dict:
    settings = get_settings()
    body = {
        "request_code": request_code,
        "project_code": settings.sct_project_code,
    }

    client = get_http_client()
    resp = await client.post(
        f"{settings.sct_api_url}/api/get-request-code",
        data=body,
        headers=_shared_headers(),
    )

    if resp.status_code >= 400:
        return {"success": False, "raw": resp.text}

    payload = resp.json()
    if not _is_success(payload):
        return {"success": False, "raw": payload}

    result = payload.get("data") or {}
    return {
        "success": True,
        "meta_data": _maybe_parse_json(result.get("meta_data")),
        "payment_data": _maybe_parse_json(result.get("payment_data")),
        "subscription_data": _maybe_parse_json(result.get("subscription_data")),
        "customer_code": result.get("customer_code"),
        "subscription_code": result.get("subscription_code"),
        "plan_code": result.get("plan_code"),
        "email": result.get("email"),
    }


def _maybe_parse_json(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}
