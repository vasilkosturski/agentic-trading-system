import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Paper, SimpleGrid, Text, Group, Title, Badge, Popover, ActionIcon } from '@mantine/core'
import Markdown from 'react-markdown'
import { IconInfoCircle } from '@tabler/icons-react'
import type { PortfolioSnapshot, Agent } from './types.ts'
import { AGENT_COLORS, AGENT_ORDER } from './constants.ts'
import { formatCurrency, formatPercent, pnlColor } from './utils.ts'
import classes from './AgentComparison.module.css'

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
              className={agent.id ? classes.agentCardClickable : classes.agentCard}
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
                          className={classes.clickable}
                          aria-label="View agent system prompt"
                        >
                          <IconInfoCircle size={16} />
                        </ActionIcon>
                      </Popover.Target>
                      <Popover.Dropdown className={classes.scrollablePopover}>
                        <div className={classes.markdownSmall}>
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
