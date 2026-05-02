"""Tests for mac_mcp.analytics — mocks PostHog, no network calls."""
from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ---------------------------------------------------------------------------
# PostHogAnalytics
# ---------------------------------------------------------------------------

@pytest.fixture
def analytics():
    with patch("posthog.Posthog") as mock_posthog_cls:
        mock_client = MagicMock()
        mock_posthog_cls.return_value = mock_client

        from mac_mcp.analytics import PostHogAnalytics
        instance = PostHogAnalytics()
        instance.client = mock_client
        yield instance, mock_client


@pytest.mark.asyncio
async def test_track_tool_calls_capture(analytics):
    instance, mock_client = analytics
    await instance.track_tool("test_tool", {"duration_ms": 100, "success": True})
    mock_client.capture.assert_called_once()
    call_kwargs = mock_client.capture.call_args
    assert call_kwargs[1]["event"] == "tool_executed"
    assert call_kwargs[1]["properties"]["tool_name"] == "test_tool"


@pytest.mark.asyncio
async def test_track_error_calls_capture(analytics):
    instance, mock_client = analytics
    err = ValueError("test error")
    await instance.track_error(err, {"tool_name": "snapshot"})
    mock_client.capture.assert_called_once()
    call_kwargs = mock_client.capture.call_args
    assert call_kwargs[1]["event"] == "exception"


@pytest.mark.asyncio
async def test_track_tool_no_client(analytics):
    instance, _ = analytics
    instance.client = None
    await instance.track_tool("test_tool", {"duration_ms": 50, "success": True})


@pytest.mark.asyncio
async def test_close_shuts_down_client(analytics):
    instance, mock_client = analytics
    await instance.close()
    mock_client.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_close_no_client(analytics):
    instance, _ = analytics
    instance.client = None
    await instance.close()


def test_user_id_is_string(analytics):
    instance, _ = analytics
    uid = instance.user_id
    assert isinstance(uid, str)
    assert len(uid) > 0


# ---------------------------------------------------------------------------
# with_analytics decorator
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_with_analytics_success():
    with patch("posthog.Posthog") as mock_posthog_cls:
        mock_client = MagicMock()
        mock_posthog_cls.return_value = mock_client

        from mac_mcp.analytics import PostHogAnalytics, with_analytics
        a = PostHogAnalytics()
        a.client = mock_client

        @with_analytics(a, "my_tool")
        async def dummy_tool():
            return "result"

        result = await dummy_tool()
        assert result == "result"
        mock_client.capture.assert_called_once()


@pytest.mark.asyncio
async def test_with_analytics_none_instance():
    from mac_mcp.analytics import with_analytics

    @with_analytics(None, "my_tool")
    async def dummy_tool():
        return "ok"

    result = await dummy_tool()
    assert result == "ok"


@pytest.mark.asyncio
async def test_with_analytics_propagates_exception():
    from mac_mcp.analytics import with_analytics

    @with_analytics(None, "my_tool")
    async def failing_tool():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await failing_tool()
