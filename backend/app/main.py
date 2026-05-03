from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import proxy, api_keys, usage, billing, models_list, auth, setup, admin, cardtransaction, ws
from app.models.database import init_supabase, close_http_client
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_supabase()
    yield
    await close_http_client()


app = FastAPI(
    title="Vuzo API",
    description="Unified LLM API proxy -- one key for OpenAI, Grok, and Gemini.",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        settings.web_app_url,
        "http://localhost:5173",
        "http://localhost:3000",
        "https://vuzo-dashboard.onrender.com",
        "https://vuzo-api-1.onrender.com",
        "https://simpler-claw-web-staging.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimiterMiddleware)

app.include_router(proxy.router, prefix="/v1", tags=["LLM Proxy"])
app.include_router(auth.router, prefix="/v1/auth", tags=["Auth"])
app.include_router(api_keys.router, prefix="/v1/api-keys", tags=["API Keys"])
app.include_router(usage.router, prefix="/v1/usage", tags=["Usage"])
app.include_router(billing.router, prefix="/v1/billing", tags=["Billing"])
app.include_router(cardtransaction.router, prefix="/v1", tags=["Payments"])
app.include_router(models_list.router, prefix="/v1", tags=["Models"])
app.include_router(setup.router, prefix="/v1", tags=["Setup"])
app.include_router(admin.router, prefix="/v1", tags=["Admin"])
app.include_router(ws.router, prefix="/v1", tags=["WebSocket"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "vuzo-api"}
