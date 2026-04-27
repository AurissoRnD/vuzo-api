import { useState, useEffect, useCallback } from 'react'
import { supabase } from '../lib/supabase'
import { api } from '../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Overview {
  total_revenue: number
  total_provider_cost: number
  total_vuzo_cost: number
  profit: number
  margin: number
  total_users: number
  active_users: number
  active_keys: number
  total_tokens: number
  total_requests: number
  daily_stats: DailyStat[]
}

interface DailyStat {
  date: string
  charged: number
  provider_cost: number
  tokens: number
  requests: number
  topups?: number
}

interface AdminUser {
  id: string
  email: string
  is_active: boolean
  is_admin: boolean
  created_at: string
  balance: number
  active_keys: number
  total_keys: number
  total_tokens: number
  total_spent: number
  total_topups: number
}

interface AdminKey {
  id: string
  user_id: string
  user_email: string
  name: string
  key_prefix: string
  is_active: boolean
  token_limit: number | null
  tokens_used: number
  cost_generated: number
  rate_limit_rpm: number
  created_at: string
  last_used_at: string | null
}

interface UsageLog {
  id: string
  user_email: string
  model: string
  provider: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  vuzo_cost: number
  provider_cost: number
  response_time_ms: number
  created_at: string
}

interface Transaction {
  id: string
  user_email: string
  type: 'topup' | 'usage' | 'refund'
  amount: number
  description: string
  created_at: string
}

