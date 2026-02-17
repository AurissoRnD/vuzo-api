#!/usr/bin/env python3
"""
Vuzo API Key Test Script
========================
Tests your Vuzo API key by sending a request to one model from each provider.

Usage:
    python test_key.py <your-vuzo-api-key>
    python test_key.py                        # will prompt for the key
"""

import sys
import json
import requests

VUZO_BASE_URL = "http://localhost:8000/v1"

TEST_MODELS = [
    ("openai", "gpt-4o-mini"),
    ("xai", "grok-3-mini"),
    ("google", "gemini-2.0-flash"),
]

TEST_MESSAGE = "Say hello and tell me what model you are in one short sentence."


def test_model(api_key: str, provider: str, model: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  Provider: {provider}")
    print(f"  Model:    {model}")
    print(f"{'─' * 50}")

    try:
        resp = requests.post(
            f"{VUZO_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": TEST_MESSAGE}],
                "max_tokens": 100,
            },
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"  ERROR {resp.status_code}: {resp.text}")
            return

        data = resp.json()

        content = ""
        if "choices" in data and data["choices"]:
            msg = data["choices"][0].get("message", {})
            content = msg.get("content", "")
        elif "candidates" in data and data["candidates"]:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            content = parts[0].get("text", "") if parts else ""

        usage = data.get("usage", data.get("usageMetadata", {}))
        input_tok = usage.get("prompt_tokens", usage.get("promptTokenCount", 0))
        output_tok = usage.get("completion_tokens", usage.get("candidatesTokenCount", 0))

        print(f"  Response: {content.strip()[:200]}")
        print(f"  Tokens:   {input_tok} input + {output_tok} output = {input_tok + output_tok} total")

    except requests.ConnectionError:
        print("  ERROR: Could not connect. Is the Vuzo server running on localhost:8000?")
    except requests.Timeout:
        print("  ERROR: Request timed out after 30s.")
    except Exception as e:
        print(f"  ERROR: {e}")


def main():
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        api_key = input("Enter your Vuzo API key: ").strip()

    if not api_key.startswith("vz-"):
        print("Warning: Vuzo keys start with 'vz-'. Are you sure this is correct?")

    print(f"\nTesting Vuzo API key: {api_key[:12]}...")
    print(f"Server: {VUZO_BASE_URL}")

    # Check server health first
    try:
        health = requests.get(f"{VUZO_BASE_URL.replace('/v1', '')}/health", timeout=5)
        if health.status_code == 200:
            print("Server: OK")
        else:
            print(f"Server: returned {health.status_code}")
    except requests.ConnectionError:
        print("Server: NOT REACHABLE -- start it with 'python run.py'")
        sys.exit(1)

    for provider, model in TEST_MODELS:
        test_model(api_key, provider, model)

    print(f"\n{'─' * 50}")
    print("Done! Check your usage at http://localhost:5173/usage")


if __name__ == "__main__":
    main()
