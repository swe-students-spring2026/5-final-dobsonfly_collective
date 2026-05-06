"""
Tests for app/main.py — lifespan, CORS middleware, and router registration.
"""

import os

os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/vibe_test")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_EXPIRY_DAYS", "7")
os.environ.setdefault("SPOTIFY_CLIENT_ID", "fake")
os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "fake")
os.environ.setdefault("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/spotify/callback")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from app.config import get_settings
get_settings.cache_clear()

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.middleware.cors import CORSMiddleware

from app.main import app, lifespan


class TestLifespan:
    @pytest.mark.asyncio
    async def test_startup_calls_create_indexes_and_start_scheduler(self):
        with (
            patch("app.main.create_indexes", new_callable=AsyncMock) as mock_ci,
            patch("app.main.start_scheduler") as mock_ss,
            patch("app.main.stop_scheduler"),
        ):
            async with lifespan(app):
                mock_ci.assert_awaited_once()
                mock_ss.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_calls_stop_scheduler(self):
        with (
            patch("app.main.create_indexes", new_callable=AsyncMock),
            patch("app.main.start_scheduler"),
            patch("app.main.stop_scheduler") as mock_stop,
        ):
            async with lifespan(app):
                pass
        mock_stop.assert_called_once()


class TestAppConfiguration:
    def test_cors_middleware_present(self):
        assert any(m.cls is CORSMiddleware for m in app.user_middleware)

    def test_all_routers_registered(self):
        paths = {getattr(r, "path", "") for r in app.routes}
        for expected in [
            "/api/auth/login",
            "/api/auth/register",
            "/api/users/me",
            "/api/spotify/connect",
            "/api/feed",
            "/api/likes/{user_id}",
            "/api/matches",
        ]:
            assert expected in paths, f"{expected} not found in registered routes"
