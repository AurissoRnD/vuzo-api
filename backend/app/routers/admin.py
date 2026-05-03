from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.dependencies import get_current_user_id
from app.models.database import get_supabase
from app.services.key_service import create_api_key

router = APIRouter()


def _require_admin(user_id: str = Depends(get_current_user_id)) -> str:
    sb = get_supabase()
    result = sb.table("users").select("is_admin").eq("id", user_id).single().execute()
    if not result.data or not result.data.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get("/admin/overview")
async def admin_overview(_: str = Depends(_require_admin)):
    sb = get_supabase()

    # Revenue: use payment_amount when set (package purchases), else amount (regular top-ups)
    topups = sb.table("credit_transactions").select("amount, payment_amount, created_at").eq("type", "topup").execute()
    total_revenue = sum(
        float(t["payment_amount"]) if t.get("payment_amount") else float(t["amount"])
        for t in (topups.data or [])
    )
    total_credits_issued = sum(float(t["amount"]) for t in (topups.data or []))

    # Usage costs
    usage_all = sb.table("usage_logs").select("provider_cost, vuzo_cost, total_tokens, created_at").execute()
    usage_data = usage_all.data or []
    total_provider_cost = sum(float(u["provider_cost"]) for u in usage_data)
    total_vuzo_cost = sum(float(u["vuzo_cost"]) for u in usage_data)
    total_tokens = sum(int(u["total_tokens"]) for u in usage_data)
    total_requests = len(usage_data)
    profit = total_vuzo_cost - total_provider_cost
    margin = (profit / total_vuzo_cost * 100) if total_vuzo_cost > 0 else 0

    # User counts
    all_users = sb.table("users").select("id, is_active").execute()
    active_users = sum(1 for u in (all_users.data or []) if u["is_active"])
    total_users = len(all_users.data or [])

    # Key counts
    all_keys = sb.table("api_keys").select("id, is_active").execute()
    active_keys = sum(1 for k in (all_keys.data or []) if k["is_active"])

    # Daily stats (last 30 days)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    daily: dict = {}

    for u in usage_data:
        if u["created_at"] >= cutoff:
            date = u["created_at"][:10]
            if date not in daily:
                daily[date] = {"date": date, "charged": 0.0, "provider_cost": 0.0, "tokens": 0, "requests": 0}
            daily[date]["charged"] += float(u["vuzo_cost"])
            daily[date]["provider_cost"] += float(u["provider_cost"])
            daily[date]["tokens"] += int(u["total_tokens"])
            daily[date]["requests"] += 1

    for t in (topups.data or []):
        if t["created_at"] >= cutoff:
            date = t["created_at"][:10]
            if date not in daily:
                daily[date] = {"date": date, "charged": 0.0, "provider_cost": 0.0, "tokens": 0, "requests": 0, "topups": 0.0}
            if "topups" not in daily[date]:
                daily[date]["topups"] = 0.0
            # Use payment_amount for daily topup chart (actual cash received)
            daily[date]["topups"] += float(t["payment_amount"]) if t.get("payment_amount") else float(t["amount"])

    return {
        "total_revenue": total_revenue,
        "total_credits_issued": total_credits_issued,
        "total_provider_cost": total_provider_cost,
        "total_vuzo_cost": total_vuzo_cost,
        "profit": profit,
        "margin": margin,
        "total_users": total_users,
        "active_users": active_users,
        "active_keys": active_keys,
        "total_tokens": total_tokens,
        "total_requests": total_requests,
        "daily_stats": sorted(daily.values(), key=lambda x: x["date"]),
    }


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/admin/users")
async def admin_users(_: str = Depends(_require_admin)):
    sb = get_supabase()

    users = sb.table("users").select("id, email, is_active, is_admin, created_at").order("created_at", desc=True).execute()
    credits = sb.table("credits").select("user_id, balance").execute()
    keys = sb.table("api_keys").select("user_id, id, is_active").execute()
    usage = sb.table("usage_logs").select("user_id, total_tokens, vuzo_cost").execute()
    topups = sb.table("credit_transactions").select("user_id, amount").eq("type", "topup").execute()

    credit_map = {c["user_id"]: float(c["balance"]) for c in (credits.data or [])}

    keys_map: dict = {}
    for k in (keys.data or []):
        uid = k["user_id"]
        if uid not in keys_map:
            keys_map[uid] = {"total": 0, "active": 0}
        keys_map[uid]["total"] += 1
        if k["is_active"]:
            keys_map[uid]["active"] += 1

    usage_map: dict = {}
    for u in (usage.data or []):
        uid = u["user_id"]
        if uid not in usage_map:
            usage_map[uid] = {"tokens": 0, "cost": 0.0}
        usage_map[uid]["tokens"] += int(u["total_tokens"])
        usage_map[uid]["cost"] += float(u["vuzo_cost"])

    topup_map: dict = {}
    for t in (topups.data or []):
        uid = t["user_id"]
        topup_map[uid] = topup_map.get(uid, 0.0) + float(t["amount"])

    result = []
    for user in (users.data or []):
        uid = user["id"]
        result.append({
            "id": uid,
            "email": user["email"],
            "is_active": user["is_active"],
            "is_admin": user.get("is_admin", False),
            "created_at": user["created_at"],
            "balance": credit_map.get(uid, 0.0),
            "active_keys": keys_map.get(uid, {}).get("active", 0),
            "total_keys": keys_map.get(uid, {}).get("total", 0),
            "total_tokens": usage_map.get(uid, {}).get("tokens", 0),
            "total_spent": usage_map.get(uid, {}).get("cost", 0.0),
            "total_topups": topup_map.get(uid, 0.0),
        })

    return result


