"""Investment style enum for trading agents.

StrEnum so enum values serialize as plain strings for JSON/API compatibility.
The DB stores these exact strings (e.g., "Value Investor"), and StrEnum allows
direct construction from DB values: InvestmentStyle("Value Investor").
"""

from enum import StrEnum


class InvestmentStyle(StrEnum):
    """Investment styles for the four trading agents.

    Values match the DB column `agents.trading_agents.style` exactly.
    """

    VALUE = "Value Investor"
    MOMENTUM = "Momentum Trader"
    RISK_PARITY = "Risk Parity"
    GROWTH = "Growth Innovation"
