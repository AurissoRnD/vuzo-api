from fastapi import HTTPException
from app.models.database import get_supabase


def get_balance(user_id: str) -> float:
    sb = get_supabase()
    result = sb.table("credits").select("balance").eq("user_id", user_id).execute()
    if not result.data:
        sb.table("credits").insert({"user_id": user_id, "balance": 0}).execute()
        return 0.0
    return float(result.data[0]["balance"])


def check_sufficient_balance(user_id: str, min_amount: float = 0.05) -> float:
    """
    Check that the user has at least min_amount in credits.
    Returns the current balance. Raises 402 if insufficient.
    """
    balance = get_balance(user_id)
    if balance < min_amount:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits (${balance:.4f}). Please top up at your SimplerClaw dashboard to continue.",
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


def add_credits(
    user_id: str,
    amount: float,
    description: str = "Credit top-up",
    payment_amount: float | None = None,
) -> tuple[float, str]:
    """
    Add credits to the user's balance.
    - amount: credits added (what the user gets)
    - payment_amount: actual cash received (may differ for package purchases)
    Returns (new_balance, transaction_id).
    """
    sb = get_supabase()

    current = get_balance(user_id)
    new_balance = current + amount

    sb.table("credits").update(
        {"balance": new_balance, "updated_at": "now()"}
    ).eq("user_id", user_id).execute()

    tx_row: dict = {
        "user_id": user_id,
        "amount": amount,
        "type": "topup",
        "description": description,
    }
    if payment_amount is not None:
        tx_row["payment_amount"] = payment_amount

    tx_result = sb.table("credit_transactions").insert(tx_row).execute()

    tx_id = tx_result.data[0]["id"] if tx_result.data else ""
    return new_balance, tx_id


def get_total_topups(user_id: str) -> float:
    """Sum of all topup transactions for a user (lifetime)."""
    sb = get_supabase()
    result = (
        sb.table("credit_transactions")
        .select("amount")
        .eq("user_id", user_id)
        .eq("type", "topup")
        .execute()
    )
    return sum(float(t["amount"]) for t in (result.data or []))


def get_balance_after_last_topup(user_id: str, current_balance: float) -> float:
    """
    Reconstruct the balance immediately after the user's last topup.
    Formula: current_balance + sum of all usage debits since last topup.
    Used to calculate the low-balance threshold on a per-cycle basis.
    Returns 0 if no topup exists.
    """
    sb = get_supabase()

    last_topup = (
        sb.table("credit_transactions")
        .select("created_at")
        .eq("user_id", user_id)
        .eq("type", "topup")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not last_topup.data:
        return 0.0

    last_topup_time = last_topup.data[0]["created_at"]

    usage_since = (
        sb.table("credit_transactions")
        .select("amount")
        .eq("user_id", user_id)
        .eq("type", "usage")
        .gte("created_at", last_topup_time)
        .execute()
    )

    spent_since_topup = sum(abs(float(t["amount"])) for t in (usage_since.data or []))
    return current_balance + spent_since_topup


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