type Tab = 'overview' | 'users' | 'keys' | 'usage' | 'transactions'
type AuthState = 'loading' | 'unauthenticated' | 'not_admin' | 'authenticated'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt$(n: number) { return `$${n.toFixed(2)}` }
function fmtTokens(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`
  return n.toString()
}
function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function fmtDateShort(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// ── Metric Card ───────────────────────────────────────────────────────────────

function MetricCard({
  label, value, sub, accent,
}: { label: string; value: string; sub?: string; accent: string }) {
  return (
    <div className={`bg-zinc-900 border ${accent} rounded-xl p-5`}>
      <p className="text-xs text-zinc-500 font-medium uppercase tracking-wider mb-2">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}
    </div>
  )
}

// ── Revenue Chart (SVG) ───────────────────────────────────────────────────────

function RevenueChart({ data }: { data: DailyStat[] }) {
  const last14 = data.slice(-14)
  if (last14.length === 0) return (
    <div className="h-40 flex items-center justify-center text-zinc-600 text-sm">No data yet</div>
  )

  const maxVal = Math.max(...last14.map(d => Math.max(d.topups ?? 0, d.charged, d.provider_cost)), 0.01)
  const W = 600
  const H = 140
  const pad = { top: 10, right: 10, bottom: 30, left: 48 }
  const chartW = W - pad.left - pad.right
  const chartH = H - pad.top - pad.bottom
  const barGroup = chartW / last14.length
  const barW = Math.max(4, barGroup * 0.28)

  const scaleY = (v: number) => chartH - (v / maxVal) * chartH

  const yTicks = [0, maxVal * 0.25, maxVal * 0.5, maxVal * 0.75, maxVal]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-40">
      {/* Y grid */}
      {yTicks.map((t, i) => (
        <g key={i}>
          <line
            x1={pad.left} y1={pad.top + scaleY(t)}
            x2={pad.left + chartW} y2={pad.top + scaleY(t)}
            stroke="#27272a" strokeWidth="1"
          />
          <text x={pad.left - 6} y={pad.top + scaleY(t) + 4} textAnchor="end" fontSize="9" fill="#52525b">
            {fmt$(t)}
          </text>
        </g>
      ))}

      {last14.map((d, i) => {
        const x = pad.left + i * barGroup + barGroup / 2
        const topupH = ((d.topups ?? 0) / maxVal) * chartH
        const chargedH = (d.charged / maxVal) * chartH
        const costH = (d.provider_cost / maxVal) * chartH

        return (
          <g key={d.date}>
            {/* Topups bar */}
            <rect x={x - barW * 1.5} y={pad.top + scaleY(d.topups ?? 0)} width={barW} height={topupH}
              fill="#10b981" opacity="0.8" rx="2" />
            {/* Charged bar */}
            <rect x={x - barW * 0.5} y={pad.top + scaleY(d.charged)} width={barW} height={chargedH}
              fill="#6366f1" opacity="0.8" rx="2" />
            {/* Provider cost bar */}
            <rect x={x + barW * 0.5} y={pad.top + scaleY(d.provider_cost)} width={barW} height={costH}
              fill="#f59e0b" opacity="0.7" rx="2" />
            {/* Date label */}
            <text x={x} y={H - 4} textAnchor="middle" fontSize="8" fill="#52525b">
              {d.date.slice(5)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

// ── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
      active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              : 'bg-zinc-700/40 text-zinc-500 border border-zinc-700'
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
      {active ? 'Active' : 'Disabled'}
    </span>
  )
}

// ── Token Usage Bar ───────────────────────────────────────────────────────────

function TokenBar({ used, limit }: { used: number; limit: number | null }) {
  if (!limit) return <span className="text-zinc-500 text-xs">{fmtTokens(used)} / ∞</span>
  const pct = Math.min(100, (used / limit) * 100)
  const color = pct > 90 ? 'bg-red-500' : pct > 70 ? 'bg-amber-500' : 'bg-indigo-500'
  return (
    <div className="w-full min-w-[100px]">
      <div className="flex justify-between text-xs text-zinc-500 mb-1">
        <span>{fmtTokens(used)}</span>
        <span>{fmtTokens(limit)}</span>
      </div>
      <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

// ── Overview Tab ──────────────────────────────────────────────────────────────

function OverviewTab({ data }: { data: Overview }) {
  return (
    <div>
      {/* Business metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard label="Total Revenue" value={fmt$(data.total_revenue)}
          sub="all-time topups" accent="border-emerald-900/50" />
        <MetricCard label="Total Charged" value={fmt$(data.total_vuzo_cost)}
          sub="billed to users" accent="border-indigo-900/50" />
        <MetricCard label="Provider Cost" value={fmt$(data.total_provider_cost)}
          sub="paid to Moonshot" accent="border-amber-900/50" />
        <MetricCard label="Gross Profit" value={fmt$(data.profit)}
          sub={`${data.margin.toFixed(1)}% margin`} accent={data.profit >= 0 ? 'border-emerald-900/50' : 'border-red-900/50'} />
      </div>

      {/* Operational metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <MetricCard label="Total Users" value={data.total_users.toString()}
          sub={`${data.active_users} active`} accent="border-zinc-800" />
        <MetricCard label="Active Keys" value={data.active_keys.toString()}
          sub="enabled API keys" accent="border-zinc-800" />
        <MetricCard label="Total Tokens" value={fmtTokens(data.total_tokens)}
          sub="all time" accent="border-zinc-800" />
        <MetricCard label="Total Requests" value={data.total_requests.toLocaleString()}
          sub="API calls" accent="border-zinc-800" />
        <MetricCard label="Avg per Request" value={data.total_requests > 0 ? fmtTokens(Math.round(data.total_tokens / data.total_requests)) : '—'}
          sub="tokens/request" accent="border-zinc-800" />
      </div>

      {/* Chart */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">Daily Activity — Last 14 Days</h3>
          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-emerald-500" />Topups</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-indigo-500" />Charged</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-amber-500" />Provider Cost</span>
          </div>
        </div>
        <RevenueChart data={data.daily_stats} />
      </div>
    </div>
  )
}

// ── Users Tab ─────────────────────────────────────────────────────────────────

function UsersTab({ users, onToggle }: { users: AdminUser[]; onToggle: (id: string, active: boolean) => void }) {
  const [search, setSearch] = useState('')
  const [busy, setBusy] = useState<string | null>(null)

  const filtered = users.filter(u =>
    u.email.toLowerCase().includes(search.toLowerCase())
  )

  const toggle = async (u: AdminUser) => {
    setBusy(u.id)
    try {
      await api.patch(`/admin/users/${u.id}`, { is_active: !u.is_active })
      onToggle(u.id, !u.is_active)
    } catch { /* ignore */ }
    setBusy(null)
  }

  return (
    <div>
      <div className="mb-4">
        <input
          type="text" placeholder="Search by email…" value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full max-w-sm px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-400 text-xs uppercase tracking-wide">
              <th className="text-left px-4 py-3 font-medium">User</th>
              <th className="text-right px-4 py-3 font-medium">Balance</th>
              <th className="text-right px-4 py-3 font-medium">Topups</th>
              <th className="text-right px-4 py-3 font-medium">Spent</th>
              <th className="text-right px-4 py-3 font-medium">Keys</th>
              <th className="text-right px-4 py-3 font-medium">Tokens</th>
              <th className="text-center px-4 py-3 font-medium">Status</th>
              <th className="text-right px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-10 text-center text-zinc-600">No users found.</td></tr>
            ) : filtered.map(u => (
              <tr key={u.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                <td className="px-4 py-3">
                  <div className="flex flex-col">
                    <span className="text-white font-medium text-xs">{u.email}</span>
                    <span className="text-zinc-600 text-xs">{fmtDateShort(u.created_at)}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-mono text-emerald-400 text-xs">{fmt$(u.balance)}</td>
                <td className="px-4 py-3 text-right font-mono text-indigo-400 text-xs">{fmt$(u.total_topups)}</td>
                <td className="px-4 py-3 text-right font-mono text-amber-400 text-xs">{fmt$(u.total_spent)}</td>
                <td className="px-4 py-3 text-right text-zinc-400 text-xs">{u.active_keys}/{u.total_keys}</td>
                <td className="px-4 py-3 text-right text-zinc-400 text-xs">{fmtTokens(u.total_tokens)}</td>
                <td className="px-4 py-3 text-center"><StatusBadge active={u.is_active} /></td>
                <td className="px-4 py-3 text-right">
                  {!u.is_admin && (
                    <button
                      onClick={() => toggle(u)}
                      disabled={busy === u.id}
                      className={`px-3 py-1 text-xs font-medium rounded-lg border transition-colors disabled:opacity-40 ${
                        u.is_active
                          ? 'border-red-800/60 text-red-400 hover:bg-red-950/40'
                          : 'border-emerald-800/60 text-emerald-400 hover:bg-emerald-950/40'
                      }`}
                    >
                      {busy === u.id ? '…' : u.is_active ? 'Disable' : 'Enable'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Keys Tab ──────────────────────────────────────────────────────────────────

function KeysTab({ keys, onToggle, onRotate }: {
  keys: AdminKey[]
  onToggle: (id: string, active: boolean) => void
  onRotate: (oldId: string, newKey: AdminKey) => void
}) {
  const [search, setSearch] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [rotatedKeys, setRotatedKeys] = useState<Record<string, string>>({})

  const filtered = keys.filter(k =>
    k.user_email.toLowerCase().includes(search.toLowerCase()) ||
    k.name.toLowerCase().includes(search.toLowerCase()) ||
    k.key_prefix.toLowerCase().includes(search.toLowerCase())
  )

  const toggle = async (k: AdminKey) => {
    setBusy(k.id + '-toggle')
    try {
      await api.patch(`/admin/keys/${k.id}`, { is_active: !k.is_active })
      onToggle(k.id, !k.is_active)
    } catch { /* ignore */ }
    setBusy(null)
  }

  const rotate = async (k: AdminKey) => {
    if (!confirm(`Renew key for ${k.user_email}? The current key will stop working immediately.`)) return
    setBusy(k.id + '-rotate')
    try {
      const result = await api.post<{ new_key: string; new_key_id: string; token_limit: number }>(`/admin/keys/${k.id}/rotate`)
      setRotatedKeys(prev => ({ ...prev, [result.new_key_id]: result.new_key }))
      onRotate(k.id, {
        ...k,
        id: result.new_key_id,
        is_active: true,
        tokens_used: 0,
        token_limit: result.token_limit,
      })
    } catch { /* ignore */ }
    setBusy(null)
  }

  return (
    <div>
      <div className="mb-4">
        <input
          type="text" placeholder="Search by user, name, or prefix…" value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full max-w-sm px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-400 text-xs uppercase tracking-wide">
              <th className="text-left px-4 py-3 font-medium">User / Key</th>
              <th className="text-left px-4 py-3 font-medium">Name</th>
              <th className="text-left px-4 py-3 font-medium w-48">Token Usage</th>
              <th className="text-right px-4 py-3 font-medium">Revenue</th>
              <th className="text-left px-4 py-3 font-medium">Last Used</th>
              <th className="text-center px-4 py-3 font-medium">Status</th>
              <th className="text-right px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-zinc-600">No keys found.</td></tr>
            ) : filtered.map(k => (
              <tr key={k.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                <td className="px-4 py-3">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-zinc-300 text-xs">{k.user_email}</span>
                    <span className="font-mono text-[11px] text-zinc-600">{k.key_prefix}…</span>
                    {rotatedKeys[k.id] && (
                      <div className="mt-1 flex items-center gap-1.5 px-2 py-1 bg-emerald-950/40 border border-emerald-800/50 rounded text-[10px]">
                        <span className="text-emerald-400 font-medium">New key:</span>
                        <code className="font-mono text-emerald-300 break-all">{rotatedKeys[k.id]}</code>
                        <span className="text-zinc-500 shrink-0">— shown once</span>
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-zinc-400 text-xs">{k.name}</td>
                <td className="px-4 py-3"><TokenBar used={k.tokens_used} limit={k.token_limit} /></td>
                <td className="px-4 py-3 text-right font-mono text-indigo-400 text-xs">{fmt$(k.cost_generated)}</td>
                <td className="px-4 py-3 text-zinc-500 text-xs">
                  {k.last_used_at ? fmtDate(k.last_used_at) : 'Never'}
                </td>
                <td className="px-4 py-3 text-center"><StatusBadge active={k.is_active} /></td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => toggle(k)}
                      disabled={!!busy}
                      className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors disabled:opacity-40 ${
                        k.is_active
                          ? 'border-red-800/60 text-red-400 hover:bg-red-950/40'
                          : 'border-emerald-800/60 text-emerald-400 hover:bg-emerald-950/40'
                      }`}
                    >
                      {busy === k.id + '-toggle' ? '…' : k.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => rotate(k)}
                      disabled={!!busy}
                      className="px-2.5 py-1 text-xs font-medium rounded-lg border border-indigo-800/60 text-indigo-400 hover:bg-indigo-950/40 transition-colors disabled:opacity-40"
                    >
                      {busy === k.id + '-rotate' ? '…' : 'Renew'}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Usage Tab ─────────────────────────────────────────────────────────────────

