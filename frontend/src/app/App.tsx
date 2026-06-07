import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Table, Badge, Container, Title, Text, Loader, Center } from '@mantine/core'
import { useInView } from 'react-intersection-observer'
import type { TradingRun, Agent, PortfolioSnapshot } from '@/lib/types.ts'
import { fetchRuns, fetchAgents, fetchSnapshots } from '@/lib/api.ts'
import { fetchOrEmpty } from '@/lib/fetchHelpers.ts'
import { useFetchOnce } from '@/hooks/useFetchOnce.ts'
import { statusColor, decisionColor, formatTimestamp } from '@/lib/utils.ts'
import PortfolioChart from '@/features/portfolio/PortfolioChart.tsx'
import AgentComparison from '@/features/agents/AgentComparison.tsx'
import classes from './App.module.css'

const PAGE_SIZE = 20

interface InitialPayload {
  runs: TradingRun[]
  totalRuns: number
  agents: Agent[]
  snapshots: PortfolioSnapshot[]
}

function RunsTable() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const showAll = searchParams.get('showAll') === 'true'

  // Initial load via shared hook; pagination state lives separately so the
  // load-more callback can append without re-firing the initial fetch.
  const initial = useFetchOnce<InitialPayload>(
    async (signal) => {
      // Cosmetic fetch (agents map for friendly names) must not collapse the
      // primary runs fetch if it fails — fall back to [] so the runs table
      // still renders with the "Agent #N" fallback in the agent column.
      const [runsData, agentsData, snapshotsData] = await Promise.all([
        fetchRuns(0, PAGE_SIZE, signal, showAll),
        fetchOrEmpty(fetchAgents(signal)),
        fetchSnapshots(signal),
      ])
      return {
        runs: runsData.runs ?? [],
        totalRuns: runsData.total ?? 0,
        agents: agentsData,
        snapshots: snapshotsData,
      }
    },
    [showAll],
  )

  const [extraRuns, setExtraRuns] = useState<TradingRun[]>([])
  const [paginatedTotal, setPaginatedTotal] = useState<number | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const pageRef = useRef(0)

  // Reset pagination state when the data source flips (public ↔ admin),
  // otherwise the next infinite-scroll trigger asks for `prev + 1` against
  // an unrelated dataset.
  useEffect(() => {
    pageRef.current = 0
    setExtraRuns([])
    setPaginatedTotal(null)
  }, [showAll])

  const runs = useMemo(() => [...(initial.data?.runs ?? []), ...extraRuns], [initial.data, extraRuns])
  const totalRuns = paginatedTotal ?? initial.data?.totalRuns ?? 0
  const hasMore = runs.length < totalRuns

  const { ref: loadMoreRef, inView } = useInView({ threshold: 0 })

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return
    setLoadingMore(true)
    const nextPage = pageRef.current + 1

    try {
      const data = await fetchRuns(nextPage, PAGE_SIZE, undefined, showAll)
      setExtraRuns((prev) => [...prev, ...(data.runs ?? [])])
      setPaginatedTotal(data.total ?? 0)
      pageRef.current = nextPage
    } catch {
      // Silently fail on load-more — user can scroll again
    } finally {
      setLoadingMore(false)
    }
  }, [loadingMore, hasMore, showAll])

  useEffect(() => {
    if (inView && hasMore && !loadingMore) {
      loadMore()
    }
  }, [inView, hasMore, loadingMore, loadMore])

  const agentMap = useMemo(
    () => new Map((initial.data?.agents ?? []).map((a) => [a.id, a.name])),
    [initial.data],
  )

  if (initial.loading) {
    return (
      <Container size="lg" py="xl">
        <Title order={1} mb="lg">Trading Dashboard</Title>
        <Text size="lg" c="dimmed">Loading runs...</Text>
      </Container>
    )
  }

  if (initial.error) {
    return (
      <Container size="lg" py="xl">
        <Title order={1} mb="lg">Trading Dashboard</Title>
        <Text size="lg" c="red">{initial.error}</Text>
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

  const snapshots = initial.data?.snapshots ?? []
  const agents = initial.data?.agents ?? []

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
              className={classes.clickableRow}
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
                  '—'
                )}
              </Table.Td>
              <Table.Td>{run.symbol ?? '—'}</Table.Td>
              <Table.Td>{formatTimestamp(run.startedAt)}</Table.Td>
              <Table.Td>
                {run.completedAt
                  ? formatTimestamp(run.completedAt)
                  : run.status === 'IN_PROGRESS'
                    ? `Running since ${formatTimestamp(run.startedAt)}`
                    : '—'}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {/* Infinite scroll sentinel */}
      {hasMore && (
        <Center ref={loadMoreRef} py="lg">
          {loadingMore ? (
            <Loader size="sm" />
          ) : (
            <Text size="sm" c="dimmed">Scroll for more</Text>
          )}
        </Center>
      )}

      {!hasMore && runs.length > PAGE_SIZE && (
        <Center py="lg">
          <Text size="sm" c="dimmed">All {totalRuns} runs loaded</Text>
        </Center>
      )}
    </Container>
  )
}

export default RunsTable
