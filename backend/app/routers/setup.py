from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.database import get_supabase
from app.config import get_settings
from app.services.key_service import create_api_key
from app.services.pricing_service import get_all_models

router = APIRouter()

VUZO_API_BASE_URL = "https://api.vuzo.ai/v1"


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
    try:
        auth_response = sb_auth.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })
        if auth_response.user:
            supabase_uid = auth_response.user.id
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
                sb.table("credits").insert({
                    "user_id": new_user.data[0]["id"],
                    "balance": 0,
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

    # --- Step 3: Create a named API key ---
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

    return {
        "api_key": api_key,
        "models": model_ids,
        "openclaw_config": openclaw_config,
    }
