import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useFetchOnce } from './useFetchOnce'

describe('useFetchOnce', () => {
  it('starts in loading state with null data and null error', () => {
    const fetcher = vi.fn(() => new Promise<number>(() => {}))
    const { result } = renderHook(() => useFetchOnce(fetcher, []))
    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('resolves to data on successful fetch', async () => {
    const fetcher = vi.fn(async () => ({ value: 42 }))
    const { result } = renderHook(() => useFetchOnce(fetcher, []))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ value: 42 })
    expect(result.current.error).toBeNull()
  })

  it('captures an error message on rejection', async () => {
    const fetcher = vi.fn(async () => {
      throw new Error('boom')
    })
    const { result } = renderHook(() => useFetchOnce(fetcher, []))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('boom')
    expect(result.current.data).toBeNull()
  })

  it('passes an AbortSignal to the fetcher and aborts on unmount', async () => {
    let captured: AbortSignal | null = null
    const fetcher = vi.fn((signal: AbortSignal) => {
      captured = signal
      return new Promise<number>(() => {})
    })
    const { unmount } = renderHook(() => useFetchOnce(fetcher, []))
    expect(captured).not.toBeNull()
    expect(captured!.aborted).toBe(false)
    unmount()
    expect(captured!.aborted).toBe(true)
  })

  it('does NOT set error state when the fetcher rejects because the request was aborted', async () => {
    let rejectFn: ((err: unknown) => void) | null = null
    const fetcher = vi.fn(
      () =>
        new Promise<number>((_resolve, reject) => {
          rejectFn = reject
        }),
    )
    const { result, unmount } = renderHook(() => useFetchOnce(fetcher, []))
    unmount()
    await act(async () => {
      const err = new Error('aborted')
      err.name = 'AbortError'
      rejectFn!(err)
      await Promise.resolve()
    })
    expect(result.current.error).toBeNull()
  })

  it('re-runs when a dep changes', async () => {
    const fetcher = vi.fn(async () => 1)
    const { rerender } = renderHook(({ id }: { id: number }) => useFetchOnce(() => fetcher(), [id]), {
      initialProps: { id: 1 },
    })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
    rerender({ id: 2 })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  })
})
