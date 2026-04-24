import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Accordion,
  Container,
  Title,
  Text,
  Paper,
  Group,
  Table,
  Anchor,
  Loader,
  Badge,
} from '@mantine/core'
import { IconClock } from '@tabler/icons-react'
import { formatDistanceToNow } from 'date-fns'
import Markdown from 'react-markdown'
import type { AgentPortfolio, Holding } from './types.ts'
import { fetchAgentPortfolio, fetchAgents } from './api.ts'
import { AGENT_COLORS } from './constants.ts'
import { formatCurrency, formatPercent, pnlColor } from './utils.ts'
import classes from './AgentDetail.module.css'

function sortByMarketValue(holdings: Holding[]): Holding[] {
  return [...holdings].sort((a, b) => (b.marketValue ?? 0) - (a.marketValue ?? 0))
}

function AgentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [portfolio, setPortfolio] = useState<AgentPortfolio | null>(null)
  const [agentName, setAgentName] = useState<string | null>(null)
  const [agentStyle, setAgentStyle] = useState<string | null>(null)
  const [systemPrompt, setSystemPrompt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function load() {
      try {
        const agentId = Number(id)
        const [portfolioData, agents] = await Promise.all([
          fetchAgentPortfolio(agentId, controller.signal),
          fetchAgents(controller.signal),
        ])
        setPortfolio(portfolioData)
        const agent = agents.find(a => a.id === agentId)
        setAgentName(agent?.name ?? portfolioData.agentName)
        setAgentStyle(agent?.style ?? null)
        setSystemPrompt(agent?.systemPrompt ?? null)
      } catch (err) {
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }

    load()
    return () => controller.abort()
  }, [id])

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

  if (error || !portfolio) {
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

  const color = AGENT_COLORS[agentName ?? ''] ?? 'gray'
  const sorted = sortByMarketValue(portfolio.holdings)
  const hasPrices = sorted.some(h => h.currentPrice != null)

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

      {/* Historical Data Disclaimer */}
      <Paper p="md" bg="yellow.1" mb="lg">
        <Text size="sm" fw={600}>Historical Data Notice</Text>
        <Text size="xs">
          Currently showing data delayed by 7 days. All information below is historical
          and for educational purposes only.
        </Text>
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

      {/* System Prompt */}
      {systemPrompt && (
        <Paper p="lg" shadow="xs" mb="lg">
          <Accordion variant="separated" defaultValue="system-prompt">
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

      {/* Positions Table */}
      <Paper p="lg" shadow="xs">
        <Title order={3} mb="md">
          Positions ({portfolio.holdingsCount})
        </Title>

        {sorted.length === 0 ? (
          <Text c="dimmed">No positions</Text>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Symbol</Table.Th>
                <Table.Th className={classes.rightAlign}>Shares</Table.Th>
                <Table.Th className={classes.rightAlign}>Avg Cost</Table.Th>
                {hasPrices && <Table.Th className={classes.rightAlign}>Price</Table.Th>}
                {hasPrices && <Table.Th className={classes.rightAlign}>Market Value</Table.Th>}
                {hasPrices && <Table.Th className={classes.rightAlign}>P&L</Table.Th>}
                {hasPrices && <Table.Th className={classes.rightAlign}>P&L %</Table.Th>}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {sorted.map(h => (
                <Table.Tr key={h.symbol}>
                  <Table.Td>
                    <Text fw={600}>{h.symbol}</Text>
                  </Table.Td>
                  <Table.Td className={classes.rightAlign}>{h.quantity}</Table.Td>
                  <Table.Td className={classes.rightAlign}>{formatCurrency(h.averagePrice)}</Table.Td>
                  {hasPrices && (
                    <Table.Td className={classes.rightAlign}>
                      {h.currentPrice != null ? formatCurrency(h.currentPrice) : <Text c="dimmed" size="sm">N/A</Text>}
                    </Table.Td>
                  )}
                  {hasPrices && (
                    <Table.Td className={classes.rightAlign}>
                      {h.marketValue != null ? <Text fw={600}>{formatCurrency(h.marketValue)}</Text> : <Text c="dimmed" size="sm">N/A</Text>}
                    </Table.Td>
                  )}
                  {hasPrices && (
                    <Table.Td className={classes.rightAlign}>
                      {h.unrealizedPnl != null ? (
                        <Text c={pnlColor(h.unrealizedPnl)} fw={600}>{formatCurrency(h.unrealizedPnl)}</Text>
                      ) : <Text c="dimmed" size="sm">N/A</Text>}
                    </Table.Td>
                  )}
                  {hasPrices && (
                    <Table.Td className={classes.rightAlign}>
                      {h.gainLossPercent != null ? (
                        <Text c={pnlColor(h.gainLossPercent)} fw={600}>{formatPercent(h.gainLossPercent)}</Text>
                      ) : <Text c="dimmed" size="sm">N/A</Text>}
                    </Table.Td>
                  )}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </Container>
  )
}

export default AgentDetail
