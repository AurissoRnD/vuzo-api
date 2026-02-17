from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.middleware.auth import validate_api_key
from app.middleware.jwt_auth import validate_session
from app.models.schemas import AuthContext

security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """
    Unified auth dependency that works with BOTH Vuzo API keys and Supabase JWTs.
    - If the token starts with "vz-" -> validates as Vuzo API key, returns user_id
    - Otherwise -> validates as Supabase JWT, returns user_id
    """
    token = credentials.credentials

    if token.startswith("vz-"):
        auth_ctx = await validate_api_key(credentials)
        return auth_ctx.user_id
    else:
        user_id = await validate_session(credentials)
        return user_id
