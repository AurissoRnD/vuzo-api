from fastapi import HTTPException
from app.models.database import get_supabase
from app.utils.crypto import decrypt_provider_key


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
    Retrieve and decrypt the master API key for a provider.
    Raises 503 if provider key is not configured.
    """
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
    return decrypt_provider_key(result.data[0]["api_key_encrypted"])
