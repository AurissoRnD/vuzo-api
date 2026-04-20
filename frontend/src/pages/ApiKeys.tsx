import { useEffect, useState } from 'react'
import { api } from '../lib/api'

interface ApiKey {
  id: string
  name: string
  key_prefix: string
  is_active: boolean
  rate_limit_rpm: number
  created_at: string
  last_used_at: string | null
}

interface CreatedKey {
  id: string
  name: string
  key: string
  key_prefix: string
  created_at: string
}

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [rotating, setRotating] = useState<string | null>(null)

  const loadKeys = async () => {
    try {
      const data = await api.get<ApiKey[]>('/api-keys')
      setKeys(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadKeys() }, [])

  const handleRotate = async (key: ApiKey) => {
    if (!confirm(`Rotate "${key.name}"? Your old key will stop working immediately.`)) return
    setRotating(key.id)
    try {
      await api.del(`/api-keys/${key.id}`)
      await api.post<CreatedKey>('/api-keys', { name: key.name })
      await loadKeys()
    } catch {
      // ignore
    } finally {
      setRotating(null)
    }
  }

  if (loading) return <div className="text-zinc-400">Loading...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold">API Keys</h2>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-400">
              <th className="text-left px-4 py-3 font-medium">Name</th>
              <th className="text-left px-4 py-3 font-medium">Prefix</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
              <th className="text-left px-4 py-3 font-medium">RPM</th>
              <th className="text-left px-4 py-3 font-medium">Created</th>
              <th className="text-left px-4 py-3 font-medium">Last Used</th>
              <th className="text-right px-4 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {keys.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                  No API keys yet. Run the SimplerClaw installer to get your key.
                </td>
              </tr>
            ) : (
              keys.map((k) => (
                <tr key={k.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                  <td className="px-4 py-3 text-white">{k.name}</td>
                  <td className="px-4 py-3 font-mono text-zinc-400">{k.key_prefix}••••••••</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      k.is_active
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-red-500/10 text-red-400'
                    }`}>
                      {k.is_active ? 'Active' : 'Revoked'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-400">{k.rate_limit_rpm}</td>
                  <td className="px-4 py-3 text-zinc-400">
                    {new Date(k.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-zinc-400">
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {k.is_active && (
                      <button
                        onClick={() => handleRotate(k)}
                        disabled={rotating === k.id}
                        className="text-zinc-400 hover:text-white disabled:opacity-40 text-xs font-medium transition-colors"
                      >
                        {rotating === k.id ? 'Rotating...' : 'Rotate'}
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
