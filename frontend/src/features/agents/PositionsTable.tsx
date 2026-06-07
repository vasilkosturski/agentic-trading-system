import { Paper, Title, Text, Table } from '@mantine/core'
import type { Holding } from '@/lib/types.ts'
import { formatCurrency, formatPercent, pnlColor } from '@/lib/utils.ts'
import classes from './AgentDetail.module.css'

function sortByMarketValue(holdings: Holding[]): Holding[] {
  return [...holdings].sort((a, b) => (b.marketValue ?? 0) - (a.marketValue ?? 0))
}

interface PositionsTableProps {
  holdings: Holding[]
  count: number
}

function PositionsTable({ holdings, count }: PositionsTableProps) {
  const sorted = sortByMarketValue(holdings)
  const hasPrices = sorted.some((h) => h.currentPrice != null)

  return (
    <Paper p="lg" shadow="xs">
      <Title order={3} mb="md">Positions ({count})</Title>

      {sorted.length === 0 ? (
        <Text c="dimmed">No positions</Text>
      ) : (
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Symbol</Table.Th>
              <Table.Th className={classes.rightAlign}>Shares</Table.Th>
              <Table.Th className={classes.rightAlign}>Avg Cost</Table.Th>
              {hasPrices && <Table.Th className={classes.rightAlign}>Price</Table.Th>}
              {hasPrices && <Table.Th className={classes.rightAlign}>Market Value</Table.Th>}
              {hasPrices && <Table.Th className={classes.rightAlign}>P&L</Table.Th>}
              {hasPrices && <Table.Th className={classes.rightAlign}>P&L %</Table.Th>}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {sorted.map((h) => (
              <Table.Tr key={h.symbol}>
                <Table.Td>
                  <Text fw={600}>{h.symbol}</Text>
                </Table.Td>
                <Table.Td className={classes.rightAlign}>{h.quantity}</Table.Td>
                <Table.Td className={classes.rightAlign}>{formatCurrency(h.averagePrice)}</Table.Td>
                {hasPrices && (
                  <Table.Td className={classes.rightAlign}>
                    {h.currentPrice != null ? formatCurrency(h.currentPrice) : <Text c="dimmed" size="sm">N/A</Text>}
                  </Table.Td>
                )}
                {hasPrices && (
                  <Table.Td className={classes.rightAlign}>
                    {h.marketValue != null ? <Text fw={600}>{formatCurrency(h.marketValue)}</Text> : <Text c="dimmed" size="sm">N/A</Text>}
                  </Table.Td>
                )}
                {hasPrices && (
                  <Table.Td className={classes.rightAlign}>
                    {h.unrealizedPnl != null ? (
                      <Text c={pnlColor(h.unrealizedPnl)} fw={600}>{formatCurrency(h.unrealizedPnl)}</Text>
                    ) : <Text c="dimmed" size="sm">N/A</Text>}
                  </Table.Td>
                )}
                {hasPrices && (
                  <Table.Td className={classes.rightAlign}>
                    {h.gainLossPercent != null ? (
                      <Text c={pnlColor(h.gainLossPercent)} fw={600}>{formatPercent(h.gainLossPercent)}</Text>
                    ) : <Text c="dimmed" size="sm">N/A</Text>}
                  </Table.Td>
                )}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Paper>
  )
}

export default PositionsTable
