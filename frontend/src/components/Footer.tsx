import { Box, Container, Text, Anchor } from '@mantine/core'
import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <Box component="footer" py="md" style={{ borderTop: '1px solid #dee2e6' }}>
      <Container size="xl">
        <Text size="xs" c="dimmed" ta="center">
          Educational demonstration only. All data delayed 7+ days.
          {' '}
          <Anchor component={Link} to="/disclaimer" size="xs">
            View full disclaimer
          </Anchor>
        </Text>
      </Container>
    </Box>
  )
}
