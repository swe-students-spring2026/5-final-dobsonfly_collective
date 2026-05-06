"""
Tests for app/routers/users.py.

Covers:
- GET  /api/users/me
- PUT  /api/users/me
- POST /api/users/me/photo
- GET  /api/users/{user_id}

MongoDB and Cloudinary are fully mocked — no live connections required.
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
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

import cloudinary
import cloudinary.uploader

from app.auth import get_current_user
from app.routers import users as users_router

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

FAKE_OID = ObjectId("507f1f77bcf86cd799439011")
OTHER_OID = ObjectId("507f1f77bcf86cd799439022")
_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

FAKE_USER = {
    "_id": FAKE_OID,
    "email": "jack@example.com",
    "display_name": "Jack",
    "age": 22,
    "city": "New York",
    "bio": "hello world",
    "gender": "male",
    "gender_preference": "any",
    "age_range_preference": {"min": 18, "max": 30},
    "photo_url": "https://example.com/jack.jpg",
    "contact_info": {"phone": None, "instagram": "jackgram"},
    "spotify": {
        "access_token": None,
        "refresh_token": None,
        "top_artists": [],
        "top_genres": ["indie", "rock"],
        "audio_features": None,
        "last_synced": None,
    },
    "is_spotify_connected": False,
    "likes_sent_today": 0,
    "likes_reset_at": _NOW,
    "created_at": _NOW,
    "updated_at": _NOW,
}

OTHER_USER = {
    "_id": OTHER_OID,
    "display_name": "Sam",
    "age": 25,
    "city": "New York",
    "bio": "hey there",
    "gender": "female",
    "photo_url": "https://example.com/sam.jpg",
    "contact_info": {"phone": None, "instagram": "samgram"},
    "spotify": {
        "top_genres": ["folk"],
        "top_artists": [],
    },
}

# ---------------------------------------------------------------------------
# Test app wiring
# ---------------------------------------------------------------------------

_test_app = FastAPI()
_test_app.include_router(users_router.router)
_test_app.dependency_overrides[get_current_user] = lambda: FAKE_USER

client = TestClient(_test_app, raise_server_exceptions=False)


# ===========================================================================
# GET /api/users/me
# ===========================================================================


class TestGetMyProfile:
    def test_returns_200_with_full_user_fields(self):
        resp = client.get("/api/users/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "jack@example.com"
        assert data["display_name"] == "Jack"
        assert data["city"] == "New York"
        assert "password_hash" not in data

    def test_spotify_fields_present(self):
        resp = client.get("/api/users/me")
        data = resp.json()
        assert "top_genres" in data
        assert "is_spotify_connected" in data


# ===========================================================================
# PUT /api/users/me
# ===========================================================================


class TestUpdateProfile:
    @patch("app.routers.users.get_users_collection")
    def test_partial_update_display_name(self, mock_get_col):
        updated = {**FAKE_USER, "display_name": "Jackie"}
        mock_col = AsyncMock()
        mock_col.find_one.return_value = updated
        mock_get_col.return_value = mock_col

        resp = client.put("/api/users/me", json={"display_name": "Jackie"})

        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Jackie"
        mock_col.update_one.assert_awaited_once()

    @patch("app.routers.users.get_users_collection")
    def test_update_age_range_preference(self, mock_get_col):
        updated = {**FAKE_USER, "age_range_preference": {"min": 20, "max": 28}}
        mock_col = AsyncMock()
        mock_col.find_one.return_value = updated
        mock_get_col.return_value = mock_col

        resp = client.put(
            "/api/users/me",
            json={"age_range_preference": {"min": 20, "max": 28}},
        )

        assert resp.status_code == 200

    @patch("app.routers.users.get_users_collection")
    def test_update_contact_info(self, mock_get_col):
        updated = {**FAKE_USER, "contact_info": {"phone": "555-1234", "instagram": "new_ig"}}
        mock_col = AsyncMock()
        mock_col.find_one.return_value = updated
        mock_get_col.return_value = mock_col

        resp = client.put(
            "/api/users/me",
            json={"contact_info": {"phone": "555-1234", "instagram": "new_ig"}},
        )

        assert resp.status_code == 200

    @patch("app.routers.users.get_users_collection")
    def test_update_all_scalar_fields(self, mock_get_col):
        updated = {**FAKE_USER, "age": 25, "city": "Queens", "bio": "new bio",
                   "gender": "female", "gender_preference": "male"}
        mock_col = AsyncMock()
        mock_col.find_one.return_value = updated
        mock_get_col.return_value = mock_col

        resp = client.put("/api/users/me", json={
            "age": 25, "city": "Queens", "bio": "new bio",
            "gender": "female", "gender_preference": "male",
        })

        assert resp.status_code == 200

    @patch("app.routers.users.get_users_collection")
    def test_empty_body_succeeds(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = FAKE_USER
        mock_get_col.return_value = mock_col

        resp = client.put("/api/users/me", json={})

        assert resp.status_code == 200


# ===========================================================================
# POST /api/users/me/photo
# ===========================================================================


def _jpeg_file(size: int = 512) -> tuple:
    return ("photo.jpg", BytesIO(b"x" * size), "image/jpeg")


class TestUploadPhoto:
    def test_unsupported_format_returns_422(self):
        resp = client.post(
            "/api/users/me/photo",
            files={"file": ("photo.gif", BytesIO(b"data"), "image/gif")},
        )
        assert resp.status_code == 422

    def test_file_over_5mb_returns_422(self):
        big = b"x" * (5 * 1024 * 1024 + 1)
        resp = client.post(
            "/api/users/me/photo",
            files={"file": ("photo.jpg", BytesIO(big), "image/jpeg")},
        )
        assert resp.status_code == 422

    def test_cloudinary_not_configured_returns_503(self):
        # Default settings have empty cloudinary_cloud_name
        resp = client.post(
            "/api/users/me/photo",
            files={"file": _jpeg_file()},
        )
        assert resp.status_code == 503

    @patch("app.routers.users.get_users_collection")
    @patch("app.routers.users.get_settings")
    def test_jpeg_upload_success_returns_200_with_photo_url(
        self, mock_get_settings, mock_get_col
    ):
        mock_settings = MagicMock()
        mock_settings.cloudinary_cloud_name = "mycloud"
        mock_settings.cloudinary_api_key = "key123"
        mock_settings.cloudinary_api_secret = "secret456"
        mock_get_settings.return_value = mock_settings

        photo_url = "https://res.cloudinary.com/mycloud/image/upload/photo.jpg"
        updated = {**FAKE_USER, "photo_url": photo_url}
        mock_col = AsyncMock()
        mock_col.find_one.return_value = updated
        mock_get_col.return_value = mock_col

        with patch("cloudinary.uploader.upload", return_value={"secure_url": photo_url}):
            resp = client.post(
                "/api/users/me/photo",
                files={"file": _jpeg_file()},
            )

        assert resp.status_code == 200
        assert resp.json()["photo_url"] == photo_url

    @patch("app.routers.users.get_users_collection")
    @patch("app.routers.users.get_settings")
    def test_webp_format_accepted(self, mock_get_settings, mock_get_col):
        mock_settings = MagicMock()
        mock_settings.cloudinary_cloud_name = "mycloud"
        mock_settings.cloudinary_api_key = "key"
        mock_settings.cloudinary_api_secret = "secret"
        mock_get_settings.return_value = mock_settings

        mock_col = AsyncMock()
        mock_col.find_one.return_value = FAKE_USER
        mock_get_col.return_value = mock_col

        with patch(
            "cloudinary.uploader.upload",
            return_value={"secure_url": "https://res.cloudinary.com/photo.webp"},
        ):
            resp = client.post(
                "/api/users/me/photo",
                files={"file": ("photo.webp", BytesIO(b"x" * 100), "image/webp")},
            )

        assert resp.status_code == 200


# ===========================================================================
# GET /api/users/{user_id}
# ===========================================================================


class TestGetUser:
    @patch("app.routers.users.get_users_collection")
    def test_own_profile_returns_200(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = FAKE_USER
        mock_get_col.return_value = mock_col

        resp = client.get(f"/api/users/{str(FAKE_OID)}")

        assert resp.status_code == 200
        assert resp.json()["user_id"] == str(FAKE_OID)

    @patch("app.routers.users.get_matches_collection")
    @patch("app.routers.users.get_users_collection")
    def test_other_user_unmatched_hides_photo_and_contact(
        self, mock_get_users, mock_get_matches
    ):
        mock_users_col = AsyncMock()
        mock_users_col.find_one.return_value = OTHER_USER
        mock_get_users.return_value = mock_users_col

        mock_matches_col = AsyncMock()
        mock_matches_col.find_one.return_value = None
        mock_get_matches.return_value = mock_matches_col

        resp = client.get(f"/api/users/{str(OTHER_OID)}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["photo_url"] is None
        assert data["contact_info"] is None

    @patch("app.routers.users.get_matches_collection")
    @patch("app.routers.users.get_users_collection")
    def test_other_user_matched_exposes_photo_and_contact(
        self, mock_get_users, mock_get_matches
    ):
        mock_users_col = AsyncMock()
        mock_users_col.find_one.return_value = OTHER_USER
        mock_get_users.return_value = mock_users_col

        mock_matches_col = AsyncMock()
        mock_matches_col.find_one.return_value = {
            "user_ids": [str(FAKE_OID), str(OTHER_OID)]
        }
        mock_get_matches.return_value = mock_matches_col

        resp = client.get(f"/api/users/{str(OTHER_OID)}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["photo_url"] == OTHER_USER["photo_url"]
        assert data["contact_info"] is not None
        assert data["contact_info"]["instagram"] == "samgram"

    def test_invalid_object_id_returns_404(self):
        resp = client.get("/api/users/not-a-valid-bson-id")
        assert resp.status_code == 404

    @patch("app.routers.users.get_users_collection")
    def test_valid_id_but_user_missing_returns_404(self, mock_get_col):
        mock_col = AsyncMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        resp = client.get(f"/api/users/{str(OTHER_OID)}")

        assert resp.status_code == 404
