import { describe, it, expect, vi, beforeEach } from 'vitest'

// Unmock the api module so we test the real implementation
vi.unmock('../lib/api')

import { api } from '../lib/api'
import { supabase } from '../lib/supabase'

const BASE = '/v1'

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: () => Promise.resolve(body),
    statusText: status >= 400 ? 'Error' : 'OK',
  })
}

describe('api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: { access_token: 'test-token' } as any },
      error: null,
    } as any)
  })

  describe('get', () => {
    it('calls the correct URL with GET', async () => {
      global.fetch = mockFetch(200, { ok: true })
      await api.get('/models')
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/models'),
        expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer test-token' }) })
      )
    })

    it('returns parsed JSON on success', async () => {
      global.fetch = mockFetch(200, { id: '1', name: 'test' })
      const result = await api.get('/test')
      expect(result).toEqual({ id: '1', name: 'test' })
    })

    it('throws on non-OK response', async () => {
      global.fetch = mockFetch(404, { detail: 'Not found' })
      await expect(api.get('/missing')).rejects.toThrow('Not found')
    })

    it('includes Authorization header when session exists', async () => {
      global.fetch = mockFetch(200, {})
      await api.get('/test')
      const [, opts] = vi.mocked(global.fetch).mock.calls[0] as [string, RequestInit]
      expect((opts.headers as Record<string, string>)['Authorization']).toBe('Bearer test-token')
    })

    it('omits Authorization header when no session', async () => {
      vi.mocked(supabase.auth.getSession).mockResolvedValueOnce({
        data: { session: null },
        error: null,
      } as any)
      global.fetch = mockFetch(200, {})
      await api.get('/public')
      const [, opts] = vi.mocked(global.fetch).mock.calls[0] as [string, RequestInit]
      expect((opts.headers as Record<string, string>)['Authorization']).toBeUndefined()
    })
  })

  describe('post', () => {
    it('sends POST with JSON body', async () => {
      global.fetch = mockFetch(200, { created: true })
      await api.post('/api-keys', { name: 'My Key' })

      const [, opts] = vi.mocked(global.fetch).mock.calls[0] as [string, RequestInit]
      expect(opts.method).toBe('POST')
      expect(opts.body).toBe(JSON.stringify({ name: 'My Key' }))
    })

    it('sends POST without body when none given', async () => {
      global.fetch = mockFetch(200, {})
      await api.post('/trigger')
      const [, opts] = vi.mocked(global.fetch).mock.calls[0] as [string, RequestInit]
      expect(opts.body).toBeUndefined()
    })

    it('throws on error response', async () => {
      global.fetch = mockFetch(400, { detail: 'Bad request' })
      await expect(api.post('/bad')).rejects.toThrow('Bad request')
    })
  })

  describe('del', () => {
    it('sends DELETE request', async () => {
      global.fetch = mockFetch(200, { deleted: true })
      await api.del('/api-keys/key-1')

      const [url, opts] = vi.mocked(global.fetch).mock.calls[0] as [string, RequestInit]
      expect(url).toContain('/api-keys/key-1')
      expect(opts.method).toBe('DELETE')
    })

    it('throws on error response', async () => {
      global.fetch = mockFetch(404, { detail: 'Key not found' })
      await expect(api.del('/api-keys/missing')).rejects.toThrow('Key not found')
    })
  })
})
