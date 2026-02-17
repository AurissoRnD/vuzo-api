from fastapi import APIRouter

from app.models.schemas import ModelPricingItem
from app.services.pricing_service import get_all_models

router = APIRouter()


@router.get("/models", response_model=list[ModelPricingItem])
async def list_models():
    """List all available models with Vuzo pricing (public endpoint)."""
    rows = get_all_models()
    result = []
    for r in rows:
        inp = float(r["input_price_per_million"])
        out = float(r["output_price_per_million"])
        markup = float(r["vuzo_markup_percent"])
        multiplier = 1 + markup / 100

        result.append(
            ModelPricingItem(
                provider=r["provider"],
                model_name=r["model_name"],
                input_price_per_million=inp,
                output_price_per_million=out,
                vuzo_input_price_per_million=round(inp * multiplier, 4),
                vuzo_output_price_per_million=round(out * multiplier, 4),
                vuzo_markup_percent=markup,
            )
        )
    return result
