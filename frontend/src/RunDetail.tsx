import { useParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Title,
  Text,
  Badge,
  Group,
  Anchor,
  Alert,
  Loader,
} from '@mantine/core'
import { IconAlertCircle } from '@tabler/icons-react'
import type { RunDetailResponse } from './types.ts'
import { fetchRunDetail, fetchAgents } from './api.ts'
import { fetchOrEmpty } from './fetchHelpers.ts'
import { useFetchOnce } from './useFetchOnce.ts'
import { statusColor, decisionColor, formatTimestamp } from './utils.ts'
import { formatDuration } from './runDetailFormat.ts'
import ResearchSection from './ResearchSection.tsx'
import DecisionSection from './DecisionSection.tsx'
import ExecutionSection from './ExecutionSection.tsx'
import classes from './RunDetail.module.css'

interface RunPayload {
  detail: RunDetailResponse
  agentName: string
}

function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data, loading, error } = useFetchOnce<RunPayload>(
    async (signal) => {
      // Cosmetic fetch (agents map for the friendly header name) must not
      // collapse the primary run detail fetch if it fails — fall back to []
      // so the header shows the "Agent #N" fallback instead of an error.
      const [runData, agentsData] = await Promise.all([
        fetchRunDetail(id!, signal),
        fetchOrEmpty(fetchAgents(signal)),
      ])
      const agent = agentsData.find((a) => a.id === runData.run.agentId)
      return {
        detail: runData,
        agentName: agent?.name ?? `Agent #${runData.run.agentId}`,
      }
    },
    [id],
  )

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

  const { run, research, decision, execution } = data.detail

  return (
    <Container size="lg" py="xl">
      <Anchor component="button" onClick={() => navigate('/')} mb="md">
        &larr; Back to runs
      </Anchor>

      {/* Header */}
      <Group justify="space-between" align="flex-start" mb="lg">
        <div>
          <Title order={1} mb="xs">
            Run #{run.runId} &mdash; {data.agentName}
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
