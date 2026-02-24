from app.models.database import get_supabase
from app.utils.crypto import generate_api_key, get_key_prefix, hash_api_key


def create_api_key(user_id: str, name: str = "Default") -> dict:
    """
    Generate a new Vuzo API key for a user.
    Returns dict with id, name, key (plaintext, shown once), key_prefix, created_at.
    """
    raw_key = generate_api_key()
    prefix = get_key_prefix(raw_key)
    hashed = hash_api_key(raw_key)

    sb = get_supabase()
    result = sb.table("api_keys").insert({
        "user_id": user_id,
        "key_prefix": prefix,
        "key_hash": hashed,
        "name": name,
    }).execute()

    row = result.data[0]
    return {
        "id": row["id"],
        "name": row["name"],
        "key": raw_key,
        "key_prefix": prefix,
        "created_at": row["created_at"],
    }


def list_api_keys(user_id: str) -> list[dict]:
    """List all API keys for a user (without hashes)."""
    sb = get_supabase()
    result = (
        sb.table("api_keys")
        .select("id, name, key_prefix, is_active, rate_limit_rpm, created_at, last_used_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def revoke_api_key(user_id: str, key_id: str) -> bool:
    """Revoke (deactivate) an API key. Returns True if found and revoked."""
    sb = get_supabase()
    result = (
        sb.table("api_keys")
        .update({"is_active": False})
        .eq("id", key_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(result.data)
