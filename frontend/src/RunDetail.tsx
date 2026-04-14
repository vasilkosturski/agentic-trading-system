import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Accordion,
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
import Markdown from 'react-markdown'
import { IconAlertCircle } from '@tabler/icons-react'
import type {
  RunDetailResponse,
  TradeDecision,
  ResearchPhase,
  DecisionPhase,
  ExecutionPhase,
  ToolCall,
} from './types.ts'
import { fetchRunDetail, fetchAgents } from './api.ts'
import { statusColor, decisionColor, formatTimestamp } from './utils.ts'

function formatDuration(startedAt: string, completedAt: string | null): string {
  if (!completedAt) return 'In progress'
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime()
  const seconds = (ms / 1000).toFixed(1)
  return `${seconds}s`
}

function formatParams(params: Record<string, unknown>): string {
  return Object.entries(params)
    .map(([key, val]) => `${key}=${typeof val === 'string' ? val : JSON.stringify(val)}`)
    .join(', ')
}

function PhaseMetrics({ phase }: { phase: ResearchPhase | DecisionPhase }) {
  const m = phase.metrics
  if (!m) return null

  const hasTokens = m.inputTokens != null || m.outputTokens != null
  if (!hasTokens && !m.modelName && !m.numTurns) return null

  return (
    <Group gap="lg" mb="sm">
      {m.modelName && <Text size="xs" c="dimmed">Model: {m.modelName}</Text>}
      {m.numTurns != null && <Text size="xs" c="dimmed">Turns: {m.numTurns}</Text>}
      {hasTokens && (
        <Text size="xs" c="dimmed">
          Tokens: {m.inputTokens?.toLocaleString() ?? '?'} in / {m.outputTokens?.toLocaleString() ?? '?'} out / {m.tokensUsed?.toLocaleString() ?? '?'} total
        </Text>
      )}
      {(m.cachedTokens ?? 0) > 0 && <Text size="xs" c="dimmed">Cached: {m.cachedTokens!.toLocaleString()}</Text>}
      {(m.reasoningTokens ?? 0) > 0 && <Text size="xs" c="dimmed">Reasoning: {m.reasoningTokens!.toLocaleString()}</Text>}
      {m.costUsd != null && <Text size="xs" c="dimmed">Cost: ${m.costUsd.toFixed(4)}</Text>}
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

function PromptsAccordion({
  label,
  systemPrompt,
  taskPrompt,
}: {
  label: string
  systemPrompt: string | null
  taskPrompt: string | null
}) {
  if (!systemPrompt && !taskPrompt) return null

  return (
    <Accordion variant="separated" mb="sm">
      <Accordion.Item value="prompts">
        <Accordion.Control>
          <Text fw={600} size="sm">{label}</Text>
        </Accordion.Control>
        <Accordion.Panel>
          {systemPrompt && (
            <>
              <Text fw={600} size="sm" mb={4}>System Prompt</Text>
              <div style={{ maxHeight: 400, overflow: 'auto', marginBottom: 12 }}>
                <Markdown>{systemPrompt}</Markdown>
              </div>
            </>
          )}
          {taskPrompt && (
            <>
              <Text fw={600} size="sm" mb={4}>Task Prompt</Text>
              <div style={{ maxHeight: 400, overflow: 'auto' }}>
                <Markdown>{taskPrompt}</Markdown>
              </div>
            </>
          )}
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
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
        {research.latencyMs != null && <Text c="dimmed" size="sm">Completed in {research.latencyMs.toLocaleString()}ms</Text>}
      </Group>

      <PhaseMetrics phase={research} />

      <PromptsAccordion
        label="Research Instructions"
        systemPrompt={research.systemPrompt}
        taskPrompt={research.taskPrompt}
      />

      <Text fw={600} mb={4}>Candidates</Text>
      <Group gap="xs" mb="md">
        {research.candidates.map((c) => (
          <Badge key={c} variant="outline">{c}</Badge>
        ))}
      </Group>

      <Text fw={600} mb={4}>Research Notes</Text>
      <div style={{ marginBottom: 'var(--mantine-spacing-md)' }}>
        <Markdown>{research.researchNotes}</Markdown>
      </div>

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
        {decision.latencyMs != null && (
          <Text c="dimmed" size="sm">Completed in {decision.latencyMs.toLocaleString()}ms</Text>
        )}
      </Group>

      <PhaseMetrics phase={decision} />

      <PromptsAccordion
        label="Decision Instructions"
        systemPrompt={decision.systemPrompt}
        taskPrompt={decision.taskPrompt}
      />

      <Group gap="sm" mb="md">
        <Badge color={decisionColor(decision.decision)} variant="light" size="lg">
          {decision.decision}
        </Badge>
        {decision.symbol && <Text fw={600}>{decision.symbol}</Text>}
        {decision.quantity != null && <Text c="dimmed">x{decision.quantity} shares</Text>}
      </Group>

      {decision.reasoning && (
        <>
          <Text fw={600} mb="xs">Reasoning</Text>

          <Paper withBorder p="sm" mb="xs">
            <Text size="sm" fw={600} mb={4}>Research Context</Text>
            <div style={{ fontSize: 'var(--mantine-font-size-sm)' }}>
              <Markdown>{decision.reasoning.researchContext}</Markdown>
            </div>
          </Paper>

          <Paper withBorder p="sm" mb="xs">
            <Text size="sm" fw={600} mb={4}>Portfolio Context</Text>
            <div style={{ fontSize: 'var(--mantine-font-size-sm)' }}>
              <Markdown>{decision.reasoning.portfolioContext}</Markdown>
            </div>
          </Paper>

          <Paper withBorder p="sm" mb="md">
            <Text size="sm" fw={600} mb={4}>Historical Context</Text>
            <div style={{ fontSize: 'var(--mantine-font-size-sm)' }}>
              <Markdown>{decision.reasoning.historicalContext}</Markdown>
            </div>
          </Paper>
        </>
      )}

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
        const [runData, agentsData] = await Promise.all([
          fetchRunDetail(id!, controller.signal),
          fetchAgents(controller.signal),
        ])

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

      {/* Error Alert for FAILED runs */}
      {run.status === 'FAILED' && run.errorMessage && (
        <Alert
          icon={<IconAlertCircle size={16} />}
          title="Run Failed"
          color="red"
          mb="lg"
        >
          {run.errorMessage}
        </Alert>
      )}

      {/* Phase Sections */}
      <ResearchSection research={research} />
      <DecisionSection decision={decision} />
      <ExecutionSection execution={execution} />
    </Container>
  )
}

export default RunDetail
