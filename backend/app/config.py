from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str = ""
    provider_encryption_key: str

    # Polar payment integration
    polar_access_token: str = ""
    polar_webhook_secret: str = ""
    polar_sandbox: bool = False  # set to true to use sandbox-api.polar.sh instead of api.polar.sh
    # Polar product IDs — set these in .env, never exposed to the frontend
    polar_product_10: str = ""
    polar_product_30: str = ""
    polar_product_50: str = ""
    polar_product_custom: str = ""  # "Pay what you want" product for custom amounts

    # Frontend URL for CORS
    frontend_url: str = "http://localhost:5173"

    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
