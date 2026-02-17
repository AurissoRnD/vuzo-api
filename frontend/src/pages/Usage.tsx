import { useEffect, useState } from 'react'
import { api } from '../lib/api'

interface UsageLog {
  id: string
  provider: string
  model: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  provider_cost: number
  vuzo_cost: number
  response_time_ms: number
  created_at: string
}

interface UsageSummary {
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_provider_cost: number
  total_vuzo_cost: number
}

export default function Usage() {
  const [logs, setLogs] = useState<UsageLog[]>([])
  const [summary, setSummary] = useState<UsageSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [filterModel, setFilterModel] = useState('')
  const [filterProvider, setFilterProvider] = useState('')

  const loadData = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filterModel) params.set('model', filterModel)
      if (filterProvider) params.set('provider', filterProvider)
      const qs = params.toString() ? `?${params}` : ''

      const [logsData, summaryData] = await Promise.all([
        api.get<UsageLog[]>(`/usage${qs}`),
        api.get<UsageSummary>('/usage/summary'),
      ])
      setLogs(logsData)
      setSummary(summaryData)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [filterModel, filterProvider])

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Usage</h2>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MiniCard label="Requests" value={summary.total_requests.toLocaleString()} />
          <MiniCard label="Input Tokens" value={summary.total_input_tokens.toLocaleString()} />
          <MiniCard label="Output Tokens" value={summary.total_output_tokens.toLocaleString()} />
          <MiniCard label="Total Cost" value={`$${summary.total_vuzo_cost.toFixed(4)}`} />
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          value={filterProvider}
          onChange={(e) => setFilterProvider(e.target.value)}
          className="px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All Providers</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="google">Google</option>
        </select>
        <input
          type="text"
          value={filterModel}
          onChange={(e) => setFilterModel(e.target.value)}
          placeholder="Filter by model..."
          className="px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Usage table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                <th className="text-left px-4 py-3 font-medium">Model</th>
                <th className="text-left px-4 py-3 font-medium">Provider</th>
                <th className="text-right px-4 py-3 font-medium">Input</th>
                <th className="text-right px-4 py-3 font-medium">Output</th>
                <th className="text-right px-4 py-3 font-medium">Cost</th>
                <th className="text-right px-4 py-3 font-medium">Latency</th>
                <th className="text-left px-4 py-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">Loading...</td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                    No usage data yet. Make some API calls to see them here.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="px-4 py-3 font-mono text-white text-xs">{log.model}</td>
                    <td className="px-4 py-3 text-zinc-400 capitalize">{log.provider}</td>
                    <td className="px-4 py-3 text-right text-zinc-300">{log.input_tokens.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-zinc-300">{log.output_tokens.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-indigo-400">${log.vuzo_cost.toFixed(6)}</td>
                    <td className="px-4 py-3 text-right text-zinc-400">{log.response_time_ms}ms</td>
                    <td className="px-4 py-3 text-zinc-500 text-xs">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function MiniCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className="text-lg font-semibold text-white">{value}</div>
    </div>
  )
}
