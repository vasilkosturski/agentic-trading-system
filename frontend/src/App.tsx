import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Badge, Container, Title, Text } from '@mantine/core'
import type { TradingRun, Agent, PortfolioSnapshot } from './types.ts'
import { fetchRuns, fetchAgents, fetchSnapshots } from './api.ts'
import { statusColor, decisionColor, formatTimestamp } from './utils.ts'
import PortfolioChart from './PortfolioChart.tsx'
import AgentComparison from './AgentComparison.tsx'

function RunsTable() {
  const navigate = useNavigate()
  const [runs, setRuns] = useState<TradingRun[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function fetchData() {
      try {
        const [runsData, agentsData, snapshotsData] = await Promise.all([
          fetchRuns(controller.signal),
          fetchAgents(controller.signal),
          fetchSnapshots(controller.signal),
        ])

        setRuns(runsData.runs ?? [])
        setAgents(agentsData)
        setSnapshots(snapshotsData)
      } catch (err) {
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => controller.abort()
  }, [])

  const agentMap = useMemo(() => new Map(agents.map((a) => [a.id, a.name])), [agents])

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <Title order={1} mb="lg">Trading Dashboard</Title>
        <Text size="lg" c="dimmed">Loading runs...</Text>
      </Container>
    )
  }

  if (error) {
    return (
      <Container size="lg" py="xl">
        <Title order={1} mb="lg">Trading Dashboard</Title>
        <Text size="lg" c="red">{error}</Text>
      </Container>
    )
  }

  if (runs.length === 0) {
    return (
      <Container size="lg" py="xl">
        <Title order={1} mb="lg">Trading Dashboard</Title>
        <Text size="lg" c="dimmed">No trading runs yet.</Text>
      </Container>
    )
  }

  return (
    <Container size="lg" py="xl">
      <Title order={1} mb="lg">Trading Dashboard</Title>
      <AgentComparison snapshots={snapshots} agents={agents} />
      <PortfolioChart snapshots={snapshots} />
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Run ID</Table.Th>
            <Table.Th>Agent</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Decision</Table.Th>
            <Table.Th>Symbol</Table.Th>
            <Table.Th>Started</Table.Th>
            <Table.Th>Completed</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {runs.map((run) => (
            <Table.Tr
              key={run.runId}
              style={{ cursor: 'pointer' }}
              onClick={() => navigate(`/runs/${run.runId}`)}
            >
              <Table.Td>{run.runId}</Table.Td>
              <Table.Td>{agentMap.get(run.agentId) ?? `Agent #${run.agentId}`}</Table.Td>
              <Table.Td>
                <Badge color={statusColor(run.status)} variant="light">
                  {run.status}
                </Badge>
              </Table.Td>
              <Table.Td>
                {run.decision ? (
                  <Badge color={decisionColor(run.decision)} variant="light">
                    {run.decision}
                  </Badge>
                ) : (
                  '\u2014'
                )}
              </Table.Td>
              <Table.Td>{run.symbol ?? '\u2014'}</Table.Td>
              <Table.Td>{formatTimestamp(run.startedAt)}</Table.Td>
              <Table.Td>{formatTimestamp(run.completedAt)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Container>
  )
}

export default RunsTable
