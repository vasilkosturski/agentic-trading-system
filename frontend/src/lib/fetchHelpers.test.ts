import { describe, it, expect } from 'vitest'
import { fetchOrEmpty } from './fetchHelpers'

describe('fetchOrEmpty', () => {
  it('returns the resolved array on success', async () => {
    const result = await fetchOrEmpty(Promise.resolve([1, 2, 3]))
    expect(result).toEqual([1, 2, 3])
  })

  it('resolves to [] when the inner promise rejects with a non-abort error', async () => {
    const result = await fetchOrEmpty(Promise.reject(new Error('500 Internal Server Error')))
    expect(result).toEqual([])
  })

  it('re-throws AbortError so the surrounding Promise.all unmount path stays clean', async () => {
    const abortErr = new Error('aborted')
    abortErr.name = 'AbortError'
    await expect(fetchOrEmpty(Promise.reject(abortErr))).rejects.toThrow('aborted')
  })

  it('re-throws DOMException-style AbortError (signal.abort() native shape)', async () => {
    // jsdom may not have DOMException with name; emulate the shape the browser produces.
    const abortErr = Object.assign(new Error('The user aborted a request.'), { name: 'AbortError' })
    await expect(fetchOrEmpty(Promise.reject(abortErr))).rejects.toMatchObject({ name: 'AbortError' })
  })
})
