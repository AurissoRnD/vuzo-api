import { useEffect, useState } from 'react'
import { api } from '../lib/api'

interface ApiKey {
  id: string
  name: string
  key_prefix: string
  is_active: boolean
  rate_limit_rpm: number
  token_limit: number | null
  tokens_used: number
  created_at: string
  last_used_at: string | null
}


function TokenUsage({ used, limit }: { used: number; limit: number | null }) {
  if (limit === null) return <span className="text-zinc-500">—</span>
  const pct = Math.min((used / limit) * 100, 100)
  const isNearLimit = pct >= 80
  return (
    <div className="min-w-[120px]">
      <div className="flex justify-between text-xs mb-1">
        <span className={isNearLimit ? 'text-amber-400' : 'text-zinc-400'}>
          {used.toLocaleString()}
        </span>
        <span className="text-zinc-600">{limit.toLocaleString()}</span>
      </div>
      <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${isNearLimit ? 'bg-amber-400' : 'bg-indigo-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)

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
              <th className="text-left px-4 py-3 font-medium">Tokens Used</th>
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
                  <td className="px-4 py-3">
                    <TokenUsage used={k.tokens_used} limit={k.token_limit} />
                  </td>
                  <td className="px-4 py-3 text-zinc-400">
                    {new Date(k.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-zinc-400">
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}
                  </td>
                  <td className="px-4 py-3"></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
