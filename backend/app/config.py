from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str = ""
    provider_encryption_key: str = ""

    # Provider API keys
    moonshot_api_key: str = ""

    # CardTransaction payment integration
    sct_api_url: str = "https://secure.cardtransaction.com"
    sct_project_code: str = ""
    sct_merchant_code: str = ""
    sct_api_key: str = ""
    sct_test_mode_key: str = ""
    sct_plan_10: str = ""
    sct_plan_25: str = ""
    sct_plan_50: str = ""
    sct_plan_100: str = ""
    sct_plan_150: str = ""
    sct_plan_200: str = ""
    sct_plan_300: str = ""
    test_mode_key: str = ""
    backend_url: str = "http://localhost:8000"

    # Frontend URL for CORS
    frontend_url: str = "http://localhost:5173"

    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
