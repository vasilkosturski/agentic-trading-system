import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Title,
  Text,
  Badge,
  Paper,
  Group,
  Table,
  Anchor,
  Alert,
  Loader,
} from '@mantine/core'
import type { MantineColor } from '@mantine/core'
import type {
  RunDetailResponse,
  RunStatus,
  TradeDecision,
  Agent,
  ResearchPhase,
  DecisionPhase,
  ExecutionPhase,
  ToolCall,
} from './types.ts'

function statusColor(status: RunStatus | string): MantineColor {
  switch (status) {
    case 'COMPLETED':
      return 'green'
    case 'IN_PROGRESS':
      return 'yellow'
    case 'FAILED':
      return 'red'
    default:
      return 'gray'
  }
}

function decisionColor(decision: TradeDecision | null): MantineColor {
  switch (decision) {
    case 'BUY':
      return 'green'
    case 'SELL':
      return 'red'
    case 'HOLD':
      return 'gray'
    default:
      return 'gray'
  }
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return '\u2014'
  return new Date(ts).toLocaleString()
}

function formatDuration(startedAt: string, completedAt: string | null): string {
  if (!completedAt) return 'In progress'
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime()
  const seconds = (ms / 1000).toFixed(1)
  return `${seconds}s`
}

function renderMarkdownBold(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return part
  })
}

function formatParams(params: Record<string, unknown>): string {
  return Object.entries(params)
    .map(([key, val]) => `${key}=${typeof val === 'string' ? val : JSON.stringify(val)}`)
    .join(', ')
}

function PhaseMetrics({ phase }: { phase: ResearchPhase | DecisionPhase }) {
  const hasTokens = phase.inputTokens != null || phase.outputTokens != null
  if (!hasTokens && !phase.modelName && !phase.numTurns) return null

  return (
    <Group gap="lg" mb="sm">
      {phase.modelName && <Text size="xs" c="dimmed">Model: {phase.modelName}</Text>}
      {phase.numTurns != null && <Text size="xs" c="dimmed">Turns: {phase.numTurns}</Text>}
      {hasTokens && (
        <Text size="xs" c="dimmed">
          Tokens: {phase.inputTokens?.toLocaleString() ?? '?'} in / {phase.outputTokens?.toLocaleString() ?? '?'} out / {phase.tokensUsed?.toLocaleString() ?? '?'} total
        </Text>
      )}
      {(phase.cachedTokens ?? 0) > 0 && <Text size="xs" c="dimmed">Cached: {phase.cachedTokens!.toLocaleString()}</Text>}
      {(phase.reasoningTokens ?? 0) > 0 && <Text size="xs" c="dimmed">Reasoning: {phase.reasoningTokens!.toLocaleString()}</Text>}
      {phase.costUsd != null && <Text size="xs" c="dimmed">Cost: ${phase.costUsd.toFixed(4)}</Text>}
    </Group>
  )
}

