from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListItem,
)
from app.dependencies import get_current_user_id
from app.services.key_service import create_api_key, list_api_keys, revoke_api_key

router = APIRouter()


@router.post("", response_model=APIKeyCreateResponse)
async def create_key(
    body: APIKeyCreateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Create a new Vuzo API key. The full key is returned only once."""
    result = create_api_key(user_id, body.name)
    return APIKeyCreateResponse(**result)


@router.get("", response_model=list[APIKeyListItem])
async def list_keys(user_id: str = Depends(get_current_user_id)):
    """List all API keys for the authenticated user."""
    return list_api_keys(user_id)


@router.delete("/{key_id}")
async def delete_key(
    key_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Revoke an API key."""
    success = revoke_api_key(user_id, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key revoked", "key_id": key_id}
