import CodeBlock from '../components/docs/CodeBlock'

export default function SdkDocs() {
  return (
    <div className="max-w-5xl">
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="bg-indigo-600 rounded-lg p-2.5 shrink-0">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-white">Python SDK Reference</h1>
        </div>
        <p className="text-zinc-400 text-lg">
          Full API reference for the <code className="px-2 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-sm text-indigo-400">vuzo</code> Python package — sync and async clients, all modules, and error handling.
        </p>
        <div className="flex items-center gap-4 mt-4">
          <a
            href="https://pypi.org/project/vuzo/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 rounded text-sm text-zinc-300 font-medium transition-colors"
          >
            PyPI
          </a>
          <a
            href="https://github.com/AurissoRnD/vuzo-python"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 rounded text-sm text-zinc-300 font-medium transition-colors"
          >
            GitHub
          </a>
          <span className="text-zinc-600 text-sm">v0.2.0</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <aside className="lg:col-span-1">
          <nav className="sticky top-8 space-y-1">
            <NavLink href="#installation">Installation</NavLink>
            <NavLink href="#sync-client">Sync Client</NavLink>
            <NavLink href="#async-client">Async Client</NavLink>
            <NavLink href="#chat">chat</NavLink>
            <NavLink href="#models">models</NavLink>
            <NavLink href="#usage">usage</NavLink>
            <NavLink href="#billing">billing</NavLink>
            <NavLink href="#api-keys">api_keys</NavLink>
            <NavLink href="#errors">Errors</NavLink>
            <NavLink href="#env-vars">Environment Variables</NavLink>
          </nav>
        </aside>

        <div className="lg:col-span-3 space-y-12">

          <Section id="installation" title="Installation">
            <p className="text-zinc-300 mb-4">
              Requires Python 3.8+. Install the base package with <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">requests</code> and <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">pydantic</code>. Add the <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">async</code> extra for <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">httpx</code>-based async support.
            </p>
            <CodeBlock language="bash" code={`# Sync client only
pip install vuzo

# Sync + async client
pip install "vuzo[async]"`} />
          </Section>

          <Section id="sync-client" title="Sync Client — Vuzo">
            <p className="text-zinc-300 mb-4">
              <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs text-indigo-400">Vuzo(api_key?, base_url?)</code> — the main synchronous client. Uses <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">requests</code> under the hood.
            </p>

            <h4 className="text-white font-semibold mb-3">Constructor</h4>
            <ParamTable params={[
              { name: 'api_key', type: 'str | None', desc: 'Your Vuzo key (vz-sk_…). Falls back to VUZO_API_KEY env var.' },
              { name: 'base_url', type: 'str', desc: 'API base URL. Defaults to https://vuzo-api.onrender.com/v1' },
            ]} />

            <h4 className="text-white font-semibold mt-6 mb-3">Attributes</h4>
            <ParamTable params={[
              { name: 'chat', type: 'ChatCompletions', desc: 'Chat completions module' },
              { name: 'models', type: 'Models', desc: 'Model listing module' },
              { name: 'usage', type: 'Usage', desc: 'Usage analytics module' },
              { name: 'billing', type: 'Billing', desc: 'Billing and balance module' },
              { name: 'api_keys', type: 'APIKeys', desc: 'API key management module' },
            ]} />

            <CodeBlock language="python" code={`from vuzo import Vuzo

# Pass key directly
client = Vuzo("vz-sk_your_key_here")

# Or use environment variable VUZO_API_KEY
client = Vuzo()

# Custom base URL (for self-hosted deployments)
client = Vuzo("vz-sk_...", base_url="https://your-api.example.com/v1")`} />
          </Section>

          <Section id="async-client" title="Async Client — AsyncVuzo">
            <p className="text-zinc-300 mb-4">
              <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs text-indigo-400">AsyncVuzo(api_key?, base_url?)</code> — async counterpart using <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">httpx.AsyncClient</code>. Requires <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">pip install "vuzo[async]"</code>.
            </p>

            <h4 className="text-white font-semibold mb-3">Constructor</h4>
            <ParamTable params={[
              { name: 'api_key', type: 'str | None', desc: 'Your Vuzo key (vz-sk_…). Falls back to VUZO_API_KEY env var.' },
              { name: 'base_url', type: 'str', desc: 'API base URL. Defaults to https://vuzo-api.onrender.com/v1' },
            ]} />

            <h4 className="text-white font-semibold mt-6 mb-3">Attributes</h4>
            <ParamTable params={[
              { name: 'chat', type: 'AsyncChatCompletions', desc: 'Async chat completions module' },
              { name: 'models', type: 'AsyncModels', desc: 'Async model listing module' },
              { name: 'usage', type: 'AsyncUsage', desc: 'Async usage analytics module' },
              { name: 'billing', type: 'AsyncBilling', desc: 'Async billing and balance module' },
              { name: 'api_keys', type: 'AsyncAPIKeys', desc: 'Async API key management module' },
            ]} />

            <CodeBlock language="python" code={`from vuzo import AsyncVuzo
import asyncio

# As a context manager (recommended — ensures connection cleanup)
async def main():
    async with AsyncVuzo("vz-sk_your_key_here") as client:
        response = await client.chat.complete("gpt-4o-mini", "Hello!")
        print(response)

asyncio.run(main())

# Or instantiate manually and close when done
async def main():
    client = AsyncVuzo("vz-sk_your_key_here")
    response = await client.chat.complete("gpt-4o-mini", "Hello!")
    await client.close()
    return response`} />
          </Section>

          <Section id="chat" title="chat">
            <p className="text-zinc-300 mb-4">Accessed via <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">client.chat</code>.</p>

            <MethodBlock
              name="chat.complete(model, prompt, **kwargs)"
              returns="str"
              desc="Convenience one-liner. Sends a single user message and returns the assistant's text content directly."
              params={[
                { name: 'model', type: 'str', desc: 'Model ID, e.g. "gpt-4o-mini"' },
                { name: 'prompt', type: 'str', desc: 'The user message' },
                { name: '**kwargs', type: 'any', desc: 'Forwarded to create() — temperature, max_tokens, etc.' },
              ]}
            />
            <CodeBlock language="python" code={`text = client.chat.complete("gpt-4o-mini", "Explain relativity.")
print(text)  # plain string`} />

            <MethodBlock
              name="chat.create(model, messages, **kwargs)"
              returns="ChatCompletion"
              desc="Full chat completions call. Returns a Pydantic model matching the OpenAI response schema."
              params={[
                { name: 'model', type: 'str', desc: 'Model ID' },
                { name: 'messages', type: 'list[dict]', desc: 'Array of {role, content} dicts' },
                { name: 'temperature', type: 'float', desc: 'Optional. 0–2 sampling temperature' },
                { name: 'max_tokens', type: 'int', desc: 'Optional. Max tokens to generate' },
                { name: 'stream', type: 'bool', desc: 'Optional. Set True to use streaming — returns an iterator instead' },
                { name: 'top_p', type: 'float', desc: 'Optional. Nucleus sampling parameter' },
              ]}
            />
            <CodeBlock language="python" code={`response = client.chat.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2 + 2?"},
    ],
    temperature=0.5,
    max_tokens=100,
)

print(response.choices[0].message.content)
print(f"Tokens: {response.usage.total_tokens}")`} />

            <MethodBlock
              name="chat.stream(model, messages, **kwargs)"
              returns="Iterator[str]"
              desc="Streaming variant. Yields text chunks as they arrive. Calls create() with stream=True internally."
              params={[
                { name: 'model', type: 'str', desc: 'Model ID' },
                { name: 'messages', type: 'list[dict]', desc: 'Array of {role, content} dicts' },
                { name: '**kwargs', type: 'any', desc: 'Forwarded to create()' },
              ]}
            />
            <CodeBlock language="python" code={`for chunk in client.chat.stream("gpt-4o-mini", [{"role": "user", "content": "Count to 5."}]):
    print(chunk, end="", flush=True)
print()`} />

            <div className="mt-6 p-4 bg-indigo-950/30 border border-indigo-900/50 rounded-lg">
              <p className="text-indigo-300 text-sm font-medium mb-1">Async equivalents</p>
              <p className="text-indigo-300/80 text-sm">
                <code className="px-1.5 py-0.5 bg-indigo-900/50 rounded text-xs">await client.chat.complete()</code>,{' '}
                <code className="px-1.5 py-0.5 bg-indigo-900/50 rounded text-xs">await client.chat.create()</code>, and{' '}
                <code className="px-1.5 py-0.5 bg-indigo-900/50 rounded text-xs">async for chunk in client.chat.stream()</code> — same signatures.
              </p>
            </div>
          </Section>

          <Section id="models" title="models">
            <p className="text-zinc-300 mb-4">Accessed via <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">client.models</code>.</p>

            <MethodBlock
              name="models.list()"
              returns="list[ModelPricingItem]"
              desc="Returns all available models with their provider and per-million-token pricing."
              params={[]}
            />
            <MethodBlock
              name="models.get(model_name)"
              returns="ModelPricingItem"
              desc="Fetch a single model's details. Calls GET /v1/models/{model_name} directly."
              params={[
                { name: 'model_name', type: 'str', desc: 'Model ID, e.g. "gpt-4o-mini"' },
              ]}
            />
            <CodeBlock language="python" code={`# List all models
models = client.models.list()
for m in models:
    print(f"{m.id} | {m.provider} | in: \${m.input_price_per_million}/M | out: \${m.output_price_per_million}/M")

# Fetch a single model
model = client.models.get("gpt-4o-mini")
print(model.provider)  # "openai"`} />

            <h4 className="text-white font-semibold mt-6 mb-3">ModelPricingItem fields</h4>
            <ParamTable params={[
              { name: 'id', type: 'str', desc: 'Model ID used in API calls' },
              { name: 'provider', type: 'str', desc: '"openai" | "xai" | "google" | "anthropic"' },
              { name: 'input_price_per_million', type: 'float', desc: 'USD per 1M input tokens' },
              { name: 'output_price_per_million', type: 'float', desc: 'USD per 1M output tokens' },
            ]} />
          </Section>

          <Section id="usage" title="usage">
            <p className="text-zinc-300 mb-4">Accessed via <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">client.usage</code>. All methods require authentication.</p>

            <MethodBlock
              name="usage.list(limit?, offset?)"
              returns="list[UsageLog]"
              desc="Returns individual request logs in reverse-chronological order."
              params={[
                { name: 'limit', type: 'int', desc: 'Optional. Max records to return (default 50)' },
                { name: 'offset', type: 'int', desc: 'Optional. Skip N records for pagination (default 0)' },
              ]}
            />
            <MethodBlock
              name="usage.summary()"
              returns="UsageSummary"
              desc="Aggregate totals: total requests, tokens, and cost across all time."
              params={[]}
            />
            <MethodBlock
              name="usage.daily(start_date?, end_date?)"
              returns="list[DailyUsage]"
              desc="Per-model, per-day breakdown for a date range."
              params={[
                { name: 'start_date', type: 'str', desc: 'Optional. ISO date string, e.g. "2025-01-01"' },
                { name: 'end_date', type: 'str', desc: 'Optional. ISO date string, e.g. "2025-01-31"' },
              ]}
            />
            <CodeBlock language="python" code={`# Recent logs
logs = client.usage.list(limit=10)
for log in logs:
    print(f"{log.model}: {log.total_tokens} tokens — \${log.vuzo_cost:.6f}")

# All-time summary
summary = client.usage.summary()
print(f"Requests: {summary.total_requests}, Cost: \${summary.total_vuzo_cost:.4f}")

# Daily breakdown
daily = client.usage.daily(start_date="2025-01-01", end_date="2025-01-31")
for day in daily:
    print(f"{day.date} | {day.model}: {day.total_requests} reqs")`} />
          </Section>

          <Section id="billing" title="billing">
            <p className="text-zinc-300 mb-4">Accessed via <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">client.billing</code>.</p>

            <MethodBlock
              name="billing.get_balance()"
              returns="float"
              desc="Returns the current credit balance in USD."
              params={[]}
            />
            <MethodBlock
              name="billing.transactions(limit?, offset?)"
              returns="list[Transaction]"
              desc="Returns credit transaction history (top-ups and usage deductions)."
              params={[
                { name: 'limit', type: 'int', desc: 'Optional. Max records to return' },
                { name: 'offset', type: 'int', desc: 'Optional. Pagination offset' },
              ]}
            />
            <CodeBlock language="python" code={`balance = client.billing.get_balance()
print(f"Balance: \${balance:.4f}")

txns = client.billing.transactions()
for tx in txns:
    print(f"{tx.created_at}: {tx.type} \${tx.amount:.4f}")`} />

            <h4 className="text-white font-semibold mt-6 mb-3">Transaction fields</h4>
            <ParamTable params={[
              { name: 'id', type: 'str', desc: 'Transaction ID' },
              { name: 'type', type: 'str', desc: '"topup" | "usage"' },
              { name: 'amount', type: 'float', desc: 'USD amount (positive = credit added, negative = deducted)' },
              { name: 'created_at', type: 'str', desc: 'ISO 8601 timestamp' },
            ]} />
          </Section>

          <Section id="api-keys" title="api_keys">
            <p className="text-zinc-300 mb-4">Accessed via <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">client.api_keys</code>.</p>

            <MethodBlock
              name="api_keys.list()"
              returns="list[APIKey]"
              desc="Lists all API keys belonging to the authenticated user."
              params={[]}
            />
            <MethodBlock
              name="api_keys.create(name)"
              returns="APIKeyCreated"
              desc="Creates a new API key. The raw key value is only returned once — save it immediately."
              params={[
                { name: 'name', type: 'str', desc: 'Human-readable label for the key' },
              ]}
            />
            <MethodBlock
              name="api_keys.delete(key_id)"
              returns="None"
              desc="Permanently deletes an API key by its ID."
              params={[
                { name: 'key_id', type: 'str', desc: 'The key ID (not the key prefix)' },
              ]}
            />
            <CodeBlock language="python" code={`# List keys
keys = client.api_keys.list()
for key in keys:
    print(f"{key.name}: {key.key_prefix}... (active: {key.is_active})")

# Create a new key
new_key = client.api_keys.create("Production Key")
print(f"Save this — shown only once: {new_key.api_key}")

# Delete a key
client.api_keys.delete(keys[0].id)`} />
          </Section>

          <Section id="errors" title="Errors">
            <p className="text-zinc-300 mb-4">
              All errors extend <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs text-indigo-400">APIError</code>. Import them from the top-level <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">vuzo</code> package.
            </p>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden mb-6">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800">
                    <th className="text-left px-4 py-3 text-zinc-400 font-medium">Exception</th>
                    <th className="text-left px-4 py-3 text-zinc-400 font-medium">HTTP Status</th>
                    <th className="text-left px-4 py-3 text-zinc-400 font-medium">Cause</th>
                  </tr>
                </thead>
                <tbody className="text-zinc-300">
                  {[
                    ['AuthenticationError', '401', 'Invalid or missing API key'],
                    ['InsufficientCreditsError', '402', 'Balance too low to complete the request'],
                    ['RateLimitError', '429', 'Too many requests — back off and retry'],
                    ['InvalidRequestError', '400', 'Bad model name, malformed messages, etc.'],
                    ['APIError', 'any', 'Base class; also raised for 5xx server errors'],
                  ].map(([cls, code, cause]) => (
                    <tr key={cls} className="border-b border-zinc-800/50">
                      <td className="px-4 py-3 font-mono text-xs text-indigo-400">{cls}</td>
                      <td className="px-4 py-3">{code}</td>
                      <td className="px-4 py-3 text-zinc-400">{cause}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <CodeBlock language="python" code={`from vuzo import (
    Vuzo,
    AuthenticationError,
    InsufficientCreditsError,
    RateLimitError,
    InvalidRequestError,
    APIError,
)

client = Vuzo("vz-sk_your_key_here")

try:
    response = client.chat.complete("gpt-4o-mini", "Hello!")
except AuthenticationError:
    print("Invalid API key — check your vz-sk_ key")
except InsufficientCreditsError:
    print("Top up your balance at the Vuzo dashboard")
except RateLimitError as e:
    print(f"Rate limited — retry after a moment")
except InvalidRequestError as e:
    print(f"Bad request: {e}")
except APIError as e:
    print(f"API error {e.status_code}: {e}")`} />

            <p className="text-zinc-400 text-sm mt-4">
              All <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">APIError</code> instances expose a <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">status_code: int</code> attribute and a <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs">message: str</code> attribute.
            </p>
          </Section>

          <Section id="env-vars" title="Environment Variables">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800">
                    <th className="text-left px-4 py-3 text-zinc-400 font-medium">Variable</th>
                    <th className="text-left px-4 py-3 text-zinc-400 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody className="text-zinc-300">
                  <tr className="border-b border-zinc-800/50">
                    <td className="px-4 py-3 font-mono text-xs text-indigo-400">VUZO_API_KEY</td>
                    <td className="px-4 py-3 text-zinc-400">Your Vuzo API key (<code className="px-1 py-0.5 bg-zinc-800 rounded text-xs">vz-sk_…</code>). Used when no key is passed to the constructor.</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <CodeBlock language="bash" code={`export VUZO_API_KEY="vz-sk_your_key_here"`} />
            <CodeBlock language="python" code={`# No key argument needed when env var is set
from vuzo import Vuzo
client = Vuzo()  # reads VUZO_API_KEY automatically`} />
          </Section>

        </div>
      </div>
    </div>
  )
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-8">
      <h2 className="text-2xl font-bold text-white mb-4">{title}</h2>
      {children}
    </section>
  )
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="block px-3 py-2 text-sm text-zinc-400 hover:text-white hover:bg-zinc-900 rounded-lg transition-colors"
    >
      {children}
    </a>
  )
}

function MethodBlock({
  name,
  returns,
  desc,
  params,
}: {
  name: string
  returns: string
  desc: string
  params: { name: string; type: string; desc: string }[]
}) {
  return (
    <div className="mb-4">
      <div className="bg-zinc-950 border border-zinc-800 rounded-t-lg px-4 py-3 font-mono text-sm">
        <span className="text-indigo-400">{name}</span>
        <span className="text-zinc-500 ml-2">→ {returns}</span>
      </div>
      <div className="bg-zinc-900/50 border border-t-0 border-zinc-800 rounded-b-lg px-4 py-3">
        <p className="text-zinc-300 text-sm mb-3">{desc}</p>
        {params.length > 0 && (
          <table className="w-full text-xs">
            <tbody>
              {params.map((p) => (
                <tr key={p.name} className="border-t border-zinc-800/50 first:border-0">
                  <td className="py-1.5 pr-3 font-mono text-indigo-300 whitespace-nowrap">{p.name}</td>
                  <td className="py-1.5 pr-3 text-zinc-500 whitespace-nowrap">{p.type}</td>
                  <td className="py-1.5 text-zinc-400">{p.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function ParamTable({ params }: { params: { name: string; type: string; desc: string }[] }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden mb-4">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800">
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium text-xs">Parameter</th>
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium text-xs">Type</th>
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium text-xs">Description</th>
          </tr>
        </thead>
        <tbody className="text-zinc-300">
          {params.map((p) => (
            <tr key={p.name} className="border-b border-zinc-800/50">
              <td className="px-4 py-2.5 font-mono text-xs text-indigo-400">{p.name}</td>
              <td className="px-4 py-2.5 text-xs text-zinc-500">{p.type}</td>
              <td className="px-4 py-2.5 text-xs text-zinc-400">{p.desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
