from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.database import get_supabase
from app.config import get_settings
from app.services.key_service import create_api_key

router = APIRouter()



class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register")
async def register(body: RegisterRequest):
    """
    Register a new user. Creates a Supabase auth account, a Vuzo user record,
    a starter API key, and a 200K token credit allowance ($0.40).
    The API key is returned only once — store it immediately.
    """
    settings = get_settings()
    from supabase import create_client

    sb_auth = create_client(settings.supabase_url, settings.supabase_key)

    try:
        auth_response = sb_auth.auth.sign_up({
            "email": body.email,
            "password": body.password,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not auth_response.user:
        raise HTTPException(status_code=400, detail="Registration failed")

    supabase_uid = auth_response.user.id

    sb = get_supabase()
    existing = (
        sb.table("users")
        .select("id")
        .eq("supabase_auth_id", supabase_uid)
        .execute()
    )

    api_key_data = None

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
            internal_id = new_user.data[0]["id"]

            # No starter credits — free credits are only granted via the installer
            sb.table("credits").insert({
                "user_id": internal_id,
                "balance": 0,
            }).execute()

            # Auto-create a starter API key
            api_key_data = create_api_key(user_id=internal_id, name="Default")

    session_data = None
    if auth_response.session:
        session_data = {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "expires_in": auth_response.session.expires_in,
        }

    return {
        "message": "Registration successful",
        "user_id": supabase_uid,
        "session": session_data,
        "api_key": api_key_data["key"] if api_key_data else None,
    }


@router.post("/login")
async def login(body: LoginRequest):
    """Sign in with email/password via Supabase Auth."""
    settings = get_settings()
    from supabase import create_client

    sb_auth = create_client(settings.supabase_url, settings.supabase_key)

    try:
        auth_response = sb_auth.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    if not auth_response.session:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "access_token": auth_response.session.access_token,
        "refresh_token": auth_response.session.refresh_token,
        "expires_in": auth_response.session.expires_in,
        "user": {
            "id": auth_response.user.id if auth_response.user else None,
            "email": auth_response.user.email if auth_response.user else None,
        },
    }


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
