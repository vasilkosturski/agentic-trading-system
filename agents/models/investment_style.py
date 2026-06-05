from enum import StrEnum


class InvestmentStyle(StrEnum):
    # Values must match the DB column `agents.trading_agents.style` exactly.
    VALUE = "Value Investor"
    CONTRARIAN_MACRO = "Contrarian Macro"
    RISK_PARITY = "Risk Parity"
    GROWTH = "Growth Innovation"
