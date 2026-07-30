"""Per-phase cost and concrete-model capture from gateway response headers.

Why this exists: once a phase names an *intent* (``research-tier``) instead of a
model, the local ``MODEL_PRICING`` table can no longer price it — there is no
``research-tier`` entry, and the app deliberately does not know which model the
gateway picked. The proxy already answers both questions on every response::

    x-litellm-response-cost: 0.000123
    x-litellm-model-name:    gpt-5-mini      # the deployment, not the alias

The gateway is the pricing authority here, which is the point of moving binding
out of the app: a price change, or an intent rebound to a different model, shows
up in the persisted cost with no app release.

The Agents SDK calls ``chat.completions.create()`` and returns only the parsed
body, so headers have to be intercepted a layer lower — an httpx event hook on
the gateway client. That hook fires for every request the client makes, so the
per-phase total is scoped with a ``ContextVar``: each phase opens a collector,
and the hook credits whichever collector is active on the current task. Four
agents in one ``asyncio.gather`` therefore keep separate totals, and a request
issued outside any phase is simply not counted.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_COST_HEADER = "x-litellm-response-cost"
_MODEL_HEADER = "x-litellm-model-name"


@dataclass
class GatewayUsage:
    """What the gateway reported for one phase.

    ``cost_usd`` is ``None`` when at least one call in the phase came back
    without a parseable cost: a partial sum would read as a real total, and
    aggregating that would understate spend. ``responses`` still counts the
    call, so "the gateway priced nothing" is distinguishable from "no calls".
    """

    responses: int = 0
    model_names: list[str] = field(default_factory=list)
    _cost_usd: float = 0.0
    _cost_complete: bool = True

    @property
    def cost_usd(self) -> float | None:
        return self._cost_usd if self._cost_complete else None

    @property
    def model_name(self) -> str | None:
        """The one model that served the phase, or ``None`` if more than one did.

        Naming a winner would be a lie, so the caller keeps its intent label and
        ``model_names`` carries the full list.
        """
        return self.model_names[0] if len(self.model_names) == 1 else None

    def record(self, cost: str | None, model_name: str | None) -> None:
        self.responses += 1
        if model_name and model_name not in self.model_names:
            self.model_names.append(model_name)

        parsed = _parse_cost(cost)
        if parsed is None:
            self._cost_complete = False
        else:
            self._cost_usd += parsed


def _parse_cost(raw: str | None) -> float | None:
    """LiteLLM stringifies the cost, so an unpriced call arrives as ``"None"``."""
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        logger.warning("Gateway returned an unparseable %s: %r", _COST_HEADER, raw)
        return None


_active_usage: ContextVar[GatewayUsage | None] = ContextVar("gateway_usage", default=None)


@contextmanager
def collect_gateway_usage() -> Iterator[GatewayUsage]:
    """Collect gateway-reported usage for the duration of one phase."""
    usage = GatewayUsage()
    token = _active_usage.set(usage)
    try:
        yield usage
    finally:
        _active_usage.reset(token)


async def record_gateway_response(response: httpx.Response) -> None:
    """httpx response event hook — credit this response to the active collector.

    Registered on the gateway's httpx client, so it sees every gateway call and
    nothing else. Responses without the cost header are ignored rather than
    counted as free: the same client may serve non-LLM routes.
    """
    usage = _active_usage.get()
    if usage is None:
        return
    if _COST_HEADER not in response.headers:
        return
    usage.record(response.headers.get(_COST_HEADER), response.headers.get(_MODEL_HEADER))
