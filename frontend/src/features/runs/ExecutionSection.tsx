import { Paper, Title, Group, Text, Badge, Alert } from '@mantine/core'
import type { ExecutionPhase } from '@/lib/types.ts'
import { statusColor, decisionColor } from '@/lib/utils.ts'
import PhaseEmptyState from './PhaseEmptyState.tsx'

function ExecutionSection({ execution }: { execution: ExecutionPhase | null }) {
  if (!execution) return <PhaseEmptyState title="Execution Phase" />

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
          <Badge color={decisionColor(execution.trade.transactionType)} variant="light">
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

export default ExecutionSection
