import { useParams, useNavigate } from 'react-router-dom'
import {
  Accordion,
  Container,
  Title,
  Text,
  Paper,
  Group,
  Anchor,
  Loader,
  Badge,
} from '@mantine/core'
import { IconClock, IconAlertTriangle } from '@tabler/icons-react'
import { formatDistanceToNow } from 'date-fns'
import Markdown from 'react-markdown'
import type { AgentPortfolio } from '@/lib/types.ts'
import { fetchAgentPortfolio, fetchAgents } from '@/lib/api.ts'
import { fetchOrEmpty } from '@/lib/fetchHelpers.ts'
import { useFetchOnce } from '@/hooks/useFetchOnce.ts'
import { AGENT_COLORS } from '@/lib/constants.ts'
import { formatCurrency, formatPercent, pnlColor } from '@/lib/utils.ts'
import PositionsTable from './PositionsTable.tsx'
import classes from './AgentDetail.module.css'

interface AgentPayload {
  portfolio: AgentPortfolio
  agentName: string
  agentStyle: string | null
  systemPrompt: string | null
}

function AgentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data, loading, error } = useFetchOnce<AgentPayload>(
    async (signal) => {
      const agentId = Number(id)
      // Cosmetic fetch (agents map for friendly name + style + system prompt)
      // must not collapse the primary portfolio fetch if it fails — fall back
      // to [] so the page still renders with portfolio.agentName + no style.
      const [portfolioData, agents] = await Promise.all([
        fetchAgentPortfolio(agentId, signal),
        fetchOrEmpty(fetchAgents(signal)),
      ])
      const agent = agents.find((a) => a.id === agentId)
      return {
        portfolio: portfolioData,
        agentName: agent?.name ?? portfolioData.agentName,
        agentStyle: agent?.style ?? null,
        systemPrompt: agent?.systemPrompt ?? null,
      }
    },
    [id],
  )

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <Group>
          <Loader size="sm" />
          <Text size="lg" c="dimmed">Loading portfolio...</Text>
        </Group>
      </Container>
    )
  }

  if (error || !data) {
    return (
      <Container size="lg" py="xl">
        <Anchor component="button" onClick={() => navigate('/')}>
          &larr; Back to dashboard
        </Anchor>
        <Title order={1} mt="md" mb="lg">Agent Portfolio</Title>
        <Text size="lg" c="red">{error ?? 'Portfolio not found'}</Text>
      </Container>
    )
  }

  const { portfolio, agentName, agentStyle, systemPrompt } = data
  const color = AGENT_COLORS[agentName] ?? 'gray'

  return (
    <Container size="lg" py="xl">
      <Anchor component="button" onClick={() => navigate('/')} mb="md">
        &larr; Back to dashboard
      </Anchor>

      {/* Header */}
      <Group align="center" gap="sm" mb="lg">
        <Title order={1} c={color}>{agentName}</Title>
        {agentStyle && <Badge variant="light" size="lg">{agentStyle}</Badge>}
      </Group>

      {/* Historical Data Notice */}
      <Paper p="md" shadow="xs" mb="lg" bg="yellow.1" withBorder>
        <Group align="flex-start" gap="sm" wrap="nowrap">
          <IconAlertTriangle size={20} color="var(--mantine-color-yellow-8)" />
          <div>
            <Text fw={600} mb={4}>Historical Data Notice</Text>
            <Text size="sm">
              All trading data shown here is delayed by 7 days. This platform is for
              educational purposes only and does not constitute financial advice.
            </Text>
          </div>
        </Group>
      </Paper>

      {/* Portfolio Summary */}
      <Paper p="lg" shadow="xs" mb="lg">
        <Group align="center" justify="space-between" mb="md">
          <Title order={3}>Portfolio Summary</Title>
          {portfolio.lastUpdated && (
            <Badge
              color="gray"
              variant="light"
              leftSection={<IconClock size={14} />}
            >
              {formatDistanceToNow(new Date(portfolio.lastUpdated), { addSuffix: true })}
            </Badge>
          )}
        </Group>
        <Group grow>
          <div>
            <Text size="sm" c="dimmed">Total Value</Text>
            <Text size="xl" fw={700}>{formatCurrency(portfolio.totalPortfolioValue)}</Text>
          </div>
          <div>
            <Text size="sm" c="dimmed">Cash</Text>
            <Text size="xl" fw={700}>{formatCurrency(portfolio.balance)}</Text>
          </div>
          <div>
            <Text size="sm" c="dimmed">Holdings Value</Text>
            <Text size="xl" fw={700}>{formatCurrency(portfolio.holdingsValue)}</Text>
          </div>
          <div>
            <Text size="sm" c="dimmed">Total P&L</Text>
            <Text size="xl" fw={700} c={pnlColor(portfolio.totalProfitLoss)}>
              {formatCurrency(portfolio.totalProfitLoss)}
            </Text>
          </div>
          <div>
            <Text size="sm" c="dimmed">Return</Text>
            <Text size="xl" fw={700} c={pnlColor(portfolio.profitLossPercent)}>
              {formatPercent(portfolio.profitLossPercent)}
            </Text>
          </div>
        </Group>
      </Paper>

      {/* System Prompt — keyed on id so a route change to a different agent
          remounts the Accordion. Without this remount, defaultValue is bound
          on first mount only, so the panel state for the previous agent
          carries over (e.g., the "collapsed by user" choice persists into the
          next agent's view). */}
      {systemPrompt && (
        <Paper p="lg" shadow="xs" mb="lg">
          <Accordion key={id} variant="separated" defaultValue="system-prompt">
            <Accordion.Item value="system-prompt">
              <Accordion.Control>
                <Text fw={600}>Strategy</Text>
              </Accordion.Control>
              <Accordion.Panel>
                <div className={classes.scrollablePrompt}>
                  <Markdown>{systemPrompt}</Markdown>
                </div>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        </Paper>
      )}

      <PositionsTable holdings={portfolio.holdings} count={portfolio.holdingsCount} />
    </Container>
  )
}

export default AgentDetail
