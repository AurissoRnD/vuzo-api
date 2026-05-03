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

    # Package plans (payment ≠ credits)
    sct_plan_starter: str = ""   # $19 payment → $10 credits
    sct_plan_popular: str = ""   # $50 payment → $55 credits
    sct_plan_pro: str = ""       # $100 payment → $115 credits
    web_app_url: str = "http://localhost:3000"  # SimplerClaw web app URL

    # Frontend URL for CORS
    frontend_url: str = "http://localhost:5173"

    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
