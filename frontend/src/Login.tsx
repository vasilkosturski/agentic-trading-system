import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Container, Title, TextInput, PasswordInput, Button, Paper, Alert } from '@mantine/core'
import { login } from './auth'

/**
 * Login page component.
 * Displays username/password form and handles authentication.
 * Redirects back to the original URL with query parameters after login.
 */
function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await login(username, password)
      // Redirect back to the original URL with query parameters
      const returnUrl = searchParams.get('returnUrl') || '/'
      navigate(returnUrl)
    } catch {
      setError('Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container size="xs" py="xl">
      <Title order={1} mb="lg" ta="center">
        Admin Login
      </Title>

      <Paper shadow="md" p="xl" withBorder>
        <form onSubmit={handleSubmit}>
          <TextInput
            label="Username"
            placeholder="Enter username"
            value={username}
            onChange={(e) => setUsername(e.currentTarget.value)}
            required
            mb="md"
          />

          <PasswordInput
            label="Password"
            placeholder="Enter password"
            value={password}
            onChange={(e) => setPassword(e.currentTarget.value)}
            required
            mb="md"
          />

          {error && (
            <Alert color="red" mb="md">
              {error}
            </Alert>
          )}

          <Button type="submit" fullWidth disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </Button>
        </form>
      </Paper>
    </Container>
  )
}

export default Login
