"""
Tests for app/auth.py and app/routers/auth.py.

Covers:
- Pure helpers: hash_password, verify_password, encode_jwt, decode_jwt
- FastAPI dependency: get_current_user
- Routes: POST /api/auth/register, POST /api/auth/login,
          POST /api/auth/logout, GET /api/auth/me

MongoDB is fully mocked via unittest.mock — no live DB required.
"""

# ---------------------------------------------------------------------------
# Env-var bootstrap — must precede any app.* import
# ---------------------------------------------------------------------------
import os

os.environ.setdefault("JWT_SECRET", "testsecret_32_bytes_minimum_key!!")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/vibe_test")
os.environ.setdefault("SPOTIFY_CLIENT_ID", "fake")
os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "fake")
os.environ.setdefault(
    "SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/spotify/callback"
)

from app.config import get_settings

get_settings.cache_clear()

# ---------------------------------------------------------------------------
# Standard imports
# ---------------------------------------------------------------------------
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.auth import (
    decode_jwt,
    encode_jwt,
    get_current_user,
    hash_password,
    verify_password,
)
from app.routers import auth as auth_router

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

FAKE_OID = ObjectId("507f1f77bcf86cd799439011")
_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

FAKE_USER = {
    "_id": FAKE_OID,
    "email": "jack@example.com",
    "password_hash": "irrelevant_for_me_endpoint",
    "display_name": "Jack",
    "age": 22,
    "city": "New York",
    "bio": None,
    "gender": None,
    "gender_preference": None,
    "age_range_preference": None,
    "photo_url": None,
    "contact_info": {"phone": None, "instagram": None},
    "spotify": {
        "access_token": None,
        "refresh_token": None,
        "top_artists": [],
        "top_genres": [],
        "audio_features": None,
        "last_synced": None,
    },
    "is_spotify_connected": False,
    "likes_sent_today": 0,
    "likes_reset_at": _NOW,
    "created_at": _NOW,
    "updated_at": _NOW,
}

# ---------------------------------------------------------------------------
# Test app wiring
# ---------------------------------------------------------------------------

_test_app = FastAPI()
_test_app.include_router(auth_router.router)
_test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

client = TestClient(_test_app, raise_server_exceptions=False)


def _unauthed_client() -> TestClient:
    app = FastAPI()
    app.include_router(auth_router.router)
    app.dependency_overrides[get_current_user] = lambda: (
        (_ for _ in ()).throw(HTTPException(status_code=401, detail="Not authenticated"))
    )
    return TestClient(app, raise_server_exceptions=False)


# ===========================================================================
# Pure helpers — hash_password / verify_password
# ===========================================================================


