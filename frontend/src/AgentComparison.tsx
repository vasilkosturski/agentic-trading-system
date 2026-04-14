import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Paper, SimpleGrid, Text, Group, Title, Badge, Popover, ActionIcon } from '@mantine/core'
import Markdown from 'react-markdown'
import { IconInfoCircle } from '@tabler/icons-react'
import type { PortfolioSnapshot, Agent } from './types.ts'
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
  id: number | null
  name: string
  totalValue: number
  cashBalance: number | null
  totalPnl: number | null
  totalReturnPercent: number | null
  style?: string
  systemPrompt?: string
}

/** Extract the latest snapshot per agent from the full snapshots array and merge with agent data. */
function latestPerAgent(snapshots: PortfolioSnapshot[], agents: Agent[]): AgentSummary[] {
  const latest = new Map<string, PortfolioSnapshot>()
  const agentMap = new Map(agents.map(a => [a.name, a]))

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

function AgentComparison({ snapshots, agents }: { snapshots: PortfolioSnapshot[], agents: Agent[] }) {
  const navigate = useNavigate()
  const agentSummaries = useMemo(() => latestPerAgent(snapshots, agents), [snapshots, agents])

  if (agentSummaries.length === 0) return null

  return (
    <Paper p="lg" shadow="xs" mb="lg">
      <Title order={3} mb="md">Agent Performance</Title>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        {agentSummaries.map((agent) => {
          const color = AGENT_COLORS[agent.name] ?? 'gray'
          return (
            <Paper
              key={agent.name}
              p="md"
              radius="md"
              withBorder
              style={{ cursor: agent.id ? 'pointer' : undefined, transition: 'box-shadow 0.15s' }}
              onMouseEnter={e => { if (agent.id) (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 12px rgba(0,0,0,0.12)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = '' }}
              onClick={() => { if (agent.id) navigate(`/agents/${agent.id}`) }}
            >
              <Text fw={700} size="lg" c={color} mb="xs">{agent.name}</Text>

              {agent.style && (
                <Group gap="xs" mb="md">
                  <Badge variant="light" size="sm">
                    {agent.style}
                  </Badge>
                  {agent.systemPrompt && (
                    <Popover width={400} position="bottom" withArrow shadow="md">
                      <Popover.Target>
                        <ActionIcon
                          variant="subtle"
                          size="sm"
                          style={{ cursor: 'pointer' }}
                          aria-label="View agent system prompt"
                        >
                          <IconInfoCircle size={16} />
                        </ActionIcon>
                      </Popover.Target>
                      <Popover.Dropdown style={{ maxHeight: '400px', overflowY: 'auto' }}>
                        <div style={{ fontSize: 'var(--mantine-font-size-sm)' }}>
                          <Markdown>{agent.systemPrompt!}</Markdown>
                        </div>
                      </Popover.Dropdown>
                    </Popover>
                  )}
                </Group>
              )}

              <Group justify="space-between" mb={4}>
                <Text size="sm" c="dimmed">Portfolio</Text>
                <Text size="sm" fw={600}>{formatCurrency(agent.totalValue)}</Text>
              </Group>

              <Group justify="space-between" mb={4}>
                <Text size="sm" c="dimmed">Cash</Text>
                <Text size="sm" fw={600}>{formatCurrency(agent.cashBalance)}</Text>
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
