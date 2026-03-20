import { useEffect, useState } from 'react'
import './App.css'

interface TradingRun {
  runId: number
  agentId: number
  status: string
  phase: string
  decision: string | null
  symbol: string | null
  startedAt: string
  completedAt: string | null
}

interface Agent {
  id: number
  name: string
}

function decisionClass(decision: string | null): string {
  switch (decision) {
    case 'BUY':
      return 'decision-buy'
    case 'SELL':
      return 'decision-sell'
    case 'HOLD':
      return 'decision-hold'
    default:
      return ''
  }
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return '\u2014'
  return new Date(ts).toLocaleString()
}

function App() {
  const [runs, setRuns] = useState<TradingRun[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function fetchData() {
      try {
        const [runsRes, agentsRes] = await Promise.all([
          fetch('/api/runs', { signal: controller.signal }),
          fetch('/api/agents', { signal: controller.signal }),
        ])

        if (!runsRes.ok) {
          throw new Error(`Failed to fetch runs: ${runsRes.status}`)
        }
        if (!agentsRes.ok) {
          throw new Error(`Failed to fetch agents: ${agentsRes.status}`)
        }

        const runsData = await runsRes.json()
        const agentsData = await agentsRes.json()

        setRuns(runsData.runs ?? [])
        setAgents(agentsData)
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => controller.abort()
  }, [])

  const agentMap = new Map(agents.map((a) => [a.id, a.name]))

  if (loading) {
    return (
      <div className="app">
        <h1>Trading Dashboard</h1>
        <p className="status-message">Loading runs...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="app">
        <h1>Trading Dashboard</h1>
        <p className="status-message error">{error}</p>
      </div>
    )
  }

  if (runs.length === 0) {
    return (
      <div className="app">
        <h1>Trading Dashboard</h1>
        <p className="status-message">No trading runs yet.</p>
      </div>
    )
  }

  return (
    <div className="app">
      <h1>Trading Dashboard</h1>
      <table className="runs-table">
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Agent</th>
            <th>Status</th>
            <th>Decision</th>
            <th>Symbol</th>
            <th>Started</th>
            <th>Completed</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.runId}>
              <td>{run.runId}</td>
              <td>{agentMap.get(run.agentId) ?? `Agent #${run.agentId}`}</td>
              <td>
                <span className={`status-badge status-${run.status.toLowerCase()}`}>
                  {run.status}
                </span>
              </td>
              <td>
                <span className={decisionClass(run.decision)}>
                  {run.decision ?? '\u2014'}
                </span>
              </td>
              <td>{run.symbol ?? '\u2014'}</td>
              <td>{formatTimestamp(run.startedAt)}</td>
              <td>{formatTimestamp(run.completedAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default App
