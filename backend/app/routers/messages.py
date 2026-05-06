from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.database import get_matches_collection, get_messages_collection

router = APIRouter(prefix="/api/matches", tags=["messages"])


class SendMessageRequest(BaseModel):
    text: str


def _verify_match_access(match: dict | None, user_id: str) -> None:
    if not match or user_id not in match["user_ids"]:
        raise HTTPException(status_code=403, detail="Not your match")


@router.get("/{match_id}/messages")
async def get_messages(match_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    try:
        match = await get_matches_collection().find_one({"_id": ObjectId(match_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Match not found")
    _verify_match_access(match, user_id)

    messages = []
    async for msg in get_messages_collection().find({"match_id": match_id}).sort("created_at", 1):
        messages.append({
            "message_id": str(msg["_id"]),
            "from_user_id": msg["from_user_id"],
            "text": msg["text"],
            "created_at": msg["created_at"].isoformat(),
            "is_mine": msg["from_user_id"] == user_id,
        })
    return {"messages": messages}


@router.post("/{match_id}/messages", status_code=201)
async def send_message(
    match_id: str,
    body: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    try:
        match = await get_matches_collection().find_one({"_id": ObjectId(match_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Match not found")
    _verify_match_access(match, user_id)

    now = datetime.now(timezone.utc)
    result = await get_messages_collection().insert_one({
        "match_id": match_id,
        "from_user_id": user_id,
        "text": text,
        "created_at": now,
    })
    return {
        "message_id": str(result.inserted_id),
        "from_user_id": user_id,
        "text": text,
        "created_at": now.isoformat(),
        "is_mine": True,
    }