class ToggleUserBody(BaseModel):
    is_active: bool


@router.patch("/admin/users/{user_id}")
async def toggle_user(user_id: str, body: ToggleUserBody, _: str = Depends(_require_admin)):
    sb = get_supabase()
    sb.table("users").update({"is_active": body.is_active}).eq("id", user_id).execute()
    return {"success": True}


# ── API Keys ──────────────────────────────────────────────────────────────────

@router.get("/admin/keys")
async def admin_keys(_: str = Depends(_require_admin)):
    sb = get_supabase()

    keys = (
        sb.table("api_keys")
        .select("id, user_id, name, key_prefix, is_active, rate_limit_rpm, token_limit, created_at, last_used_at")
        .order("created_at", desc=True)
        .execute()
    )
    users = sb.table("users").select("id, email").execute()
    user_map = {u["id"]: u["email"] for u in (users.data or [])}

    key_ids = [k["id"] for k in (keys.data or [])]
    usage_map: dict = {}
    if key_ids:
        usage = sb.table("usage_logs").select("api_key_id, total_tokens, vuzo_cost").in_("api_key_id", key_ids).execute()
        for u in (usage.data or []):
            kid = u["api_key_id"]
            if kid not in usage_map:
                usage_map[kid] = {"tokens": 0, "cost": 0.0}
            usage_map[kid]["tokens"] += int(u["total_tokens"])
            usage_map[kid]["cost"] += float(u["vuzo_cost"])

    result = []
    for k in (keys.data or []):
        kid = k["id"]
        result.append({
            **k,
            "user_email": user_map.get(k["user_id"], "Unknown"),
            "tokens_used": usage_map.get(kid, {}).get("tokens", 0),
            "cost_generated": usage_map.get(kid, {}).get("cost", 0.0),
        })

    return result


class ToggleKeyBody(BaseModel):
    is_active: bool


@router.patch("/admin/keys/{key_id}")
async def toggle_key(key_id: str, body: ToggleKeyBody, _: str = Depends(_require_admin)):
    sb = get_supabase()
    sb.table("api_keys").update({"is_active": body.is_active}).eq("id", key_id).execute()
    return {"success": True}


@router.post("/admin/keys/{key_id}/rotate")
async def admin_rotate_key(key_id: str, _: str = Depends(_require_admin)):
    sb = get_supabase()

    existing = sb.table("api_keys").select("id, user_id, name, token_limit, is_active").eq("id", key_id).single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Key not found")

    key_data = existing.data
    user_id = key_data["user_id"]

    # Calculate remaining token budget
    tokens_used_result = sb.table("usage_logs").select("total_tokens").eq("api_key_id", key_id).execute()
    total_used = sum(int(u["total_tokens"]) for u in (tokens_used_result.data or []))

    old_limit = key_data.get("token_limit")
    new_limit = max(0, old_limit - total_used) if old_limit is not None else None

    # Revoke old key
    sb.table("api_keys").update({"is_active": False}).eq("id", key_id).execute()

    # Issue new key with remaining balance
    new_key = create_api_key(user_id=user_id, name=key_data["name"], token_limit=new_limit)

    return {
        "new_key": new_key["key"],
        "new_key_id": new_key["id"],
        "token_limit": new_limit,
        "tokens_carried_over": new_limit,
    }


# ── Usage ─────────────────────────────────────────────────────────────────────

@router.get("/admin/usage")
async def admin_usage(limit: int = 100, offset: int = 0, _: str = Depends(_require_admin)):
    sb = get_supabase()

    usage = (
        sb.table("usage_logs")
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    user_ids = list({u["user_id"] for u in (usage.data or [])})
    user_map: dict = {}
    if user_ids:
        users = sb.table("users").select("id, email").in_("id", user_ids).execute()
        user_map = {u["id"]: u["email"] for u in (users.data or [])}

    return [{**u, "user_email": user_map.get(u["user_id"], "Unknown")} for u in (usage.data or [])]


# ── Transactions ──────────────────────────────────────────────────────────────

@router.get("/admin/transactions")
async def admin_transactions(limit: int = 100, offset: int = 0, _: str = Depends(_require_admin)):
    sb = get_supabase()

    txns = (
        sb.table("credit_transactions")
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    user_ids = list({t["user_id"] for t in (txns.data or [])})
    user_map: dict = {}
    if user_ids:
        users = sb.table("users").select("id, email").in_("id", user_ids).execute()
        user_map = {u["id"]: u["email"] for u in (users.data or [])}

    return [{**t, "user_email": user_map.get(t["user_id"], "Unknown")} for t in (txns.data or [])]
