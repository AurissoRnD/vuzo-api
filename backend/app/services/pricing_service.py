from fastapi import HTTPException
from app.models.database import get_supabase
from app.utils.crypto import decrypt_provider_key
from app.config import get_settings
from cryptography.fernet import InvalidToken

_PROVIDER_ENV_KEYS = {
    "moonshot": lambda s: s.moonshot_api_key,
}


def get_model_pricing(model_name: str) -> dict:
    """
    Fetch pricing info for a model from the database.
    Returns dict with provider, model_name, input/output prices, and markup.
    Raises 400 if model not found or inactive.
    """
    sb = get_supabase()
    result = (
        sb.table("model_pricing")
        .select("*")
        .eq("model_name", model_name)
        .eq("is_active", True)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model_name}' is not available. Use GET /v1/models to see supported models.",
        )
    return result.data[0]


def get_all_models() -> list[dict]:
    """Fetch all active model pricing entries."""
    sb = get_supabase()
    result = (
        sb.table("model_pricing")
        .select("*")
        .eq("is_active", True)
        .order("provider")
        .execute()
    )
    return result.data or []


def get_provider_api_key(provider: str) -> str:
    """
    Retrieve the master API key for a provider.
    Checks env var first, falls back to encrypted DB entry.
    Raises 503 if neither is configured.
    """
    # Env var takes priority
    env_getter = _PROVIDER_ENV_KEYS.get(provider)
    if env_getter:
        key = env_getter(get_settings())
        if key:
            return key

    # Fall back to encrypted DB entry
    sb = get_supabase()
    result = (
        sb.table("provider_keys")
        .select("api_key_encrypted")
        .eq("provider", provider)
        .eq("is_active", True)
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=503,
            detail=f"Provider '{provider}' is not configured. Contact Vuzo support.",
        )
    try:
        return decrypt_provider_key(result.data[0]["api_key_encrypted"])
    except InvalidToken:
        raise HTTPException(
            status_code=503,
            detail=f"Provider '{provider}' key is corrupted or encryption key mismatch. Contact Vuzo support.",
        )
