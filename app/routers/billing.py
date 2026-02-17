from fastapi import APIRouter, Depends, Query

from app.models.schemas import (
    BalanceResponse,
    TopUpRequest,
    TopUpResponse,
    TransactionItem,
)
from app.dependencies import get_current_user_id
from app.services.billing_service import get_balance, add_credits, get_transactions

router = APIRouter()


@router.get("/balance", response_model=BalanceResponse)
async def check_balance(user_id: str = Depends(get_current_user_id)):
    """Check the user's credit balance."""
    balance = get_balance(user_id)
    return BalanceResponse(user_id=user_id, balance=balance)


@router.post("/topup", response_model=TopUpResponse)
async def topup_credits(
    body: TopUpRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Add credits to the user's balance.
    In production, use the Polar checkout flow instead.
    This endpoint is kept for testing / admin use.
    """
    new_balance, tx_id = add_credits(user_id, body.amount)
    return TopUpResponse(
        user_id=user_id,
        amount=body.amount,
        new_balance=new_balance,
        transaction_id=tx_id,
    )


@router.get("/transactions", response_model=list[TransactionItem])
async def list_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
):
    """Get paginated transaction history."""
    return get_transactions(user_id, limit=limit, offset=offset)
