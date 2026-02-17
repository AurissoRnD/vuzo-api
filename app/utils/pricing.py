from decimal import Decimal


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_million: float,
    output_price_per_million: float,
    vuzo_markup_percent: float,
) -> tuple[float, float]:
    """
    Calculate provider cost and Vuzo cost (with markup).

    Returns:
        (provider_cost, vuzo_cost) both as floats in USD.
    """
    inp = Decimal(str(input_price_per_million))
    out = Decimal(str(output_price_per_million))
    markup = Decimal(str(vuzo_markup_percent))
    million = Decimal("1000000")

    provider_cost = (Decimal(input_tokens) * inp / million) + (
        Decimal(output_tokens) * out / million
    )
    vuzo_cost = provider_cost * (Decimal("1") + markup / Decimal("100"))

    return float(provider_cost.quantize(Decimal("0.000001"))), float(
        vuzo_cost.quantize(Decimal("0.000001"))
    )
