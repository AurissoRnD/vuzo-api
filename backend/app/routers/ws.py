import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.utils.crypto import get_key_prefix, hash_api_key
from app.models.database import get_supabase
from app.services.ws_manager import manager

router = APIRouter()


def _validate_key(token: str) -> str | None:
    """Validate a vz-sk_ key and return user_id, or None if invalid."""
    if not token.startswith("vz-"):
        return None

    prefix = get_key_prefix(token)
    key_hash = hash_api_key(token)

    sb = get_supabase()
    result = (
        sb.table("api_keys")
        .select("user_id, key_hash, is_active")
        .eq("key_prefix", prefix)
        .execute()
    )

    for row in (result.data or []):
        if row["key_hash"] == key_hash and row["is_active"]:
            user_result = (
                sb.table("users")
                .select("is_active")
                .eq("id", row["user_id"])
                .single()
                .execute()
            )
            if user_result.data and user_result.data["is_active"]:
                return row["user_id"]

    return None


@router.websocket("/ws/events")
async def ws_events(
    websocket: WebSocket,
    key: str = Query(..., description="vz-sk_ API key"),
):
    user_id = _validate_key(key)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or inactive API key")
        return

    await websocket.accept()
    manager.connect(user_id, websocket)

    try:
        # Send connected confirmation
        await manager.send(user_id, {
            "type": "connected",
            "message": "SimplerClaw event stream connected",
        })

        # Keep alive — ping every 30s, close if client stops responding
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_text('{"type":"ping"}')
            except Exception:
                break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id)
