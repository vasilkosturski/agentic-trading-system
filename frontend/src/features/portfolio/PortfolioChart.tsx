import { useMemo, useState } from 'react'
import { LineChart } from '@mantine/charts'
import { Group, Paper, SegmentedControl, Title } from '@mantine/core'
import type { PortfolioSnapshot } from '@/lib/types.ts'
import { AGENT_COLORS } from '@/lib/constants.ts'
import { pivotLatestDailySnapshotsByDay } from './portfolioChart.ts'

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

function PortfolioChart({ snapshots }: { snapshots: PortfolioSnapshot[] }) {
  const [timeRange, setTimeRange] = useState<TimeRange>('1M')

  const filtered = useMemo(() => filterByTimeRange(snapshots, timeRange), [snapshots, timeRange])

  const { chartData, series } = useMemo(() => {
    const data = pivotLatestDailySnapshotsByDay(filtered)
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
