/**
 * Shared constants for agent display configuration.
 * Single source of truth for agent colors and ordering across chart and comparison components.
 */

/** Agent colors using Mantine color tokens. Used by both PortfolioChart and AgentComparison. */
export const AGENT_COLORS: Record<string, string> = {
  Warren: 'indigo',
  Ray: 'cyan',
  George: 'orange',
  Cathie: 'grape',
}

/** Fixed display order for agents — matches chart legend and comparison cards. */
export const AGENT_ORDER = ['Warren', 'Ray', 'George', 'Cathie'] as const
