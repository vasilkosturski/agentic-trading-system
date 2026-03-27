import { useMemo } from 'react'
import { Paper, SimpleGrid, Text, Group, Title } from '@mantine/core'
import type { PortfolioSnapshot } from './types.ts'
import { AGENT_COLORS, AGENT_ORDER } from './constants.ts'

function formatCurrency(value: number | null): string {
  if (value == null) return '--'
  return `$${new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)}`
}

function formatPercent(value: number | null): string {
  if (value == null) return '--'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function pnlColor(value: number | null): string {
  if (value == null) return 'dimmed'
  return value >= 0 ? 'teal' : 'red'
}

interface AgentSummary {
  name: string
  totalValue: number
  totalPnl: number | null
  totalReturnPercent: number | null
}

/** Extract the latest snapshot per agent from the full snapshots array. */
function latestPerAgent(snapshots: PortfolioSnapshot[]): AgentSummary[] {
  const latest = new Map<string, PortfolioSnapshot>()
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
      return {
        name: s.agentName,
        totalValue: s.totalValue,
        totalPnl: s.totalPnl,
        totalReturnPercent: s.totalReturnPercent,
      }
    })
}

function AgentComparison({ snapshots }: { snapshots: PortfolioSnapshot[] }) {
  const agents = useMemo(() => latestPerAgent(snapshots), [snapshots])

  if (agents.length === 0) return null

  return (
    <Paper p="lg" shadow="xs" mb="lg">
      <Title order={3} mb="md">Agent Performance</Title>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        {agents.map((agent) => {
          const color = AGENT_COLORS[agent.name] ?? 'gray'
          return (
            <Paper key={agent.name} p="md" radius="md" withBorder>
              <Text fw={700} size="lg" c={color} mb="xs">{agent.name}</Text>

              <Group justify="space-between" mb={4}>
                <Text size="sm" c="dimmed">Portfolio</Text>
                <Text size="sm" fw={600}>{formatCurrency(agent.totalValue)}</Text>
              </Group>

              <Group justify="space-between" mb={4}>
                <Text size="sm" c="dimmed">P&L</Text>
                <Text size="sm" fw={600} c={pnlColor(agent.totalPnl)}>
                  {formatCurrency(agent.totalPnl)}
                </Text>
              </Group>

              <Group justify="space-between">
                <Text size="sm" c="dimmed">Return</Text>
                <Text size="sm" fw={600} c={pnlColor(agent.totalReturnPercent)}>
                  {formatPercent(agent.totalReturnPercent)}
                </Text>
              </Group>
            </Paper>
          )
        })}
      </SimpleGrid>
    </Paper>
  )
}

export default AgentComparison
