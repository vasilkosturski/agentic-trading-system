import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { setNavigator } from '@/lib/navigation'

function NavigatorSetup() {
  const navigate = useNavigate()
  useEffect(() => {
    setNavigator(navigate)
  }, [navigate])
  return null
}

export default NavigatorSetup
