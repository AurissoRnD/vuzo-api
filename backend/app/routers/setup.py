import re
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client, AuthApiError

from app.models.database import get_supabase
from app.config import get_settings
from app.services.key_service import create_api_key
from app.services.pricing_service import get_all_models

router = APIRouter()

VUZO_API_BASE_URL = "https://vuzo-api.onrender.com/v1"
WEB_PACKAGE_IDS = {"starter", "popular", "pro"}


class InstallerRequest(BaseModel):
    type: Literal["register", "login"]
    email: str
    password: str
    key_name: str = "OpenClaw"



def _rotate_openclaw_key(sb, user_id: str, key_name: str) -> str:
    """Revoke the existing named key (if any) and issue a fresh one. Returns the new plaintext key."""
    existing = (
        sb.table("api_keys")
        .select("id")
        .eq("user_id", user_id)
        .eq("name", key_name)
        .eq("is_active", True)
        .execute()
    )
    if existing.data:
        sb.table("api_keys").update({"is_active": False}).eq("id", existing.data[0]["id"]).execute()

    return create_api_key(user_id=user_id, name=key_name, token_limit=None)["key"]


def _extract_package_from_description(description: str) -> str | None:
    match = re.search(r"Package purchase \(([^)]+)\)", description or "")
    if not match:
        return None
    package = match.group(1).strip().lower()
    return package or None


