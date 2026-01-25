"""Agent execution orchestration - extracted from SimpleTrader.

Uses new phase-based Trading Runs API (/api/runs) for tracking:
- create_run() → POST /api/runs
- update_phase() → PATCH /api/runs/{id}/phase
- complete_run() → PUT /api/runs/{id}/complete

Architecture:
- RunContext dataclass passed through all phases (explicit data flow)
- No mutable instance state for per-run data
- Fail-fast error handling (no silent fallbacks)
"""

import json
import logging
from datetime import datetime
from typing import Literal, Optional

from agents import Runner

from models import TradingDecision, ResearchResponse, CycleResult
from models.orchestration import RunContext, SharedPhaseContext
from pydantic import ValidationError
from models.run_tracking import (
    CompleteRunData,
    DecisionToolCallDto,
    PhaseStatus,
    ReasoningDto,
    ResearchToolCallDto,
    SourceDto,
    TradeDecision,
)

# Import direct function tools
from trading_tools import (
    initialize_agent,
    buy_shares,
    sell_shares,
    _get_balance_raw,
    _get_holdings_raw,
)
from memory_tools import get_recent_activity

# Import new run tracking
from run_tracking import create_run, update_phase, complete_run

# Import SDK parsing utilities
from utils.sdk_parser import (
    TOOL_RESEARCHER,
    extract_tool_calls,
)

# Import status broadcasting
from status_broadcaster import (
    broadcast_status,
    PHASE_INITIALIZING,
    PHASE_RESEARCHING,
    PHASE_DECIDING,
    PHASE_TRADING,
    PHASE_COMPLETED,
    PHASE_ERROR,
)

# Import tool tracking
from tool_tracking import ToolTracker

# Import two-agent architecture
from market_analyst import create_market_analyst_agent, build_research_prompt
from decision_maker import create_decision_maker_agent, build_decision_prompt

logger = logging.getLogger(__name__)


