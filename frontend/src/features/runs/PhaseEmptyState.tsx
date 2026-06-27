import { Paper, Title, Text } from '@mantine/core'

interface PhaseEmptyStateProps {
  title: string
}

function PhaseEmptyState({ title }: PhaseEmptyStateProps) {
  return (
    <Paper p="lg" shadow="xs" mb="md">
      <Title order={3} mb="sm">{title}</Title>
      <Text c="dimmed">Phase not completed</Text>
    </Paper>
  )
}

export default PhaseEmptyState
