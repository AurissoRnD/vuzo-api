from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.utils.crypto import get_key_prefix, hash_api_key
from app.models.database import get_supabase
from app.models.schemas import AuthContext

security = HTTPBearer()


async def validate_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> AuthContext:
    """
    Dependency that validates a Vuzo API key from the Authorization header.
    Returns an AuthContext with user_id, api_key_id, and rate_limit_rpm.
    """
    token = credentials.credentials

    if not token.startswith("vz-"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    prefix = get_key_prefix(token)
    key_hash = hash_api_key(token)

    sb = get_supabase()
    result = (
        sb.table("api_keys")
        .select("id, user_id, key_hash, is_active, rate_limit_rpm")
        .eq("key_prefix", prefix)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid API key")

    matched_key = None
    for row in result.data:
        if row["key_hash"] == key_hash:
            matched_key = row
            break

    if matched_key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not matched_key["is_active"]:
        raise HTTPException(status_code=403, detail="API key has been revoked")

    user_result = (
        sb.table("users")
        .select("is_active")
        .eq("id", matched_key["user_id"])
        .single()
        .execute()
    )
    if not user_result.data or not user_result.data["is_active"]:
        raise HTTPException(status_code=403, detail="User account is inactive")

    sb.table("api_keys").update({"last_used_at": "now()"}).eq(
        "id", matched_key["id"]
    ).execute()

    return AuthContext(
        user_id=matched_key["user_id"],
        api_key_id=matched_key["id"],
        rate_limit_rpm=matched_key["rate_limit_rpm"],
    )
