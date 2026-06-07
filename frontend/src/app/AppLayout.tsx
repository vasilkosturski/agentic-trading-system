import { Box, Container } from '@mantine/core'
import DisclaimerBanner from '@/features/disclaimer/DisclaimerBanner'
import Footer from '@/components/Footer'

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