function UsageTab({ logs }: { logs: UsageLog[] }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 text-zinc-400 text-xs uppercase tracking-wide">
            <th className="text-left px-4 py-3 font-medium">Time</th>
            <th className="text-left px-4 py-3 font-medium">User</th>
            <th className="text-left px-4 py-3 font-medium">Model</th>
            <th className="text-right px-4 py-3 font-medium">In</th>
            <th className="text-right px-4 py-3 font-medium">Out</th>
            <th className="text-right px-4 py-3 font-medium">Total</th>
            <th className="text-right px-4 py-3 font-medium">Charged</th>
            <th className="text-right px-4 py-3 font-medium">Cost</th>
            <th className="text-right px-4 py-3 font-medium">Latency</th>
          </tr>
        </thead>
        <tbody>
          {logs.length === 0 ? (
            <tr><td colSpan={9} className="px-4 py-10 text-center text-zinc-600">No usage logs.</td></tr>
          ) : logs.map(u => (
            <tr key={u.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
              <td className="px-4 py-2.5 text-zinc-500 text-xs">{fmtDate(u.created_at)}</td>
              <td className="px-4 py-2.5 text-zinc-400 text-xs truncate max-w-[160px]">{u.user_email}</td>
              <td className="px-4 py-2.5 font-mono text-indigo-400 text-xs">{u.model}</td>
              <td className="px-4 py-2.5 text-right text-zinc-400 text-xs">{u.input_tokens.toLocaleString()}</td>
              <td className="px-4 py-2.5 text-right text-zinc-400 text-xs">{u.output_tokens.toLocaleString()}</td>
              <td className="px-4 py-2.5 text-right text-white text-xs font-medium">{u.total_tokens.toLocaleString()}</td>
              <td className="px-4 py-2.5 text-right font-mono text-indigo-400 text-xs">{fmt$(u.vuzo_cost)}</td>
              <td className="px-4 py-2.5 text-right font-mono text-amber-500/80 text-xs">{fmt$(u.provider_cost)}</td>
              <td className="px-4 py-2.5 text-right text-zinc-500 text-xs">{u.response_time_ms}ms</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Transactions Tab ──────────────────────────────────────────────────────────

function TransactionsTab({ txns }: { txns: Transaction[] }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 text-zinc-400 text-xs uppercase tracking-wide">
            <th className="text-left px-4 py-3 font-medium">Time</th>
            <th className="text-left px-4 py-3 font-medium">User</th>
            <th className="text-left px-4 py-3 font-medium">Type</th>
            <th className="text-right px-4 py-3 font-medium">Amount</th>
            <th className="text-left px-4 py-3 font-medium">Description</th>
          </tr>
        </thead>
        <tbody>
          {txns.length === 0 ? (
            <tr><td colSpan={5} className="px-4 py-10 text-center text-zinc-600">No transactions.</td></tr>
          ) : txns.map(t => (
            <tr key={t.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
              <td className="px-4 py-2.5 text-zinc-500 text-xs">{fmtDate(t.created_at)}</td>
              <td className="px-4 py-2.5 text-zinc-400 text-xs truncate max-w-[180px]">{t.user_email}</td>
              <td className="px-4 py-2.5">
                <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium ${
                  t.type === 'topup' ? 'bg-emerald-500/10 text-emerald-400'
                  : t.type === 'refund' ? 'bg-blue-500/10 text-blue-400'
                  : 'bg-zinc-700/40 text-zinc-400'
                }`}>{t.type}</span>
              </td>
              <td className={`px-4 py-2.5 text-right font-mono text-xs ${t.amount >= 0 ? 'text-emerald-400' : 'text-zinc-400'}`}>
                {t.amount >= 0 ? '+' : ''}{fmt$(t.amount)}
              </td>
              <td className="px-4 py-2.5 text-zinc-500 text-xs truncate max-w-xs">{t.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Login Form ────────────────────────────────────────────────────────────────

function LoginForm({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { error: authError } = await supabase.auth.signInWithPassword({ email, password })
      if (authError) throw new Error(authError.message)
      // Verify admin status
      await api.get('/admin/overview')
      onLogin()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Login failed'
      if (msg.includes('403') || msg.includes('Admin')) {
        setError('This account does not have admin access.')
      } else {
        setError(msg)
      }
      await supabase.auth.signOut()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-indigo-600 rounded-xl mb-4">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white">Admin Portal</h1>
          <p className="text-zinc-500 text-sm mt-1">SimplerClaw — Business Dashboard</p>
        </div>

        <form onSubmit={submit} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-4">
          <div>
            <label className="block text-xs text-zinc-400 font-medium mb-1.5">Email</label>
            <input
              type="email" required value={email} onChange={e => setEmail(e.target.value)}
              placeholder="admin@example.com"
              className="w-full px-3.5 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white text-sm placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-400 font-medium mb-1.5">Password</label>
            <input
              type="password" required value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3.5 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white text-sm placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-950/30 border border-red-900/50 rounded-lg">
              <svg className="w-4 h-4 text-red-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              </svg>
              <p className="text-red-400 text-xs">{error}</p>
            </div>
          )}

          <button
            type="submit" disabled={loading}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold rounded-xl transition-colors text-sm"
          >
            {loading ? 'Signing in…' : 'Sign in to Admin'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Main Admin Page ───────────────────────────────────────────────────────────

export default function Admin() {
  const [authState, setAuthState] = useState<AuthState>('loading')
  const [adminEmail, setAdminEmail] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  const [overview, setOverview] = useState<Overview | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [keys, setKeys] = useState<AdminKey[]>([])
  const [usage, setUsage] = useState<UsageLog[]>([])
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [dataLoading, setDataLoading] = useState(false)

  const loadTab = useCallback(async (tab: Tab) => {
    setDataLoading(true)
    try {
      switch (tab) {
        case 'overview':
          if (!overview) setOverview(await api.get<Overview>('/admin/overview'))
          break
        case 'users':
          setUsers(await api.get<AdminUser[]>('/admin/users'))
          break
        case 'keys':
          setKeys(await api.get<AdminKey[]>('/admin/keys'))
          break
        case 'usage':
          setUsage(await api.get<UsageLog[]>('/admin/usage'))
          break
        case 'transactions':
          setTransactions(await api.get<Transaction[]>('/admin/transactions'))
          break
      }
    } catch { /* ignore */ }
    setDataLoading(false)
  }, [overview])

  // Check session on mount
  useEffect(() => {
    const check = async () => {
      const { data } = await supabase.auth.getSession()
      if (!data.session) { setAuthState('unauthenticated'); return }
      setAdminEmail(data.session.user.email ?? '')
      try {
        const ov = await api.get<Overview>('/admin/overview')
        setOverview(ov)
        setAuthState('authenticated')
      } catch {
        setAuthState('not_admin')
        await supabase.auth.signOut()
      }
    }
    check()
  }, [])

  const handleLogin = async () => {
    const { data } = await supabase.auth.getSession()
    setAdminEmail(data.session?.user.email ?? '')
    const ov = await api.get<Overview>('/admin/overview')
    setOverview(ov)
    setAuthState('authenticated')
  }

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setAuthState('unauthenticated')
    setOverview(null)
    setUsers([])
    setKeys([])
  }

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab)
    loadTab(tab)
  }

  if (authState === 'loading') {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500 text-sm">Loading…</div>
      </div>
    )
  }

  if (authState === 'unauthenticated' || authState === 'not_admin') {
    return <LoginForm onLogin={handleLogin} />
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'users', label: 'Users' },
    { id: 'keys', label: 'API Keys' },
    { id: 'usage', label: 'Usage Logs' },
    { id: 'transactions', label: 'Transactions' },
  ]

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Top bar */}
      <header className="bg-zinc-900 border-b border-zinc-800 px-6 py-4">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center shrink-0">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <span className="font-bold text-white text-sm">SimplerClaw</span>
              <span className="ml-2 px-1.5 py-0.5 bg-indigo-600/30 border border-indigo-600/40 rounded text-[10px] text-indigo-300 font-semibold uppercase tracking-wide">Admin</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-zinc-500 text-xs">{adminEmail}</span>
            <button
              onClick={handleSignOut}
              className="px-3 py-1.5 text-xs border border-zinc-700 text-zinc-400 hover:text-white hover:border-zinc-500 rounded-lg transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Tab bar */}
      <div className="border-b border-zinc-800 bg-zinc-900/50">
        <div className="max-w-[1400px] mx-auto px-6 flex gap-1">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => handleTabChange(t.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === t.id
                  ? 'border-indigo-500 text-white'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="max-w-[1400px] mx-auto px-6 py-8">
        {dataLoading && activeTab !== 'overview' && (
          <div className="text-zinc-500 text-sm mb-4">Loading…</div>
        )}

        {activeTab === 'overview' && overview && <OverviewTab data={overview} />}

        {activeTab === 'users' && (
          <UsersTab
            users={users}
            onToggle={(id, active) =>
              setUsers(prev => prev.map(u => u.id === id ? { ...u, is_active: active } : u))
            }
          />
        )}

        {activeTab === 'keys' && (
          <KeysTab
            keys={keys}
            onToggle={(id, active) =>
              setKeys(prev => prev.map(k => k.id === id ? { ...k, is_active: active } : k))
            }
            onRotate={(oldId, newKey) =>
              setKeys(prev => prev.map(k => k.id === oldId ? newKey : k))
            }
          />
        )}

        {activeTab === 'usage' && <UsageTab logs={usage} />}
        {activeTab === 'transactions' && <TransactionsTab txns={transactions} />}
      </main>
    </div>
  )
}
