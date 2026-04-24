import { Box, Container } from '@mantine/core'
import DisclaimerBanner from './DisclaimerBanner'
import Footer from './Footer'

interface AppLayoutProps {
  children: React.ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <Box>
      <Container size="lg" py="md">
        <DisclaimerBanner />
      </Container>
      {children}
      <Footer />
    </Box>
  )
}
