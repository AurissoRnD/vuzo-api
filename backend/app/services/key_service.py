from app.models.database import get_supabase
from app.utils.crypto import generate_api_key, get_key_prefix, hash_api_key


def create_api_key(user_id: str, name: str = "Default", token_limit: int | None = None) -> dict:
    """
    Generate a new Vuzo API key for a user.
    Returns dict with id, name, key (plaintext, shown once), key_prefix, created_at.
    """
    raw_key = generate_api_key()
    prefix = get_key_prefix(raw_key)
    hashed = hash_api_key(raw_key)

    row_data: dict = {
        "user_id": user_id,
        "key_prefix": prefix,
        "key_hash": hashed,
        "name": name,
    }
    if token_limit is not None:
        row_data["token_limit"] = token_limit

    sb = get_supabase()
    result = sb.table("api_keys").insert(row_data).execute()

    row = result.data[0]
    return {
        "id": row["id"],
        "name": row["name"],
        "key": raw_key,
        "key_prefix": prefix,
        "created_at": row["created_at"],
    }


def list_api_keys(user_id: str) -> list[dict]:
    """List all API keys for a user, including token_limit and tokens_used."""
    sb = get_supabase()
    result = (
        sb.table("api_keys")
        .select("id, name, key_prefix, is_active, rate_limit_rpm, token_limit, created_at, last_used_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    keys = result.data or []

    if not keys:
        return keys

    key_ids = [k["id"] for k in keys]
    usage = (
        sb.table("usage_logs")
        .select("api_key_id, total_tokens")
        .in_("api_key_id", key_ids)
        .execute()
    )
    tokens_by_key: dict[str, int] = {}
    for row in (usage.data or []):
        tokens_by_key[row["api_key_id"]] = tokens_by_key.get(row["api_key_id"], 0) + row["total_tokens"]

    for k in keys:
        k["tokens_used"] = tokens_by_key.get(k["id"], 0)

    return keys


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
