import { Container, Title, Text, List, Stack } from '@mantine/core'

export default function Disclaimer() {
  return (
    <Container size="md" py="xl">
      <Stack gap="lg">
        <Title order={1} mb="md">EDUCATIONAL DEMONSTRATION - NOT FINANCIAL ADVICE</Title>

        <Text size="md">
          This platform is an educational demonstration of autonomous AI agents and agentic systems.
          It is designed solely for educational purposes to showcase how AI agents research, reason,
          and make decisions in a financial context. All data is delayed by 7+ days to reinforce
          the educational nature of this platform.
        </Text>

        <div>
          <Title order={2} mb="sm">Important Limitations</Title>
          <List>
            <List.Item>All data delayed by 7+ days - no real-time information</List.Item>
            <List.Item>Historical and educational only - not current market conditions</List.Item>
            <List.Item>Not personalized advice - does not consider your individual circumstances</List.Item>
            <List.Item>Not recommendations to buy, sell, or hold securities</List.Item>
            <List.Item>Not managed by licensed financial advisors or investment professionals</List.Item>
            <List.Item>Past performance does not guarantee future results</List.Item>
            <List.Item>AI agents can make mistakes and lose money</List.Item>
          </List>
        </div>

        <div>
          <Title order={2} mb="sm">What This Platform Is NOT</Title>
          <List>
            <List.Item>Not a trading service or investment platform</List.Item>
            <List.Item>Not personalized financial advice tailored to your situation</List.Item>
            <List.Item>Not recommendations to buy or sell any specific securities</List.Item>
            <List.Item>Not managed by licensed financial advisors or certified professionals</List.Item>
            <List.Item>Not a substitute for consulting with a qualified financial advisor</List.Item>
          </List>
        </div>

        <div>
          <Title order={2} mb="sm">Educational Purpose</Title>
          <Text>
            This platform demonstrates how autonomous AI agents can research stocks, analyze data,
            and make trading decisions. The focus is on the process of agentic AI systems, not on
            the specific investment picks. Think of it as watching a documentary about trading from
            last week, not following a live trading room.
          </Text>
          <Text mt="sm">
            The 7-day delay ensures that all displayed information is historical and educational,
            preventing real-time replication of trades and reinforcing that this is not actionable
            investment advice.
          </Text>
        </div>

        <div>
          <Title order={2} mb="sm">Risk Warning</Title>
          <Text>
            Investing in stocks and securities carries significant risk. Past performance does not
            guarantee future results. AI agents can make mistakes, use flawed reasoning, and lose money.
            Market conditions change, and historical patterns may not repeat.
          </Text>
          <Text mt="sm" fw={600}>
            Consult a licensed financial advisor before making any investment decisions.
          </Text>
        </div>

        <div>
          <Title order={2} mb="sm">Acknowledgment</Title>
          <Text>
            By using this platform, you acknowledge that you understand this is an educational
            demonstration only, that all data is delayed by 7+ days, and that nothing on this
            platform constitutes financial advice or investment recommendations. You agree to
            consult with qualified financial professionals before making any investment decisions.
          </Text>
        </div>
      </Stack>
    </Container>
  )
}
