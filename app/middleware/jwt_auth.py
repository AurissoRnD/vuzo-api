from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings
from app.models.database import get_supabase

security = HTTPBearer()


async def validate_session(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """
    Validate a Supabase JWT from the Authorization header.
    Uses Supabase's own auth.get_user() for reliable server-side verification.
    Returns the Vuzo user_id (not the Supabase auth UUID).

    Creates a Vuzo user + credits row on first login if none exists.
    """
    token = credentials.credentials
    settings = get_settings()

    from supabase import create_client

    sb_auth = create_client(settings.supabase_url, settings.supabase_key)

    try:
        user_response = sb_auth.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not user_response or not user_response.user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    supabase_uid = user_response.user.id
    email = user_response.user.email or ""

    sb = get_supabase()
    result = (
        sb.table("users")
        .select("id, is_active")
        .eq("supabase_auth_id", supabase_uid)
        .execute()
    )

    if result.data:
        user = result.data[0]
        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="User account is inactive")
        return user["id"]

    new_user = (
        sb.table("users")
        .insert({
            "supabase_auth_id": supabase_uid,
            "email": email,
            "name": email.split("@")[0] if email else "",
        })
        .execute()
    )
    if not new_user.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user_id = new_user.data[0]["id"]

    sb.table("credits").insert({"user_id": user_id, "balance": 0}).execute()

    return user_id