function ToolCallsTable({ toolCalls }: { toolCalls: ToolCall[] }) {
  if (toolCalls.length === 0) return null
  return (
    <>
      <Text fw={600} mt="sm" mb={4}>Tool Calls</Text>
      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Tool</Table.Th>
            <Table.Th>Parameters</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {toolCalls.map((tc, i) => (
            <Table.Tr key={i}>
              <Table.Td><Text size="sm" ff="monospace">{tc.tool}</Text></Table.Td>
              <Table.Td><Text size="sm" ff="monospace">{formatParams(tc.params)}</Text></Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </>
  )
}

function ResearchSection({ research }: { research: ResearchPhase | null }) {
  if (!research) {
    return (
      <Paper p="lg" shadow="xs" mb="md">
        <Title order={3} mb="sm">Research Phase</Title>
        <Text c="dimmed">Phase not completed</Text>
      </Paper>
    )
  }

  const webSources = research.sources.filter((s) => s.type !== 'system_context')

  return (
    <Paper p="lg" shadow="xs" mb="md">
      <Group justify="space-between" mb="sm">
        <Title order={3}>Research Phase</Title>
        <Text c="dimmed" size="sm">Completed in {research.latencyMs.toLocaleString()}ms</Text>
      </Group>

      <PhaseMetrics phase={research} />

      <Text fw={600} mb={4}>Candidates</Text>
      <Group gap="xs" mb="md">
        {research.candidates.map((c) => (
          <Badge key={c} variant="outline">{c}</Badge>
        ))}
      </Group>

      <Text fw={600} mb={4}>Research Notes</Text>
      <Text mb="md" style={{ whiteSpace: 'pre-wrap' }}>{renderMarkdownBold(research.researchNotes)}</Text>

      {webSources.length > 0 && (
        <>
          <Text fw={600} mb={4}>Web Sources</Text>
          <ul style={{ margin: 0, paddingLeft: 20, marginBottom: 12 }}>
            {webSources.map((s, i) => (
              <li key={i}>
                {s.url ? (
                  <Anchor href={s.url} target="_blank" rel="noopener noreferrer" size="sm">
                    {s.title ?? s.url}
                  </Anchor>
                ) : (
                  <Text size="sm">{s.title ?? 'Untitled source'}</Text>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      <ToolCallsTable toolCalls={research.toolCalls} />
    </Paper>
  )
}

function DecisionSection({ decision }: { decision: DecisionPhase | null }) {
  if (!decision) {
    return (
      <Paper p="lg" shadow="xs" mb="md">
        <Title order={3} mb="sm">Decision Phase</Title>
        <Text c="dimmed">Phase not completed</Text>
      </Paper>
    )
  }

  return (
    <Paper p="lg" shadow="xs" mb="md">
      <Group justify="space-between" mb="sm">
        <Title order={3}>Decision Phase</Title>
        <Text c="dimmed" size="sm">Completed in {decision.latencyMs.toLocaleString()}ms</Text>
      </Group>

      <PhaseMetrics phase={decision} />

      <Group gap="sm" mb="md">
        <Badge color={decisionColor(decision.decision)} variant="light" size="lg">
          {decision.decision}
        </Badge>
        <Text fw={600}>{decision.symbol}</Text>
        <Text c="dimmed">x{decision.quantity} shares</Text>
      </Group>

      <Text fw={600} mb="xs">Reasoning</Text>

      <Paper withBorder p="sm" mb="xs">
        <Text size="sm" fw={600} mb={4}>Research Context</Text>
        <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
          {decision.reasoning.researchContext}
        </Text>
      </Paper>

      <Paper withBorder p="sm" mb="xs">
        <Text size="sm" fw={600} mb={4}>Portfolio Context</Text>
        <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
          {decision.reasoning.portfolioContext}
        </Text>
      </Paper>

      <Paper withBorder p="sm" mb="md">
        <Text size="sm" fw={600} mb={4}>Historical Context</Text>
        <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
          {decision.reasoning.historicalContext}
        </Text>
      </Paper>

      <ToolCallsTable toolCalls={decision.toolCalls} />
    </Paper>
  )
}

function ExecutionSection({ execution }: { execution: ExecutionPhase | null }) {
  if (!execution) {
    return (
      <Paper p="lg" shadow="xs" mb="md">
        <Title order={3} mb="sm">Execution Phase</Title>
        <Text c="dimmed">Phase not completed</Text>
      </Paper>
    )
  }

  return (
    <Paper p="lg" shadow="xs" mb="md">
      <Title order={3} mb="sm">Execution Phase</Title>

      <Group gap="sm" mb="sm">
        <Text fw={600}>Status:</Text>
        <Badge color={statusColor(execution.status)} variant="light">
          {execution.status}
        </Badge>
      </Group>

      {execution.tradeId != null && (
        <Text size="sm" mb="sm">Trade ID: {execution.tradeId}</Text>
      )}

      {execution.trade && (
        <Group gap="sm" mb="sm">
          <Badge color={decisionColor(execution.trade.transactionType as TradeDecision)} variant="light">
            {execution.trade.transactionType}
          </Badge>
          <Text fw={600}>{execution.trade.quantity} shares {execution.trade.symbol}</Text>
          <Text c="dimmed">@ ${execution.trade.price.toFixed(2)}</Text>
          <Text fw={600}>= ${execution.trade.totalAmount.toLocaleString()}</Text>
        </Group>
      )}

      {execution.errorDetails && (
        <Alert color="red" title="Execution Error" mt="sm">
          {execution.errorDetails}
        </Alert>
      )}
    </Paper>
  )
}

function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<RunDetailResponse | null>(null)
  const [agentName, setAgentName] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function fetchDetail() {
      try {
        const [runRes, agentsRes] = await Promise.all([
          fetch(`/api/runs/${id}`, { signal: controller.signal }),
          fetch('/api/agents', { signal: controller.signal }),
        ])

        if (!runRes.ok) {
          throw new Error(`Failed to fetch run: ${runRes.status}`)
        }
        if (!agentsRes.ok) {
          throw new Error(`Failed to fetch agents: ${agentsRes.status}`)
        }

        const runData: RunDetailResponse = await runRes.json()
        const agentsData: Agent[] = await agentsRes.json()

        setData(runData)
        const agent = agentsData.find((a) => a.id === runData.run.agentId)
        setAgentName(agent?.name ?? `Agent #${runData.run.agentId}`)
      } catch (err) {
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    fetchDetail()
    return () => controller.abort()
  }, [id])

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <Group>
          <Loader size="sm" />
          <Text size="lg" c="dimmed">Loading run details...</Text>
        </Group>
      </Container>
    )
  }

  if (error || !data) {
    return (
      <Container size="lg" py="xl">
        <Anchor component="button" onClick={() => navigate('/')}>
          &larr; Back to runs
        </Anchor>
        <Title order={1} mt="md" mb="lg">Run Detail</Title>
        <Text size="lg" c="red">{error ?? 'Run not found'}</Text>
      </Container>
    )
  }

  const { run, research, decision, execution } = data

  return (
    <Container size="lg" py="xl">
      <Anchor component="button" onClick={() => navigate('/')} mb="md">
        &larr; Back to runs
      </Anchor>

      {/* Header */}
      <Group justify="space-between" align="flex-start" mb="lg">
        <div>
          <Title order={1} mb="xs">
            Run #{run.runId} &mdash; {agentName}
          </Title>
          <Group gap="sm">
            <Badge color={statusColor(run.status)} variant="light" size="lg">
              {run.status}
            </Badge>
            {run.decision && (
              <Badge color={decisionColor(run.decision)} variant="light" size="lg">
                {run.decision}
              </Badge>
            )}
            {run.symbol && (
              <Badge variant="outline" size="lg">{run.symbol}</Badge>
            )}
          </Group>
        </div>
        <div style={{ textAlign: 'right' }}>
          <Text size="sm" c="dimmed">Started: {formatTimestamp(run.startedAt)}</Text>
          <Text size="sm" c="dimmed">Completed: {formatTimestamp(run.completedAt)}</Text>
          <Text size="sm" fw={600}>
            Duration: {formatDuration(run.startedAt, run.completedAt)}
          </Text>
        </div>
      </Group>

      {/* Phase Sections */}
      <ResearchSection research={research} />
      <DecisionSection decision={decision} />
      <ExecutionSection execution={execution} />
    </Container>
  )
}

export default RunDetail