def _get_web_payment_status(sb, user_id: str) -> dict:
    """
    Return whether the user has completed a valid web package payment
    (starter/popular/pro) and the latest matching transaction metadata.
    """
    result = (
        sb.table("credit_transactions")
        .select("id, amount, payment_amount, description, created_at")
        .eq("user_id", user_id)
        .eq("type", "topup")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    if not result.data:
        return {
            "has_paid_via_web": False,
            "latest": None,
        }

    latest = None
    package_name = None
    for row in result.data:
        parsed_package = _extract_package_from_description(row.get("description", ""))
        if parsed_package in WEB_PACKAGE_IDS:
            latest = row
            package_name = parsed_package
            break

    if latest is None:
        return {
            "has_paid_via_web": False,
            "latest": None,
        }

    return {
        "has_paid_via_web": True,
        "latest": {
            "transaction_id": latest.get("id"),
            "package": package_name,
            "credits_amount": latest.get("amount"),
            "payment_amount": latest.get("payment_amount"),
            "paid_at": latest.get("created_at"),
        },
    }


@router.post("/setup/installer")
async def setup_installer(body: InstallerRequest):
    """
    Explicit register or login flow for the SimplerClaw installer.
    - type=register: create account + fresh OpenClaw key (fails if email exists)
    - type=login: sign in + always rotate OpenClaw key (revoke old, issue new)
    """
    settings = get_settings()
    sb_auth = create_client(settings.supabase_url, settings.supabase_key)

    supabase_uid: str | None = None
    supabase_session = None
    internal_user_id: str | None = None

    if body.type == "register":
        # --- Register: fail if account already exists ---
        try:
            auth_response = sb_auth.auth.sign_up({
                "email": body.email,
                "password": body.password,
            })
        except AuthApiError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Could not create account. Please try again.")

        # Supabase sign_up succeeds even if email exists (returns user but no session)
        # when email confirmation is disabled. Detect this by checking for a session.
        if not auth_response.session:
            raise HTTPException(status_code=400, detail="An account with this email already exists. Use type=login instead.")

        supabase_uid = auth_response.user.id
        supabase_session = auth_response.session

        # Create internal user + credits row
        sb = get_supabase()
        existing = sb.table("users").select("id").eq("supabase_auth_id", supabase_uid).execute()
        if not existing.data:
            new_user = sb.table("users").insert({
                "supabase_auth_id": supabase_uid,
                "email": body.email,
                "name": body.email.split("@")[0],
            }).execute()
            if new_user.data:
                uid = new_user.data[0]["id"]
                sb.table("credits").insert({"user_id": uid, "balance": 0.00}).execute()

    else:
        # --- Login: fail if credentials are wrong ---
        try:
            auth_response = sb_auth.auth.sign_in_with_password({
                "email": body.email,
                "password": body.password,
            })
        except AuthApiError:
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        supabase_uid = auth_response.user.id
        supabase_session = auth_response.session
        sb = get_supabase()

        # --- Single-device enforcement ---
        # If an older session is still active, revoke it and let this login continue.
        user_row = (
            sb.table("users")
            .select("id, active_refresh_token")
            .eq("supabase_auth_id", supabase_uid)
            .execute()
        )
        if not user_row.data:
            raise HTTPException(status_code=500, detail="User record not found after auth.")

        internal_user_id = user_row.data[0]["id"]
        stored_token = user_row.data[0].get("active_refresh_token")

        if stored_token:
            try:
                check = sb_auth.auth.refresh_session(stored_token)
                if check.session:
                    # Revoke prior active session so this login becomes the single active device.
                    try:
                        sb_auth.auth.admin.sign_out(check.session.access_token)
                    except Exception:
                        pass
            except AuthApiError:
                pass  # Stored token is dead — allow login

    # --- Get internal user id (resolved above for login; look up now for register) ---
    if internal_user_id is None:
        user_row = sb.table("users").select("id").eq("supabase_auth_id", supabase_uid).execute()
        if not user_row.data:
            raise HTTPException(status_code=500, detail="User record not found after auth.")
        internal_user_id = user_row.data[0]["id"]

    # --- Persist active session so future logins from other devices are blocked ---
    sb.table("users").update({"active_refresh_token": supabase_session.refresh_token}).eq("id", internal_user_id).execute()

    # --- Issue API key ---
    # register → create fresh key
    # login    → always rotate (revoke old, issue new with fresh 500K limit)
    if body.type == "register":
        api_key = create_api_key(user_id=internal_user_id, name=body.key_name, token_limit=None)["key"]
    else:
        api_key = _rotate_openclaw_key(sb, internal_user_id, body.key_name)

    # --- Build response ---
    model_rows = get_all_models()
    model_ids = [r["model_name"] for r in model_rows]

    openclaw_config = {
        "base_url": VUZO_API_BASE_URL,
        "provider_name": "vuzo",
        "models": model_ids,
    }

    dashboard_url = "https://vuzo-api-1.onrender.com"
    if supabase_session:
        dashboard_url = (
            f"https://vuzo-api-1.onrender.com"
            f"#refresh_token={supabase_session.refresh_token}"
        )

    web_payment = _get_web_payment_status(sb, internal_user_id)

    return {
        "api_key": api_key,
        "models": model_ids,
        "openclaw_config": openclaw_config,
        "dashboard_url": dashboard_url,
        "web_payment": web_payment,
        "session": {
            "access_token": supabase_session.access_token,
            "refresh_token": supabase_session.refresh_token,
            "expires_in": supabase_session.expires_in,
        } if supabase_session else None,
    }


class SignOutRequest(BaseModel):
    refresh_token: str
    redirect_url: str | None = None


@router.post("/setup/signout")
async def setup_signout(body: SignOutRequest):
    """
    Invalidate the user's Supabase session using the refresh token.
    Refresh tokens last weeks, unlike access tokens which expire in 3600s.
    Pass redirect_url to tell the caller where to send the user after signout.
    """
    settings = get_settings()
    sb_auth = create_client(settings.supabase_url, settings.supabase_key)

    try:
        refreshed = sb_auth.auth.refresh_session(body.refresh_token)
        if refreshed.session:
            sb_auth.auth.admin.sign_out(refreshed.session.access_token)
    except Exception:
        pass  # treat any error as success — session is already invalid or expired

    # Clear the stored active session so the user can log in from another device
    sb = get_supabase()
    sb.table("users").update({"active_refresh_token": None}).eq("active_refresh_token", body.refresh_token).execute()

    return {
        "message": "Signed out successfully",
        "redirect_url": body.redirect_url,
    }


class RotateKeyRequest(BaseModel):
    email: str
    password: str
    key_name: str = "OpenClaw"


@router.post("/setup/rotate-key")
async def rotate_key(body: RotateKeyRequest):
    """
    Authenticate with email + password, revoke the existing named key, and
    issue a fresh one. No JWT required — credentials are in the request body,
    so this works even if the session from the installer has expired.
    """
    settings = get_settings()
    sb_auth = create_client(settings.supabase_url, settings.supabase_key)

    try:
        auth_response = sb_auth.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not auth_response.user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    sb = get_supabase()
    user_row = (
        sb.table("users")
        .select("id")
        .eq("supabase_auth_id", auth_response.user.id)
        .execute()
    )
    if not user_row.data:
        raise HTTPException(status_code=404, detail="User not found.")

    internal_user_id = user_row.data[0]["id"]
    api_key = _rotate_openclaw_key(sb, internal_user_id, body.key_name)

    model_rows = get_all_models()
    model_ids = [r["model_name"] for r in model_rows]

    return {
        "api_key": api_key,
        "models": model_ids,
        "openclaw_config": {
            "base_url": VUZO_API_BASE_URL,
            "provider_name": "vuzo",
            "models": model_ids,
        },
    }
