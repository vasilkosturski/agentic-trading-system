"""Tests for BackendAPIError propagation in trading_tools and market_tools.

W4 task: BackendAPIError must propagate directly (with status code intact)
out of trading tool functions instead of being wrapped as a generic Exception.

For plain async helpers (buy_shares, sell_shares, initialize_agent,
_fetch_market_data) that are called by code (not by the SDK), BackendAPIError
must surface unchanged.

For the remaining @function_tool-decorated tool (get_price_with_metadata)
the SDK's default_tool_error_function intercepts the raised exception and
turns it into a string sent to the LLM. We assert that string contains the
BackendAPIError status code, proving the underlying exception was
BackendAPIError (not a generic wrapped Exception).

W5: get_balance / get_holdings @function_tool wrappers were deleted as dead
code (never registered in any agent's tools=[...] list); their corresponding
SDK-path tests were removed alongside them.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.tool_context import ToolContext
from exceptions import BackendAPIError


# ---------------------------------------------------------------------------
# Plain async helpers — assert direct propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPlainHelpersPropagateBackendAPIError:
    """buy_shares, sell_shares, initialize_agent are not @function_tool —
    they are called by code directly, so BackendAPIError must propagate raw.
    """

    async def test_buy_shares_propagates_backend_api_error(self):
        from trading_tools import buy_shares

        mock_client = MagicMock()
        mock_client.buy_shares = AsyncMock(
            side_effect=BackendAPIError("Insufficient funds", status_code=400)
        )

        with patch("trading_tools.get_backend_client", return_value=mock_client):
            with pytest.raises(BackendAPIError) as exc_info:
                await buy_shares(agent_id=1, symbol="AAPL", quantity=10)

        assert exc_info.value.status_code == 400
        assert "Insufficient funds" in str(exc_info.value)

    async def test_sell_shares_propagates_backend_api_error(self):
        from trading_tools import sell_shares

        mock_client = MagicMock()
        mock_client.sell_shares = AsyncMock(
            side_effect=BackendAPIError("Position too small", status_code=400)
        )

        with patch("trading_tools.get_backend_client", return_value=mock_client):
            with pytest.raises(BackendAPIError) as exc_info:
                await sell_shares(agent_id=1, symbol="AAPL", quantity=10)

        assert exc_info.value.status_code == 400
        assert "Position too small" in str(exc_info.value)

    async def test_initialize_agent_propagates_backend_api_error(self):
        from trading_tools import initialize_agent

        mock_client = MagicMock()
        mock_client.initialize_agent = AsyncMock(
            side_effect=BackendAPIError("Backend unavailable", status_code=503)
        )

        with patch("trading_tools.get_backend_client", return_value=mock_client):
            with pytest.raises(BackendAPIError) as exc_info:
                await initialize_agent(name="Warren", initial_balance=100000.0)

        assert exc_info.value.status_code == 503
        assert "Backend unavailable" in str(exc_info.value)


@pytest.mark.asyncio
class TestFetchMarketDataPropagatesBackendAPIError:
    """_fetch_market_data must propagate BackendAPIError so callers
    (_lookup_share_price, get_price_with_metadata) can handle it by status
    code instead of receiving a flattened generic Exception.
    """

    async def test_fetch_market_data_propagates_backend_api_error(self):
        # Reset module cache so the test-injected mock is exercised.
        import market_tools

        market_tools._market_data_cache.clear()

        with patch("market_tools.call_backend", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = BackendAPIError(
                "Backend timeout", status_code=504
            )
            with pytest.raises(BackendAPIError) as exc_info:
                await market_tools._fetch_market_data("AAPL")

        assert exc_info.value.status_code == 504


# ---------------------------------------------------------------------------
# @function_tool-decorated tools — assert SDK error path keeps status code
# ---------------------------------------------------------------------------


def _make_tool_context(tool_name: str) -> ToolContext:
    """Minimal ToolContext for invoking a FunctionTool's on_invoke_tool."""
    return ToolContext(
        context=None,
        tool_name=tool_name,
        tool_call_id="test-call-id",
        tool_arguments="{}",
    )


@pytest.mark.asyncio
class TestFunctionToolsSurfaceBackendAPIErrorThroughSDK:
    """Confirm @function_tool wrappers raise BackendAPIError so the SDK's
    default_tool_error_function preserves the status code in its output
    string (which is what reaches the LLM).
    """

    async def test_get_price_with_metadata_surfaces_status_code(self):
        import market_tools
        from market_tools import get_price_with_metadata

        market_tools._market_data_cache.clear()

        with patch(
            "market_tools.call_backend", new_callable=AsyncMock
        ) as mock_call:
            mock_call.side_effect = BackendAPIError(
                "Rate limited", status_code=429
            )
            output = await get_price_with_metadata.on_invoke_tool(
                _make_tool_context("get_price_with_metadata"),
                json.dumps({"symbol": "AAPL"}),
            )

        assert "status=429" in output
        assert "Rate limited" in output


# ---------------------------------------------------------------------------
# sdk_parser._detect_tool_error must still flag the SDK-prefixed error
# string produced when a tool raises BackendAPIError.
# ---------------------------------------------------------------------------


class TestDetectToolErrorRecognisesBackendAPIErrorPath:
    """When @function_tool catches BackendAPIError and routes it through
    default_tool_error_function, the resulting output starts with the SDK's
    canonical prefix. _detect_tool_error must classify that as an error.
    """

    def test_detect_tool_error_flags_backend_api_error_passthrough(self):
        from agents.tool import default_tool_error_function
        from utils.sdk_parser import _detect_tool_error

        err = BackendAPIError("Account not found", status_code=404)
        sdk_output = default_tool_error_function(None, err)

        is_error, message = _detect_tool_error(sdk_output)

        assert is_error is True
        assert message is not None
        assert "status=404" in message