class TestHashVerifyPassword:
    def test_hash_returns_nonempty_string(self):
        result = hash_password("mypassword")
        assert isinstance(result, str) and len(result) > 0

    def test_verify_correct_password(self):
        h = hash_password("correctpass")
        assert verify_password("correctpass", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correctpass")
        assert verify_password("wrongpass", h) is False

    def test_hashes_differ_for_same_password(self):
        assert hash_password("same") != hash_password("same")


# ===========================================================================
# Pure helpers — encode_jwt / decode_jwt
# ===========================================================================


class TestEncodeDecodeJWT:
    def test_encode_returns_string(self):
        assert isinstance(encode_jwt({"user_id": "abc"}), str)

    def test_roundtrip_recovers_payload(self):
        token = encode_jwt({"user_id": "abc123", "role": "user"})
        result = decode_jwt(token)
        assert result["user_id"] == "abc123"
        assert result["role"] == "user"

    def test_expired_token_raises_value_error(self):
        token = encode_jwt({"user_id": "x"}, expiry_minutes=-1)
        with pytest.raises(ValueError):
            decode_jwt(token)

    def test_tampered_signature_raises_value_error(self):
        token = encode_jwt({"user_id": "x"})
        tampered = token[:-4] + "xxxx"
        with pytest.raises(ValueError):
            decode_jwt(tampered)

    def test_custom_expiry_minutes(self):
        token = encode_jwt({"user_id": "x"}, expiry_minutes=60)
        payload = decode_jwt(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        remaining = (exp - datetime.now(timezone.utc)).total_seconds()
        assert 55 * 60 < remaining < 61 * 60

    def test_default_expiry_uses_jwt_expiry_days_setting(self):
        settings = get_settings()
        token = encode_jwt({"user_id": "x"})
        payload = decode_jwt(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        remaining = (exp - datetime.now(timezone.utc)).total_seconds()
        expected_seconds = settings.jwt_expiry_days * 24 * 3600
        assert expected_seconds - 60 < remaining < expected_seconds + 60


# ===========================================================================
# FastAPI dependency — get_current_user
# ===========================================================================


class _MockRequest:
    """Minimal Starlette Request stand-in — only cookies are accessed."""

    def __init__(self, token: str | None = None):
        self.cookies: dict = {"vibe_token": token} if token else {}


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_missing_cookie_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(_MockRequest())
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_garbage_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(_MockRequest("garbage.token.value"))
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.auth.get_users_collection")
    async def test_valid_token_returns_user(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = FAKE_USER
        mock_get_col.return_value = mock_col

        token = encode_jwt({"user_id": str(FAKE_OID)})
        result = await get_current_user(_MockRequest(token))
        assert result["_id"] == FAKE_OID

    @pytest.mark.asyncio
    async def test_token_without_user_id_raises_401(self):
        token = encode_jwt({"role": "orphan"})  # valid JWT but no user_id key
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(_MockRequest(token))
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.auth.get_users_collection")
    async def test_valid_token_but_user_deleted_raises_401(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        token = encode_jwt({"user_id": str(FAKE_OID)})
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(_MockRequest(token))
        assert exc_info.value.status_code == 401


# ===========================================================================
# Router — POST /api/auth/register
# ===========================================================================

_VALID_REG = {
    "email": "newuser@example.com",
    "password": "password123",
    "display_name": "New User",
    "age": 21,
    "city": "Brooklyn",
}


class TestRegister:
    @patch("app.routers.auth.get_users_collection")
    def test_success_returns_201_with_user_id_and_cookie(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_col.insert_one.return_value = MagicMock(inserted_id=FAKE_OID)
        mock_get_col.return_value = mock_col

        resp = client.post("/api/auth/register", json=_VALID_REG)

        assert resp.status_code == 201
        assert "user_id" in resp.json()
        assert "vibe_token" in resp.cookies

    @patch("app.routers.auth.get_users_collection")
    def test_duplicate_email_returns_409(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = FAKE_USER
        mock_get_col.return_value = mock_col

        resp = client.post("/api/auth/register", json=_VALID_REG)

        assert resp.status_code == 409

    def test_password_too_short_returns_422(self):
        resp = client.post("/api/auth/register", json={**_VALID_REG, "password": "short"})
        assert resp.status_code == 422

    def test_invalid_email_returns_422(self):
        resp = client.post("/api/auth/register", json={**_VALID_REG, "email": "not-an-email"})
        assert resp.status_code == 422

    def test_age_below_minimum_returns_422(self):
        resp = client.post("/api/auth/register", json={**_VALID_REG, "age": 16})
        assert resp.status_code == 422

    def test_missing_required_field_returns_422(self):
        body = {k: v for k, v in _VALID_REG.items() if k != "city"}
        resp = client.post("/api/auth/register", json=body)
        assert resp.status_code == 422


# ===========================================================================
# Router — POST /api/auth/login
# ===========================================================================


class TestLogin:
    def _db_user(self) -> dict:
        return {**FAKE_USER, "password_hash": hash_password("correctpass")}

    @patch("app.routers.auth.get_users_collection")
    def test_success_returns_200_with_cookie(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = self._db_user()
        mock_get_col.return_value = mock_col

        resp = client.post(
            "/api/auth/login",
            json={"email": "jack@example.com", "password": "correctpass"},
        )

        assert resp.status_code == 200
        assert "vibe_token" in resp.cookies

    @patch("app.routers.auth.get_users_collection")
    def test_wrong_password_returns_401(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = self._db_user()
        mock_get_col.return_value = mock_col

        resp = client.post(
            "/api/auth/login",
            json={"email": "jack@example.com", "password": "wrongpass"},
        )

        assert resp.status_code == 401

    @patch("app.routers.auth.get_users_collection")
    def test_unknown_email_returns_401(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        resp = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "pass"},
        )

        assert resp.status_code == 401

    def test_missing_password_field_returns_422(self):
        resp = client.post("/api/auth/login", json={"email": "jack@example.com"})
        assert resp.status_code == 422


# ===========================================================================
# Router — POST /api/auth/logout
# ===========================================================================


class TestLogout:
    def test_success_returns_200(self):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200

    def test_response_clears_vibe_token_cookie(self):
        resp = client.post("/api/auth/logout")
        assert "vibe_token" in resp.headers.get("set-cookie", "")


# ===========================================================================
# Router — GET /api/auth/me
# ===========================================================================


class TestMe:
    def test_authenticated_returns_200_with_user_fields(self):
        resp = client.get("/api/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == FAKE_USER["email"]
        assert data["display_name"] == FAKE_USER["display_name"]
        assert "password_hash" not in data

    def test_unauthenticated_returns_401(self):
        resp = _unauthed_client().get("/api/auth/me")
        assert resp.status_code == 401
