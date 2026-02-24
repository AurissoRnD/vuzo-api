from fastapi import APIRouter, HTTPException

from app.models.schemas import ModelPricingItem
from app.services.pricing_service import get_all_models

router = APIRouter()


def _row_to_item(r: dict) -> ModelPricingItem:
    inp = float(r["input_price_per_million"])
    out = float(r["output_price_per_million"])
    markup = float(r["vuzo_markup_percent"])
    multiplier = 1 + markup / 100
    return ModelPricingItem(
        provider=r["provider"],
        model_name=r["model_name"],
        input_price_per_million=inp,
        output_price_per_million=out,
        vuzo_input_price_per_million=round(inp * multiplier, 4),
        vuzo_output_price_per_million=round(out * multiplier, 4),
        vuzo_markup_percent=markup,
    )


@router.get("/models", response_model=list[ModelPricingItem])
async def list_models():
    """List all available models with Vuzo pricing (public endpoint)."""
    return [_row_to_item(r) for r in get_all_models()]


@router.get("/models/{model_name}", response_model=ModelPricingItem)
async def get_model(model_name: str):
    """Get pricing details for a single model by name."""
    rows = get_all_models()
    for r in rows:
        if r["model_name"] == model_name:
            return _row_to_item(r)
    raise HTTPException(
        status_code=404,
        detail=f"Model '{model_name}' not found. Use GET /v1/models to see all available models.",
    )
