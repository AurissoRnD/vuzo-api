import { useEffect, useState } from 'react'
import { api } from '../lib/api'

interface UsageSummary {
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_provider_cost: number
  total_vuzo_cost: number
}

interface Balance {
  balance: number
}

export default function Dashboard() {
  const [balance, setBalance] = useState<number>(0)
  const [summary, setSummary] = useState<UsageSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [bal, usage] = await Promise.all([
          api.get<Balance>('/billing/balance'),
          api.get<UsageSummary>('/usage/summary'),
        ])
        setBalance(bal.balance)
        setSummary(usage)
      } catch {
        // User may not have data yet
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return <div className="text-zinc-400">Loading dashboard...</div>
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <StatCard
          label="Credit Balance"
          value={`$${balance.toFixed(4)}`}
          accent
        />
        <StatCard
          label="Total Requests"
          value={summary?.total_requests?.toLocaleString() ?? '0'}
        />
        <StatCard
          label="Total Spend"
          value={`$${(summary?.total_vuzo_cost ?? 0).toFixed(4)}`}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label="Input Tokens"
          value={(summary?.total_input_tokens ?? 0).toLocaleString()}
        />
        <StatCard
          label="Output Tokens"
          value={(summary?.total_output_tokens ?? 0).toLocaleString()}
        />
        <StatCard
          label="Total Tokens"
          value={(summary?.total_tokens ?? 0).toLocaleString()}
        />
      </div>
    </div>
  )
}

function StatCard({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
      <div className="text-sm text-zinc-400 mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${accent ? 'text-indigo-400' : 'text-white'}`}>
        {value}
      </div>
    </div>
  )
}
