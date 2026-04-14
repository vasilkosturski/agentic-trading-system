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
import Markdown from 'react-markdown'
import type { AgentPortfolio, Holding } from './types.ts'
import { fetchAgentPortfolio, fetchAgents } from './api.ts'
import { AGENT_COLORS } from './constants.ts'

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

      {/* Portfolio Summary */}
      <Paper p="lg" shadow="xs" mb="lg">
        <Title order={3} mb="md">Portfolio Summary</Title>
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
          <Accordion variant="separated">
            <Accordion.Item value="system-prompt">
              <Accordion.Control>
                <Text fw={600}>System Prompt</Text>
              </Accordion.Control>
              <Accordion.Panel>
                <div style={{ maxHeight: 500, overflowY: 'auto' }}>
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
                <Table.Th style={{ textAlign: 'right' }}>Shares</Table.Th>
                <Table.Th style={{ textAlign: 'right' }}>Avg Cost</Table.Th>
                {hasPrices && <Table.Th style={{ textAlign: 'right' }}>Price</Table.Th>}
                {hasPrices && <Table.Th style={{ textAlign: 'right' }}>Market Value</Table.Th>}
                {hasPrices && <Table.Th style={{ textAlign: 'right' }}>P&L</Table.Th>}
                {hasPrices && <Table.Th style={{ textAlign: 'right' }}>P&L %</Table.Th>}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {sorted.map(h => (
                <Table.Tr key={h.symbol}>
                  <Table.Td>
                    <Text fw={600}>{h.symbol}</Text>
                  </Table.Td>
                  <Table.Td style={{ textAlign: 'right' }}>{h.quantity}</Table.Td>
                  <Table.Td style={{ textAlign: 'right' }}>{formatCurrency(h.averagePrice)}</Table.Td>
                  {hasPrices && (
                    <Table.Td style={{ textAlign: 'right' }}>
                      {h.currentPrice != null ? formatCurrency(h.currentPrice) : <Text c="dimmed" size="sm">N/A</Text>}
                    </Table.Td>
                  )}
                  {hasPrices && (
                    <Table.Td style={{ textAlign: 'right' }}>
                      {h.marketValue != null ? <Text fw={600}>{formatCurrency(h.marketValue)}</Text> : <Text c="dimmed" size="sm">N/A</Text>}
                    </Table.Td>
                  )}
                  {hasPrices && (
                    <Table.Td style={{ textAlign: 'right' }}>
                      {h.unrealizedPnl != null ? (
                        <Text c={pnlColor(h.unrealizedPnl)} fw={600}>{formatCurrency(h.unrealizedPnl)}</Text>
                      ) : <Text c="dimmed" size="sm">N/A</Text>}
                    </Table.Td>
                  )}
                  {hasPrices && (
                    <Table.Td style={{ textAlign: 'right' }}>
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
