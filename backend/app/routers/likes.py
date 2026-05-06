import hashlib
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.database import get_likes_collection, get_matches_collection, get_users_collection


def _auto_likes_back(from_id: str, to_id: str) -> bool:
    """60% of seed users auto-like back, deterministic per pair."""
    h = int(hashlib.md5(f"{from_id}{to_id}".encode()).hexdigest(), 16)
    return (h % 100) < 60

router = APIRouter(prefix="/api/likes", tags=["likes"])

_DAILY_LIMIT = 50


@router.post("/{user_id}", status_code=201)
async def like_user(user_id: str, current_user: dict = Depends(get_current_user)):
    from_id = str(current_user["_id"])
    if from_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot like yourself")

    users = get_users_collection()
    try:
        target = await users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    likes_sent = current_user.get("likes_sent_today", 0)
    reset_at = current_user.get("likes_reset_at")
    if reset_at and hasattr(reset_at, "date") and reset_at.date() < now.date():
        likes_sent = 0
        await users.update_one(
            {"_id": current_user["_id"]},
            {"$set": {"likes_sent_today": 0, "likes_reset_at": now}},
        )
    if likes_sent >= _DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Daily like limit reached")

    likes_col = get_likes_collection()
    if await likes_col.find_one({"from_user_id": from_id, "to_user_id": user_id}):
        return {"matched": False, "match_id": None}

    await likes_col.insert_one({"from_user_id": from_id, "to_user_id": user_id, "created_at": now})
    await users.update_one({"_id": current_user["_id"]}, {"$inc": {"likes_sent_today": 1}})

    # Seed users (admin*@nyu.edu) auto-like back 60% of the time
    target_email = target.get("email", "")
    if target_email.startswith("admin") and target_email.endswith("@nyu.edu"):
        if _auto_likes_back(from_id, user_id):
            existing_reverse = await likes_col.find_one({"from_user_id": user_id, "to_user_id": from_id})
            if not existing_reverse:
                await likes_col.insert_one({"from_user_id": user_id, "to_user_id": from_id, "created_at": now})

    reverse = await likes_col.find_one({"from_user_id": user_id, "to_user_id": from_id})
    if reverse:
        matches_col = get_matches_collection()
        existing = await matches_col.find_one({"user_ids": {"$all": [from_id, user_id]}})
        if existing:
            return {"matched": True, "match_id": str(existing["_id"])}
        result = await matches_col.insert_one({
            "user_ids": [from_id, user_id],
            "seen_by": [],
            "created_at": now,
        })
        return {"matched": True, "match_id": str(result.inserted_id)}

    return {"matched": False, "match_id": None}


@router.delete("/{user_id}")
async def unlike_user(user_id: str, current_user: dict = Depends(get_current_user)):
    from_id = str(current_user["_id"])
    await get_likes_collection().delete_one({"from_user_id": from_id, "to_user_id": user_id})
    return {"detail": "Like removed"}
