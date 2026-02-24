import httpx
from supabase import create_client, Client
from app.config import get_settings

_supabase: Client | None = None
_http_client: httpx.AsyncClient | None = None


def init_supabase() -> Client:
    global _supabase
    settings = get_settings()
    _supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _supabase


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        return init_supabase()
    return _supabase


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    return _http_client


async def close_http_client():
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
