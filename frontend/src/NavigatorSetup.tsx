import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { setNavigator } from './navigation'

/**
 * Mount once under `<BrowserRouter>`. Captures the `useNavigate` function
 * and registers it on the module-level `navigation` bridge so non-component
 * code (api.ts) can trigger SPA navigation via the same router instance.
 *
 * Renders nothing.
 */
function NavigatorSetup() {
  const navigate = useNavigate()
  useEffect(() => {
    setNavigator(navigate)
  }, [navigate])
  return null
}

export default NavigatorSetup
