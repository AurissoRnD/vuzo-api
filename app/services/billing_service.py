from fastapi import HTTPException
from app.models.database import get_supabase


def get_balance(user_id: str) -> float:
    sb = get_supabase()
    result = sb.table("credits").select("balance").eq("user_id", user_id).execute()
    if not result.data:
        sb.table("credits").insert({"user_id": user_id, "balance": 0}).execute()
        return 0.0
    return float(result.data[0]["balance"])


def check_sufficient_balance(user_id: str, min_amount: float = 0.001) -> float:
    """
    Check that the user has at least min_amount in credits.
    Returns the current balance. Raises 402 if insufficient.
    """
    balance = get_balance(user_id)
    if balance < min_amount:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Balance: ${balance:.6f}. Please top up.",
        )
    return balance


def deduct_credits(user_id: str, amount: float, description: str) -> float:
    """
    Deduct credits from the user's balance and record a transaction.
    Returns the new balance.
    """
    sb = get_supabase()

    current = get_balance(user_id)
    new_balance = current - amount

    sb.table("credits").update(
        {"balance": new_balance, "updated_at": "now()"}
    ).eq("user_id", user_id).execute()

    sb.table("credit_transactions").insert({
        "user_id": user_id,
        "amount": -amount,
        "type": "usage",
        "description": description,
    }).execute()

    return new_balance


def add_credits(user_id: str, amount: float, description: str = "Credit top-up") -> tuple[float, str]:
    """
    Add credits to the user's balance.
    Returns (new_balance, transaction_id).
    """
    sb = get_supabase()

    current = get_balance(user_id)
    new_balance = current + amount

    sb.table("credits").update(
        {"balance": new_balance, "updated_at": "now()"}
    ).eq("user_id", user_id).execute()

    tx_result = sb.table("credit_transactions").insert({
        "user_id": user_id,
        "amount": amount,
        "type": "topup",
        "description": description,
    }).execute()

    tx_id = tx_result.data[0]["id"] if tx_result.data else ""
    return new_balance, tx_id


def get_transactions(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    sb = get_supabase()
    result = (
        sb.table("credit_transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data or []
