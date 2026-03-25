import { useEffect, useMemo, useState } from 'react'
import { LineChart } from '@mantine/charts'
import { Paper, Title, Text, Group, Loader } from '@mantine/core'
import type { PortfolioSnapshot } from './types.ts'
import { fetchSnapshots } from './api.ts'

const AGENT_COLORS: Record<string, string> = {
  Warren: 'blue.6',
  George: 'orange.6',
  Ray: 'green.6',
  Cathie: 'violet.6',
}

interface ChartDataPoint {
  timestamp: string
  [agentName: string]: number | string
}

function toDateKey(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

function formatDateLabel(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric' })
}

/** Keep only the last snapshot per agent per day, then pivot into chart rows. */
function transformToChartData(snapshots: PortfolioSnapshot[]): ChartDataPoint[] {
  // Last snapshot per (date, agent) — snapshots are chronological so last write wins
  const daily = new Map<string, Map<string, { iso: string; value: number }>>()

  for (const s of snapshots) {
    const dk = toDateKey(s.timestamp)
    if (!daily.has(dk)) daily.set(dk, new Map())
    daily.get(dk)!.set(s.agentName, {
      iso: s.timestamp,
      value: Math.round(s.totalValue * 100) / 100,
    })
  }

  // Convert to chart rows, one per date
  return Array.from(daily.entries()).map(([, agents]) => {
    const firstIso = agents.values().next().value!.iso
    const row: ChartDataPoint = { timestamp: formatDateLabel(firstIso) }
    for (const [name, { value }] of agents) {
      row[name] = value
    }
    return row
  })
}

function PortfolioChart() {
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadSnapshots() {
      try {
        const data = await fetchSnapshots(controller.signal)
        setSnapshots(data)
      } catch (err) {
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }

    loadSnapshots()
    return () => controller.abort()
  }, [])

  const { chartData, series } = useMemo(() => {
    const data = transformToChartData(snapshots)
    const names = [...new Set(snapshots.map((s) => s.agentName))]
    const s = names.map((name) => ({
      name,
      color: AGENT_COLORS[name] ?? 'gray.6',
    }))
    return { chartData: data, series: s }
  }, [snapshots])

  if (loading) {
    return (
      <Paper p="lg" shadow="xs" mb="lg">
        <Group>
          <Loader size="sm" />
          <Text c="dimmed">Loading portfolio chart...</Text>
        </Group>
      </Paper>
    )
  }

  if (error) {
    return (
      <Paper p="lg" shadow="xs" mb="lg">
        <Text c="red">{error}</Text>
      </Paper>
    )
  }

  if (snapshots.length === 0) {
    return null
  }

  return (
    <Paper p="lg" shadow="xs" mb="lg">
      <Title order={3} mb="md">Portfolio Performance</Title>
      <LineChart
        h={400}
        data={chartData}
        dataKey="timestamp"
        series={series}
        curveType="monotone"
        strokeWidth={2}
        withDots={chartData.length <= 30}
        withLegend
        legendProps={{ verticalAlign: 'top', height: 40 }}
        withTooltip
        tooltipAnimationDuration={200}
        valueFormatter={(value: number) => `$${new Intl.NumberFormat('en-US').format(value)}`}
        yAxisProps={{ domain: ['auto', 'auto'], width: 80 }}
        xAxisProps={{ tickMargin: 10 }}
      />
    </Paper>
  )
}

export default PortfolioChart
