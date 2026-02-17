import { useEffect, useState } from 'react'
import { api } from '../lib/api'

interface ModelPricing {
  provider: string
  model_name: string
  input_price_per_million: number
  output_price_per_million: number
  vuzo_input_price_per_million: number
  vuzo_output_price_per_million: number
  vuzo_markup_percent: number
}

export default function Models() {
  const [models, setModels] = useState<ModelPricing[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<ModelPricing[]>('/models')
      .then(setModels)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-zinc-400">Loading models...</div>

  const grouped = models.reduce<Record<string, ModelPricing[]>>((acc, m) => {
    if (!acc[m.provider]) acc[m.provider] = []
    acc[m.provider].push(m)
    return acc
  }, {})

  const providerLabels: Record<string, string> = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google',
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-2">Models & Pricing</h2>
      <p className="text-zinc-400 text-sm mb-6">
        All prices shown per 1,000,000 tokens. Vuzo pricing includes a {models[0]?.vuzo_markup_percent ?? 20}% markup.
      </p>

      {Object.entries(grouped).map(([provider, providerModels]) => (
        <div key={provider} className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">
            {providerLabels[provider] ?? provider}
          </h3>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400">
                  <th className="text-left px-4 py-3 font-medium">Model</th>
                  <th className="text-right px-4 py-3 font-medium">Input (Provider)</th>
                  <th className="text-right px-4 py-3 font-medium">Input (Vuzo)</th>
                  <th className="text-right px-4 py-3 font-medium">Output (Provider)</th>
                  <th className="text-right px-4 py-3 font-medium">Output (Vuzo)</th>
                </tr>
              </thead>
              <tbody>
                {providerModels.map((m) => (
                  <tr key={m.model_name} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="px-4 py-3 font-mono text-white text-xs">{m.model_name}</td>
                    <td className="px-4 py-3 text-right text-zinc-400">
                      ${m.input_price_per_million.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-right text-indigo-400 font-medium">
                      ${m.vuzo_input_price_per_million.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-right text-zinc-400">
                      ${m.output_price_per_million.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-right text-indigo-400 font-medium">
                      ${m.vuzo_output_price_per_million.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}
