import { Alert, Text, Anchor } from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import { Link } from 'react-router-dom'

export default function DisclaimerBanner() {
  return (
    <Alert color="yellow" icon={<IconAlertTriangle />} variant="light" mb="md">
      <Text size="sm" fw={600}>
        Educational Demonstration Only
      </Text>
      <Text size="xs">
        All trades and decisions shown are delayed by 7+ days. This is not financial advice.
        Consult a licensed advisor before investing.{' '}
        <Anchor component={Link} to="/disclaimer" size="xs">
          Learn more
        </Anchor>
      </Text>
    </Alert>
  )
}
