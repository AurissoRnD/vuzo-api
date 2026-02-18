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

interface DailyUsage {
  date: string
  model: string
  provider: string
  total_requests: number
  input_tokens: number
  output_tokens: number
  total_cost: number
}

type DateRange = 'today' | '7d' | '30d' | 'all'
type ViewTab = 'daily' | 'requests'

function getDateBounds(range: DateRange): { start_date?: string; end_date?: string } {
  if (range === 'all') return {}
  const now = new Date()
  const end_date = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59)
  let start: Date
  if (range === 'today') {
    start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  } else if (range === '7d') {
    start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6)
  } else {
    start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 29)
  }
  return {
    start_date: start.toISOString(),
    end_date: end_date.toISOString(),
  }
}

export default function Usage() {
  const [logs, setLogs] = useState<UsageLog[]>([])
  const [daily, setDaily] = useState<DailyUsage[]>([])
  const [summary, setSummary] = useState<UsageSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [filterModel, setFilterModel] = useState('')
  const [filterProvider, setFilterProvider] = useState('')
  const [dateRange, setDateRange] = useState<DateRange>('7d')
  const [viewTab, setViewTab] = useState<ViewTab>('daily')

  const loadData = async () => {
    setLoading(true)
    try {
      const bounds = getDateBounds(dateRange)
      const params = new URLSearchParams()
      if (filterModel) params.set('model', filterModel)
      if (filterProvider) params.set('provider', filterProvider)
      if (bounds.start_date) params.set('start_date', bounds.start_date)
      if (bounds.end_date) params.set('end_date', bounds.end_date)
      const qs = params.toString() ? `?${params}` : ''

      const summaryParams = new URLSearchParams()
      if (bounds.start_date) summaryParams.set('start_date', bounds.start_date)
      if (bounds.end_date) summaryParams.set('end_date', bounds.end_date)
      const summaryQs = summaryParams.toString() ? `?${summaryParams}` : ''

      const [logsData, dailyData, summaryData] = await Promise.all([
        api.get<UsageLog[]>(`/usage${qs}`),
        api.get<DailyUsage[]>(`/usage/daily${qs}`),
        api.get<UsageSummary>(`/usage/summary${summaryQs}`),
      ])
      setLogs(logsData)
      setDaily(dailyData)
      setSummary(summaryData)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [filterModel, filterProvider, dateRange])

  const dateRanges: { key: DateRange; label: string }[] = [
    { key: 'today', label: 'Today' },
    { key: '7d', label: '7 days' },
    { key: '30d', label: '30 days' },
    { key: 'all', label: 'All Time' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold">Usage</h2>
        <div className="flex bg-zinc-900 border border-zinc-700 rounded-lg overflow-hidden">
          {dateRanges.map((r) => (
            <button
              key={r.key}
              onClick={() => setDateRange(r.key)}
              className={`px-3 py-1.5 text-sm transition-colors ${
                dateRange === r.key
                  ? 'bg-indigo-600 text-white'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MiniCard label="Requests" value={summary.total_requests.toLocaleString()} />
          <MiniCard label="Input Tokens" value={summary.total_input_tokens.toLocaleString()} />
          <MiniCard label="Output Tokens" value={summary.total_output_tokens.toLocaleString()} />
          <MiniCard label="Total Cost" value={`$${summary.total_vuzo_cost.toFixed(4)}`} />
        </div>
      )}

      {/* Filters + view toggle */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-3">
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
        <div className="flex bg-zinc-900 border border-zinc-700 rounded-lg overflow-hidden">
          <button
            onClick={() => setViewTab('daily')}
            className={`px-3 py-1.5 text-sm transition-colors ${
              viewTab === 'daily'
                ? 'bg-indigo-600 text-white'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Daily
          </button>
          <button
            onClick={() => setViewTab('requests')}
            className={`px-3 py-1.5 text-sm transition-colors ${
              viewTab === 'requests'
                ? 'bg-indigo-600 text-white'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Requests
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          {viewTab === 'daily' ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400">
                  <th className="text-left px-4 py-3 font-medium">Date</th>
                  <th className="text-left px-4 py-3 font-medium">Model</th>
                  <th className="text-left px-4 py-3 font-medium">Provider</th>
                  <th className="text-right px-4 py-3 font-medium">Requests</th>
                  <th className="text-right px-4 py-3 font-medium">Input</th>
                  <th className="text-right px-4 py-3 font-medium">Output</th>
                  <th className="text-right px-4 py-3 font-medium">Cost</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">Loading...</td>
                  </tr>
                ) : daily.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                      No usage data for this period.
                    </td>
                  </tr>
                ) : (
                  daily.map((d, i) => (
                    <tr key={`${d.date}-${d.model}-${i}`} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                      <td className="px-4 py-3 text-white text-xs">{d.date}</td>
                      <td className="px-4 py-3 font-mono text-white text-xs">{d.model}</td>
                      <td className="px-4 py-3 text-zinc-400 capitalize">{d.provider}</td>
                      <td className="px-4 py-3 text-right text-zinc-300">{d.total_requests.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right text-zinc-300">{d.input_tokens.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right text-zinc-300">{d.output_tokens.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right text-indigo-400">${d.total_cost.toFixed(6)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          ) : (
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
                      No usage data for this period.
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
          )}
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
