from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.database import get_supabase
from app.config import get_settings
from app.dependencies import get_current_user_id
from app.services.key_service import create_api_key
from app.services.pricing_service import get_all_models

router = APIRouter()

VUZO_API_BASE_URL = "https://vuzo-api.onrender.com/v1"


class InstallerRequest(BaseModel):
    email: str
    password: str
    key_name: str = "OpenClaw"


def _starter_grant_already_given(sb, user_id: str) -> bool:
    """Return True if this user has already received the free starter allowance."""
    result = (
        sb.table("credit_transactions")
        .select("id")
        .eq("user_id", user_id)
        .eq("type", "topup")
        .ilike("description", "%starter allowance%")
        .limit(1)
        .execute()
    )
    return bool(result.data)


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

    return create_api_key(user_id=user_id, name=key_name)["key"]


@router.post("/setup/installer")
async def setup_installer(body: InstallerRequest):
    """
    Login or auto-register a user, create an API key, and return everything
    needed for the SimplerClaw installer to configure OpenClaw.
    """
    settings = get_settings()
    from supabase import create_client, AuthApiError

    sb_auth = create_client(settings.supabase_url, settings.supabase_key)
    sb = get_supabase()

    # --- Step 1: Try login first, fall back to register ---
    supabase_uid = None
    supabase_session = None
    try:
        auth_response = sb_auth.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })
        if auth_response.user:
            supabase_uid = auth_response.user.id
            supabase_session = auth_response.session
    except Exception:
        pass

    if not supabase_uid:
        # Account doesn't exist — auto-register
        try:
            auth_response = sb_auth.auth.sign_up({
                "email": body.email,
                "password": body.password,
            })
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Could not create account. Please try again.")

        supabase_uid = auth_response.user.id
        supabase_session = auth_response.session

        # Create Vuzo user + credits row
        existing = (
            sb.table("users")
            .select("id")
            .eq("supabase_auth_id", supabase_uid)
            .execute()
        )
        if not existing.data:
            new_user = (
                sb.table("users")
                .insert({
                    "supabase_auth_id": supabase_uid,
                    "email": body.email,
                    "name": body.email.split("@")[0],
                })
                .execute()
            )
            if new_user.data:
                uid = new_user.data[0]["id"]
                sb.table("credits").insert({
                    "user_id": uid,
                    "balance": 1.00,
                }).execute()
                sb.table("credit_transactions").insert({
                    "user_id": uid,
                    "amount": 1.00,
                    "type": "topup",
                    "description": "Free starter allowance — SimplerClaw installer",
                }).execute()

    # --- Step 2: Get the internal user id ---
    user_row = (
        sb.table("users")
        .select("id")
        .eq("supabase_auth_id", supabase_uid)
        .execute()
    )
    if not user_row.data:
        raise HTTPException(status_code=500, detail="User record not found after auth.")

    internal_user_id = user_row.data[0]["id"]

    # --- Step 2b: Grant starter credits exactly once ---
    # Check transaction history — not current balance — so draining to $0 and
    # re-running the installer cannot farm the grant a second time.
    if not _starter_grant_already_given(sb, internal_user_id):
        credits_row = (
            sb.table("credits")
            .select("balance")
            .eq("user_id", internal_user_id)
            .execute()
        )
        if credits_row.data:
            sb.table("credits").update({"balance": 1.00}).eq("user_id", internal_user_id).execute()
        else:
            sb.table("credits").insert({"user_id": internal_user_id, "balance": 1.00}).execute()

        sb.table("credit_transactions").insert({
            "user_id": internal_user_id,
            "amount": 1.00,
            "type": "topup",
            "description": "Free starter allowance — SimplerClaw installer",
        }).execute()

    # --- Step 3: Rotate the OpenClaw key ---
    api_key = _rotate_openclaw_key(sb, internal_user_id, body.key_name)

    # --- Step 4: Fetch available model ids ---
    model_rows = get_all_models()
    model_ids = [r["model_name"] for r in model_rows]

    # --- Step 5: Build the ready-to-use OpenClaw config snippet ---
    openclaw_config = {
        "base_url": VUZO_API_BASE_URL,
        "provider_name": "vuzo",
        "models": model_ids,
    }

    # Build dashboard URL with session tokens in hash so Supabase JS auto-authenticates
    # the WKWebView without requiring the user to log in again.
    dashboard_url = "https://vuzo-api-1.onrender.com"
    if supabase_session:
        dashboard_url = (
            f"https://vuzo-api-1.onrender.com"
            f"#access_token={supabase_session.access_token}"
            f"&refresh_token={supabase_session.refresh_token}"
            f"&token_type=bearer"
            f"&type=signup"
        )

    return {
        "api_key": api_key,
        "models": model_ids,
        "openclaw_config": openclaw_config,
        "dashboard_url": dashboard_url,
    }


@router.post("/setup/rotate-key")
async def rotate_key(
    key_name: str = "OpenClaw",
    user_id: str = Depends(get_current_user_id),
):
    """
    Revoke the user's current named API key and issue a fresh one.
    Authenticate with a Supabase JWT (from /v1/auth/login) — not the vz-sk key
    being rotated, since that may be compromised.
    Returns the new key and a ready-to-paste OpenClaw config snippet.
    """
    sb = get_supabase()
    api_key = _rotate_openclaw_key(sb, user_id, key_name)

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
