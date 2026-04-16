from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.database import get_supabase
from app.config import get_settings
from app.services.key_service import create_api_key
from app.services.pricing_service import get_all_models

router = APIRouter()

VUZO_API_BASE_URL = "https://vuzo-api.onrender.com/v1"


class InstallerRequest(BaseModel):
    email: str
    password: str
    key_name: str = "OpenClaw"


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
                    "balance": 1.00,  # ~500k tokens on mid-range models (free starter allowance)
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

    # --- Step 2b: Grant starter credits if balance is still $0 ---
    # Covers the case where a user registered via /auth/register (which gives $0)
    # and then comes through the installer. Only grant once.
    credits_row = (
        sb.table("credits")
        .select("balance")
        .eq("user_id", internal_user_id)
        .execute()
    )
    current_balance = credits_row.data[0]["balance"] if credits_row.data else 0

    if current_balance == 0:
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

    # --- Step 3: Reuse existing OpenClaw key if present, otherwise create one ---
    # Keys are hashed and cannot be retrieved after creation, so if one already
    # exists we revoke it and issue a fresh one. This prevents key accumulation
    # when a user re-runs the installer.
    existing_keys = (
        sb.table("api_keys")
        .select("id")
        .eq("user_id", internal_user_id)
        .eq("name", body.key_name)
        .eq("is_active", True)
        .execute()
    )
    if existing_keys.data:
        old_key_id = existing_keys.data[0]["id"]
        sb.table("api_keys").update({"is_active": False}).eq("id", old_key_id).execute()

    key_data = create_api_key(user_id=internal_user_id, name=body.key_name)
    api_key = key_data["key"]

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
