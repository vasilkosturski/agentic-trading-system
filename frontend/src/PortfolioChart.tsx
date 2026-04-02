import { useMemo, useState } from 'react'
import { LineChart } from '@mantine/charts'
import { Group, Paper, SegmentedControl, Title } from '@mantine/core'
import type { PortfolioSnapshot } from './types.ts'
import { AGENT_COLORS } from './constants.ts'

type TimeRange = '1W' | '1M' | '1Y' | 'All'

const TIME_RANGE_OPTIONS: { label: string; value: TimeRange }[] = [
  { label: '1W', value: '1W' },
  { label: '1M', value: '1M' },
  { label: '1Y', value: '1Y' },
  { label: 'All', value: 'All' },
]

function getCutoffDate(range: TimeRange): Date | null {
  if (range === 'All') return null
  const now = new Date()
  switch (range) {
    case '1W':
      now.setDate(now.getDate() - 7)
      break
    case '1M':
      now.setMonth(now.getMonth() - 1)
      break
    case '1Y':
      now.setFullYear(now.getFullYear() - 1)
      break
  }
  return now
}

function filterByTimeRange(snapshots: PortfolioSnapshot[], range: TimeRange): PortfolioSnapshot[] {
  const cutoff = getCutoffDate(range)
  if (!cutoff) return snapshots
  return snapshots.filter((s) => new Date(s.timestamp) >= cutoff)
}

interface ChartDataPoint {
  timestamp: string
  [agentName: string]: number | string
}

function toDateKey(iso: string): string {
  const d = new Date(iso)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

function formatDateLabel(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric' })
}

/** Keep only the last snapshot per agent per day, then pivot into chart rows. */
function transformToChartData(snapshots: PortfolioSnapshot[]): ChartDataPoint[] {
  const daily = new Map<string, Map<string, { iso: string; value: number }>>()

  for (const s of snapshots) {
    const dk = toDateKey(s.timestamp)
    if (!daily.has(dk)) daily.set(dk, new Map())
    daily.get(dk)!.set(s.agentName, {
      iso: s.timestamp,
      value: Math.round(s.totalValue * 100) / 100,
    })
  }

  return Array.from(daily.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, agents]) => {
      const firstIso = agents.values().next().value!.iso
      const row: ChartDataPoint = { timestamp: formatDateLabel(firstIso) }
      for (const [name, { value }] of agents) {
        row[name] = value
      }
      return row
    })
}

function PortfolioChart({ snapshots }: { snapshots: PortfolioSnapshot[] }) {
  const [timeRange, setTimeRange] = useState<TimeRange>('1M')

  const filtered = useMemo(() => filterByTimeRange(snapshots, timeRange), [snapshots, timeRange])

  const { chartData, series } = useMemo(() => {
    const data = transformToChartData(filtered)
    const names = [...new Set(filtered.map((s) => s.agentName))]
    const s = names.map((name) => ({
      name,
      color: `${AGENT_COLORS[name] ?? 'gray'}.6`,
    }))
    return { chartData: data, series: s }
  }, [filtered])

  if (snapshots.length === 0) return null

  return (
    <Paper p="lg" shadow="xs" mb="lg">
      <Group justify="space-between" mb="md">
        <Title order={3}>Portfolio Performance</Title>
        <SegmentedControl
          value={timeRange}
          onChange={(val) => setTimeRange(val as TimeRange)}
          data={TIME_RANGE_OPTIONS}
          size="sm"
        />
      </Group>
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
