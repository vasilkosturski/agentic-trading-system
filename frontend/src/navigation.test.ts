import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { NavigateFunction } from 'react-router-dom'
import { navigate, setNavigator, resetNavigator } from './navigation'

describe('navigation - module-level navigator bridge', () => {
  const originalLocation = window.location

  beforeEach(() => {
    resetNavigator()
    delete (window as Partial<Window>).location
    window.location = {
      ...originalLocation,
      href: 'http://localhost:3000/',
      pathname: '/',
      search: '',
    } as Location
  })

  afterEach(() => {
    resetNavigator()
    window.location = originalLocation
  })

  it('delegates to the registered navigator function when one is set', () => {
    const navSpy = vi.fn() as unknown as NavigateFunction
    setNavigator(navSpy)

    navigate('/login?returnUrl=%2F', { replace: true })

    expect(navSpy).toHaveBeenCalledWith('/login?returnUrl=%2F', { replace: true })
  })

  it('falls back to window.location.href when no navigator is registered', () => {
    navigate('/login?returnUrl=%2F', { replace: true })

    expect(window.location.href).toBe('/login?returnUrl=%2F')
  })

  it('passes options through to the registered navigator', () => {
    const navSpy = vi.fn() as unknown as NavigateFunction
    setNavigator(navSpy)

    navigate('/somewhere')

    expect(navSpy).toHaveBeenCalledWith('/somewhere', undefined)
  })
})
