import { useMemo } from 'react'
import { LineChart } from '@mantine/charts'
import { Paper, Title } from '@mantine/core'
import type { PortfolioSnapshot } from './types.ts'
import { AGENT_COLORS } from './constants.ts'

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
  const { chartData, series } = useMemo(() => {
    const data = transformToChartData(snapshots)
    const names = [...new Set(snapshots.map((s) => s.agentName))]
    const s = names.map((name) => ({
      name,
      color: `${AGENT_COLORS[name] ?? 'gray'}.6`,
    }))
    return { chartData: data, series: s }
  }, [snapshots])

  if (snapshots.length === 0) return null

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