class AgentExecutor:
    """Handles agent execution orchestration for trading cycles.

    Uses phase-based Trading Runs API for tracking:
    - INITIALIZING: Run created
    - RESEARCHING: Market research phase
    - DECIDING: Trade decision phase
    - TRADING: Trade execution (BUY/SELL only)
    - COMPLETED: Run finished successfully
    - ERROR: Run failed
    
    Data Flow:
    - RunContext created in Phase 1 with guaranteed non-None values
    - Context passed through all phases explicitly
    - No instance variables for per-run state (only agent identity)
    """

    def __init__(
        self,
        agent_id: int,
        name: str,
        agent_style: str,
        strategy: str,
        model_name: str = "gpt-4o-mini",
    ):
        """Initialize executor with agent identity.

        Args:
            agent_id: Unique agent identifier
            name: Agent name (e.g., "Warren")
            agent_style: Investment style (e.g., "Value Investor")
            strategy: Investment strategy description
            model_name: Model to use for agents (default: gpt-4o-mini)
        """
        # Agent identity (immutable for lifetime of executor)
        self.agent_id = agent_id
        self.name = name
        self.agent_style = agent_style
        self.strategy = strategy
        self.model_name = model_name
        
        # Decision storage - needed for decide_action tool callback
        # This is the only mutable state, set by Decision Maker's tool call
        self._pending_decision: Optional[TradingDecision] = None

    async def execute_cycle(
        self,
        mcp_pool,  # MCPPool
        force_trade: bool = False,
    ) -> CycleResult:
        """Execute one complete portfolio review cycle with TWO-AGENT architecture.

        Args:
            mcp_pool: MCP pool for creating agents
            force_trade: If True, agent must make BUY/SELL (no HOLD)

        Returns:
            CycleResult with decision, trade_count, and run_id

        Phases (two-agent architecture):
        1. Initialize: Create run, return RunContext
        2. Prepare context: Pre-fetch historical data, return SharedPhaseContext
        3. Run Market Analyst: Research phase (RESEARCHING)
        4. Run Decision Maker: Decision phase (DECIDING)
        5. Execute decision: Validate + execute trade (TRADING if BUY/SELL)
        6. Finalize: Complete run with all phase data
        """
        ctx: Optional[RunContext] = None

        print(
            f"🤖 {self.name} starting portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            # Phase 1: Start run tracking and setup - returns RunContext
            ctx = await self._phase1_start_run()

            # Phase 2: Prepare context (pre-fetch data) - updates ctx.shared_context
            await self._phase2_prepare_context(ctx)

            # Phase 3: Run Market Analyst (RESEARCHING phase) - updates ctx
            await self._phase3_run_market_analyst(ctx, mcp_pool)

            # Phase 4: Run Decision Maker (DECIDING phase) - updates ctx.decision
            await self._phase4_run_decision_maker(ctx, mcp_pool, force_trade)

            # Phase 5: Execute decision (includes validation)
            await self._phase5_execute_decision(ctx)

            # Phase 6: Finalize cycle
            await self._phase6_finalize(ctx)

            print(
                f"✅ {self.name} completed portfolio review at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            return CycleResult(
                decision=ctx.decision,
                trade_count=ctx.trade_count,
                run_id=ctx.run_id,
            )

        except Exception as e:
            await self._handle_cycle_error(e, ctx)
            raise

        finally:
            # Clear pending decision for next cycle
            self._pending_decision = None

    async def _phase1_start_run(self) -> RunContext:
        """Phase 1: Create run and transition to RESEARCHING.

        Returns:
            RunContext with guaranteed non-None run_id and timestamps

        Raises:
            RuntimeError: If agent_id is not set or run creation fails
        """
        # Initialize agent account (direct function call, not through agent)
        await initialize_agent(self.name)

        if self.agent_id is None:
            raise RuntimeError(
                f"Agent id not set for {self.name}. Use TradingSystem.create() to instantiate."
            )

        # Broadcast: INITIALIZING
        broadcast_status(
            self.agent_id, self.name, PHASE_INITIALIZING, "Starting trading cycle", 0
        )

        # Create run via new API (POST /api/runs)
        run_id = await create_run(self.agent_id)
        if run_id is None:
            raise RuntimeError(
                f"Failed to create run for {self.name}. Cannot proceed without runId."
            )

        # Update to RESEARCHING phase
        await update_phase(run_id, "RESEARCHING")
        research_start_time = datetime.now()

        # Broadcast: RESEARCHING
        broadcast_status(
            self.agent_id, self.name, PHASE_RESEARCHING, "Researching market", 20
        )

        # Create RunContext with all guaranteed values
        ctx = RunContext(
            run_id=run_id,
            agent_id=self.agent_id,
            agent_name=self.name,
            agent_style=self.agent_style,
            strategy=self.strategy,
            model_name=self.model_name,
            research_start_time=research_start_time,
            tracker=ToolTracker(run_id),
        )

        # Fetch balance and holdings for logging
        balance = await _get_balance_raw(self.agent_id)
        holdings = await _get_holdings_raw(self.agent_id)

        # Log initial data access for transparency
        portfolio_info = f"Balance: ${balance:.2f}"
        if holdings:
            symbols = [h.symbol for h in holdings]
            positions_str = ", ".join(symbols)
            portfolio_info += f", Holdings: {len(holdings)} position(s) ({positions_str})"
        else:
            portfolio_info += ", Holdings: None"

        ctx.tracker.log_data_access("Portfolio", portfolio_info)

        # Add system context source
        ctx.research_sources.append(
            SourceDto.system_context(f"Portfolio context: {portfolio_info}")
        )

        return ctx

    async def _phase2_prepare_context(self, ctx: RunContext) -> None:
        """Phase 2: Prepare baseline context (recent activity).

        Args:
            ctx: RunContext to update with shared_context
        """
        # Fetch recent activity (last 30 days) as baseline context
        recent_activity_json = await get_recent_activity(ctx.agent_name, days=30)

        logger.info(f"📊 Baseline context prepared: recent activity (30 days)")

        # Add system context source for recent activity
        ctx.research_sources.append(
            SourceDto.system_context("Retrieved 30-day trading activity history")
        )

        # Store in context
        ctx.shared_context = SharedPhaseContext(
            historical_context=recent_activity_json
        )

    async def _phase3_run_market_analyst(
        self, ctx: RunContext, mcp_pool
    ) -> None:
        """Phase 3: Run Market Analyst agent (RESEARCHING phase).

        Args:
            ctx: RunContext to update with research results
            mcp_pool: MCP pool for creating agent
        """
        # Get current account state for research context
        balance = await _get_balance_raw(ctx.agent_id)
        holdings = await _get_holdings_raw(ctx.agent_id)
        position_count = len(holdings)

        # Build holdings summary - show all (max 10 positions per agent)
        holdings_summary = ", ".join(h.symbol for h in holdings) if holdings else "None"

        # Create Market Analyst agent
        analyst = await create_market_analyst_agent(
            agent_name=ctx.agent_name,
            mcp_pool=mcp_pool,
            model_name=ctx.model_name,
        )

        # Build research prompt
        historical_context = ctx.shared_context.historical_context if ctx.shared_context else "{}"
        research_prompt = build_research_prompt(
            agent_name=ctx.agent_name,
            agent_style=ctx.agent_style,
            balance=balance,
            position_count=position_count,
            max_positions=10,
            holdings_summary=holdings_summary,
            historical_context=historical_context,
            force_trade=False,
        )

        logger.info(f"🔬 Running Market Analyst for {ctx.agent_name}...")

        # Run Market Analyst
        result = await Runner.run(analyst, research_prompt, max_turns=30)

        # Extract ResearchResponse - FAIL FAST if no output
        if not hasattr(result, 'output') or not result.output:
            raise RuntimeError(
                f"Market Analyst for {ctx.agent_name} failed to produce structured output. "
                f"Result type: {type(result)}, has output attr: {hasattr(result, 'output')}"
            )
        research_response = result.output

        # Update context with research results
        ctx.research_response = research_response
        ctx.research_candidates = research_response.candidates if hasattr(research_response, 'candidates') else []
        ctx.research_sources.extend([
            SourceDto.web(title=source.title, url=source.url)
            for source in research_response.sources
        ])
        ctx.research_notes = research_response.summary

        # Calculate research latency
        research_latency_ms = int(
            (datetime.now() - ctx.research_start_time).total_seconds() * 1000
        )
        logger.info(f"📊 Market Analyst completed in {research_latency_ms}ms")

        logger.info(
            f"✅ Market Analyst found {len(ctx.research_candidates)} candidates "
            f"with {len(ctx.research_sources)} sources"
        )

    async def _phase4_run_decision_maker(
        self,
        ctx: RunContext,
        mcp_pool,
        force_trade: bool,
    ) -> None:
        """Phase 4: Run Decision Maker agent (DECIDING phase).

        Args:
            ctx: RunContext to update with decision
            mcp_pool: MCP pool for creating agent
            force_trade: If True, agent must make BUY/SELL (no HOLD)
        """
        # Update to DECIDING phase
        await update_phase(ctx.run_id, "DECIDING")
        ctx.decision_start_time = datetime.now()

        # Broadcast: DECIDING
        broadcast_status(
            ctx.agent_id, ctx.agent_name, PHASE_DECIDING, "Making investment decision", 70
        )

        # Get current account state
        balance = await _get_balance_raw(ctx.agent_id)
        holdings = await _get_holdings_raw(ctx.agent_id)
        position_count = len(holdings)

        # Build holdings summary
        holdings_summary = ", ".join(h.symbol for h in holdings) if holdings else "None"

        # Create Decision Maker agent
        trader = await create_decision_maker_agent(
            agent_name=ctx.agent_name,
            executor=self,
            mcp_pool=mcp_pool,
            model_name=ctx.model_name,
        )

        # Build decision prompt
        historical_context = ctx.shared_context.historical_context if ctx.shared_context else ""
        decision_prompt = build_decision_prompt(
            agent_name=ctx.agent_name,
            agent_style=ctx.agent_style,
            research_response=ctx.research_response,
            balance=balance,
            position_count=position_count,
            max_positions=10,
            holdings_summary=holdings_summary,
            historical_context=historical_context,
            force_trade=force_trade,
        )

        logger.info(f"🧠 Running Decision Maker for {ctx.agent_name}...")

        # Run Decision Maker agent
        await Runner.run(trader, decision_prompt, max_turns=30)

        # Decision is stored by decide_action tool in self._pending_decision
        if not self._pending_decision:
            raise RuntimeError(
                f"{ctx.agent_name} completed decision phase but did not call decide_action tool"
            )

        # Transfer decision to context
        ctx.decision = self._pending_decision

        logger.info(
            f"✅ Decision Maker: {ctx.decision.action} {ctx.decision.symbol or ''}"
        )

        # Calculate decision latency
        decision_latency_ms = int(
            (datetime.now() - ctx.decision_start_time).total_seconds() * 1000
        )
        logger.info(f"📊 Decision Maker completed in {decision_latency_ms}ms")

    async def _phase5_execute_decision(self, ctx: RunContext) -> None:
        """Phase 5: Execute BUY/SELL/HOLD decision.

        Args:
            ctx: RunContext with decision to execute

        Updates ctx with execution results (trade_id, trade_count, execution_status).
        """
        # Validate we have a decision
        if not ctx.decision:
            raise RuntimeError(
                f"{ctx.agent_name} reached execution phase but no decision was recorded. "
                "Decision Maker agent should have called decide_action tool."
            )

        decision = ctx.decision
        logger.info(f"✅ Validated decision: {decision.action} {decision.symbol or ''}")
        logger.info(f"🟡 ABOUT TO EXECUTE: decision={decision}")

        if decision.action in ("BUY", "SELL"):
            action = decision.action
            symbol = decision.symbol
            quantity = decision.quantity

            logger.info(f"🟢 EXECUTING: {action} {quantity} shares of {symbol}")

            # Update to TRADING phase
            await update_phase(ctx.run_id, "TRADING")

            # Broadcast: TRADING
            broadcast_status(
                ctx.agent_id, ctx.agent_name, PHASE_TRADING, "Executing trade", 90
            )

            try:
                if action == "BUY":
                    result = await buy_shares(
                        ctx.agent_id,
                        symbol,
                        quantity,
                        runId=ctx.run_id,
                        agent_name=ctx.agent_name,
                    )
                else:
                    result = await sell_shares(
                        ctx.agent_id,
                        symbol,
                        quantity,
                        runId=ctx.run_id,
                        agent_name=ctx.agent_name,
                    )

                ctx.trade_count += 1
                ctx.execution_status = PhaseStatus.COMPLETED
                ctx.trade_id = result.tradeId

                if ctx.tracker:
                    ctx.tracker.log_reasoning(
                        "execution",
                        f"Executed {action}",
                        f"Successfully executed {action} {quantity} {symbol}",
                    )

            except Exception as trade_err:
                logger.error(f"Trade execution failed: {trade_err}")
                ctx.execution_status = PhaseStatus.FAILED
                ctx.execution_error = str(trade_err)

                if ctx.tracker:
                    ctx.tracker.log_reasoning(
                        "execution", f"Failed {action}", f"Trade failed: {str(trade_err)}"
                    )
        else:
            # HOLD decision - no trade execution
            ctx.execution_status = PhaseStatus.SKIPPED
            summary = decision.rationale if decision else "No decision"
            if ctx.tracker:
                ctx.tracker.log_reasoning(
                    "decision", "Decided: HOLD", f"No trades. {summary[:200] if summary else ''}"
                )

    async def _phase6_finalize(self, ctx: RunContext) -> None:
        """Phase 6: Complete run with all phase data.

        Args:
            ctx: RunContext with all phase data to persist
        """
        # Calculate latencies
        decision_latency_ms = None
        research_latency_ms = None
        
        if ctx.decision_start_time:
            decision_latency_ms = int(
                (datetime.now() - ctx.decision_start_time).total_seconds() * 1000
            )
        
        if ctx.research_start_time and ctx.decision_start_time:
            research_latency_ms = int(
                (ctx.decision_start_time - ctx.research_start_time).total_seconds() * 1000
            )

        # Determine trade decision
        trade_decision = TradeDecision.HOLD
        symbol = None
        quantity = None

        if ctx.decision:
            if ctx.decision.action == "BUY":
                trade_decision = TradeDecision.BUY
            elif ctx.decision.action == "SELL":
                trade_decision = TradeDecision.SELL
            symbol = ctx.decision.symbol if ctx.decision.action in ("BUY", "SELL") else None
            quantity = ctx.decision.quantity if ctx.decision.action in ("BUY", "SELL") else None

        # Build reasoning DTO from decision
        reasoning = None
        if ctx.decision and ctx.decision.fullReasoning:
            reasoning = ReasoningDto(
                portfolioContext=None,
                historicalContext=None,
                researchSummary=None,
                candidateEvaluation=None,
                finalRationale=ctx.decision.fullReasoning[:2000]
            )

        # Build CompleteRunData
        complete_data = CompleteRunData(
            # Research phase
            candidates=ctx.research_candidates,
            researchSources=ctx.research_sources,
            researchNotes=ctx.research_notes,
            researchToolCalls=ctx.research_tool_calls,
            researchLatencyMs=research_latency_ms,
            # Decision phase
            decision=trade_decision,
            symbol=symbol,
            quantity=quantity,
            reasoning=reasoning,
            decisionLatencyMs=decision_latency_ms,
            # Execution phase
            tradeId=ctx.trade_id,
            executionStatus=ctx.execution_status,
            errorDetails=ctx.execution_error,
        )

        # Complete the run via API
        await complete_run(ctx.run_id, complete_data)

        # Broadcast: COMPLETED
        outcome_message = (
            f"Completed - {ctx.trade_count} trade(s) executed"
            if ctx.trade_count > 0
            else "Completed - No trades (HOLD decision)"
        )
        broadcast_status(
            ctx.agent_id,
            ctx.agent_name,
            PHASE_COMPLETED,
            outcome_message,
            100,
            outcome=outcome_message,
        )

    async def _handle_cycle_error(self, error: Exception, ctx: Optional[RunContext]) -> None:
        """Handle cycle execution error.

        Args:
            error: Exception that occurred
            ctx: RunContext if available (may be None if Phase 1 failed)
        """
        agent_id = ctx.agent_id if ctx else self.agent_id
        agent_name = ctx.agent_name if ctx else self.name
        run_id = ctx.run_id if ctx else None

        # Broadcast: ERROR
        broadcast_status(
            agent_id,
            agent_name,
            PHASE_ERROR,
            f"Error: {str(error)}",
            0,
            outcome=f"Failed: {str(error)}",
        )

        # Update run to ERROR phase and complete with error details
        if run_id is not None:
            await update_phase(run_id, "ERROR")

            # Complete with partial data and error
            error_data = CompleteRunData(
                decision=TradeDecision.HOLD,
                executionStatus=PhaseStatus.FAILED,
                errorDetails=str(error)[:500],
            )
            await complete_run(run_id, error_data)

    def _process_researcher_output(
        self, tool_result: str, items: list, current_index: int, ctx: RunContext
    ) -> None:
        """Process Researcher tool output - extract sources and candidates.

        Args:
            tool_result: Full output from Researcher tool
            items: List of all items from agent result (for query extraction)
            current_index: Index of current item in items list
            ctx: RunContext to update with sources
        """
        sources = []
        query = "Market research"
        result_summary = "Research completed"

        # Parse typed ResearchResponse from Researcher
        try:
            research = ResearchResponse.model_validate_json(tool_result)
            result_summary = research.summary
            sources = [{"title": src.title, "url": src.url} for src in research.sources]
        except ValidationError as e:
            logger.error(f"Failed to parse ResearchResponse: {e}")
            result_summary = "Research completed (parsing failed)"
            sources = []

        # Try to find the original query
        if current_index > 0:
            for j in range(current_index - 1, max(0, current_index - 5), -1):
                prev_item = items[j]
                if hasattr(prev_item, "tool_calls") and prev_item.tool_calls:
                    for tool_call in prev_item.tool_calls:
                        if hasattr(tool_call, "name") and tool_call.name == "Researcher":
                            if hasattr(tool_call, "arguments"):
                                try:
                                    args = json.loads(tool_call.arguments) if isinstance(tool_call.arguments, str) else tool_call.arguments
                                    query = args.get("query", args.get("request", args.get("message", query)))
                                    if isinstance(query, str):
                                        query = query[:150]
                                    break
                                except (json.JSONDecodeError, TypeError):
                                    pass

        # Add web sources to context
        for source in sources:
            if isinstance(source, dict):
                url = source.get("url")
                if url:
                    ctx.research_sources.append(
                        SourceDto.web(
                            title=source.get("title", "Article"),
                            url=str(url)
                        )
                    )

        if sources:
            logger.info(f"  📎 Research: {len(sources)} sources, query: {query[:50]}...")

        if ctx.tracker:
            ctx.tracker.log_research_query(query, result_summary, sources)

    def store_decision(
        self,
        action: Literal["BUY", "SELL", "HOLD"],
        symbol: str,
        quantity: int,
        rationale: str,
        full_reasoning: str,
        research_sources: str,
        historical_context: str,
    ) -> None:
        """Store agent's decision for later execution.

        This is called by the decide_action tool during agent execution.
        Uses Pydantic for validation of LLM output.

        Args:
            action: "BUY", "SELL", or "HOLD"
            symbol: Stock symbol
            quantity: Number of shares
            rationale: Brief explanation
            full_reasoning: Complete analysis
            research_sources: JSON string with research sources
            historical_context: JSON string with historical insights

        Raises:
            ValueError: If decision is invalid or inconsistent
        """
        # Create validated decision using Pydantic model
        decision = TradingDecision(
            action=action,
            symbol=symbol,
            quantity=quantity,
            rationale=rationale,
            fullReasoning=full_reasoning,
            researchSources=research_sources or "[]",
            historicalContext=historical_context or "[]",
        )

        # Validate decision consistency
        decision.validate_consistency()

        # Store for transfer to RunContext after agent completes
        self._pending_decision = decision

        logger.info(f"🔴 DECISION STORED: action={action}, symbol={symbol}, quantity={quantity}")
