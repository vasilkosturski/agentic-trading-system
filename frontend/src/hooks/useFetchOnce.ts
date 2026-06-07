import { useEffect, useState, type DependencyList } from 'react'

export interface UseFetchOnceResult<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/**
 * Single-request fetch-on-mount hook with abort-on-unmount semantics.
 *
 * Pass the AbortSignal through to whatever fetcher does network I/O so the
 * unmount path cancels in-flight requests; the hook itself ignores rejections
 * once aborted so React doesn't log "setState on unmounted component".
 */
export function useFetchOnce<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: DependencyList,
): UseFetchOnceResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)

    fetcher(controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return
        setData(result)
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        if (err && (err as { name?: string }).name === 'AbortError') return
        setError(err instanceof Error ? err.message : 'Unknown error')
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      })

    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, loading, error }
}
