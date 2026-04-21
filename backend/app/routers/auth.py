from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter()


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    """Refresh an expired Supabase session token."""
    settings = get_settings()
    from supabase import create_client

    sb_auth = create_client(settings.supabase_url, settings.supabase_key)

    try:
        auth_response = sb_auth.auth.refresh_session(body.refresh_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    if not auth_response.session:
        raise HTTPException(status_code=401, detail="Could not refresh session")

    return {
        "access_token": auth_response.session.access_token,
        "refresh_token": auth_response.session.refresh_token,
        "expires_in": auth_response.session.expires_in,
    }
