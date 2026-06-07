import type { PortfolioSnapshot, Agent } from './types.ts'
import { AGENT_ORDER } from './constants.ts'

export interface AgentSummary {
  id: number | null
  name: string
  totalValue: number
  cashBalance: number | null
  totalPnl: number | null
  totalReturnPercent: number | null
  style?: string
  systemPrompt?: string
}

/**
 * For each agent that appears in `snapshots`, return the most recent snapshot
 * combined with the `Agent` metadata (id, style, system prompt). Ordering
 * follows the canonical `AGENT_ORDER` so the dashboard cards line up.
 */
export function latestPerAgent(snapshots: PortfolioSnapshot[], agents: Agent[]): AgentSummary[] {
  const latest = new Map<string, PortfolioSnapshot>()
  const agentMap = new Map(agents.map((a) => [a.name, a]))

  for (const s of snapshots) {
    const existing = latest.get(s.agentName)
    if (!existing || s.timestamp > existing.timestamp) {
      latest.set(s.agentName, s)
    }
  }

  return AGENT_ORDER
    .filter((name) => latest.has(name))
    .map((name) => {
      const s = latest.get(name)!
      const agent = agentMap.get(name)
      return {
        id: agent?.id ?? null,
        name: s.agentName,
        totalValue: s.totalValue,
        cashBalance: s.cashBalance,
        totalPnl: s.totalPnl,
        totalReturnPercent: s.totalReturnPercent,
        style: agent?.style,
        systemPrompt: agent?.systemPrompt,
      }
    })
}
