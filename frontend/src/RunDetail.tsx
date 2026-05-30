import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Title,
  Text,
  Badge,
  Paper,
  Group,
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
} from './types.ts'
import { fetchRunDetail, fetchAgents } from './api.ts'
import { fetchOrEmpty } from './fetchHelpers.ts'
import { statusColor, decisionColor, formatTimestamp } from './utils.ts'
import { formatDuration } from './runDetailFormat.ts'
import PhaseMetrics from './PhaseMetrics.tsx'
import ToolCallsTable from './ToolCallsTable.tsx'
import PromptsAccordion from './PromptsAccordion.tsx'
import classes from './RunDetail.module.css'

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
      <div className={classes.researchNotes}>
        <Markdown>{research.researchNotes}</Markdown>
      </div>

      {webSources.length > 0 && (
        <>
          <Text fw={600} mb={4}>Web Sources</Text>
          <ul className={classes.sourcesList}>
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

      {decision.reasoning?.rationale && (
        <>
          <Text fw={600} mb={4}>Decision Notes</Text>
          <div className={classes.researchNotes}>
            <Markdown>{decision.reasoning.rationale}</Markdown>
          </div>
        </>
      )}

      {decision.reasoning && (
        <>
          <Paper withBorder p="sm" mb="xs">
            <Text size="sm" fw={600} mb={4}>Research Context</Text>
            <div className={classes.markdownSmall}>
              <Markdown>{decision.reasoning.researchContext}</Markdown>
            </div>
          </Paper>

          <Paper withBorder p="sm" mb="xs">
            <Text size="sm" fw={600} mb={4}>Portfolio Context</Text>
            <div className={classes.markdownSmall}>
              <Markdown>{decision.reasoning.portfolioContext}</Markdown>
            </div>
          </Paper>

          <Paper withBorder p="sm" mb="md">
            <Text size="sm" fw={600} mb={4}>Historical Context</Text>
            <div className={classes.markdownSmall}>
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
        // Cosmetic fetch (agents map for the friendly header name) must not
        // collapse the primary run detail fetch if it fails — fall back to []
        // so the header shows the "Agent #N" fallback instead of an error.
        const [runData, agentsData] = await Promise.all([
          fetchRunDetail(id!, controller.signal),
          fetchOrEmpty(fetchAgents(controller.signal)),
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
        <div className={classes.rightAlign}>
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
