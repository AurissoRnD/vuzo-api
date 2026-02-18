#!/usr/bin/env python3
"""
Interactive chat script for Vuzo API.

Usage:
    python chat.py                          # prompts for model selection
    python chat.py --model gpt-4o-mini      # skip model picker
    python chat.py --key vz-sk_abc123...    # pass key directly
    python chat.py --stream                 # enable streaming responses

Requires: pip install openai
"""

import argparse
import sys

try:
    from openai import OpenAI
except ImportError:
    print("Missing dependency. Install it with:\n  pip install openai")
    sys.exit(1)

VUZO_BASE_URL = "http://localhost:8000/v1"

MODELS = {
    "1": ("gpt-4o",                    "OpenAI     — GPT-4o (flagship)"),
    "2": ("gpt-4o-mini",               "OpenAI     — GPT-4o Mini (fast & cheap)"),
    "3": ("gpt-4.1",                   "OpenAI     — GPT-4.1"),
    "4": ("gpt-4.1-mini",              "OpenAI     — GPT-4.1 Mini"),
    "5": ("gpt-4.1-nano",              "OpenAI     — GPT-4.1 Nano (cheapest)"),
    "6": ("claude-sonnet-4-20250514",  "Anthropic  — Claude Sonnet 4"),
    "7": ("claude-haiku-4-5",          "Anthropic  — Claude Haiku 4.5"),
    "8": ("claude-opus-4-5",           "Anthropic  — Claude Opus 4.5"),
    "9": ("gemini-2.0-flash",          "Google     — Gemini 2.0 Flash (cheapest)"),
    "10": ("gemini-3-flash",           "Google     — Gemini 3 Flash"),
}


def pick_model() -> str:
    print("\n╔══════════════════════════════════════════════════╗")
    print("║              Available Models                    ║")
    print("╠══════════════════════════════════════════════════╣")
    for num, (model_id, label) in MODELS.items():
        print(f"║  {num:>2}. {label:<44} ║")
    print("╚══════════════════════════════════════════════════╝")

    while True:
        choice = input("\nPick a model number (1-10): ").strip()
        if choice in MODELS:
            model_id, label = MODELS[choice]
            print(f"→ Selected: {model_id}\n")
            return model_id
        print("Invalid choice, try again.")


def chat_loop(client: OpenAI, model: str, stream: bool):
    messages = []
    print("=" * 52)
    print(f"  Chatting with {model}")
    print(f"  Type 'quit' to exit, 'clear' to reset history")
    print("=" * 52)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("Goodbye!")
            break
        if user_input.lower() == "clear":
            messages.clear()
            print("— conversation cleared —")
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            if stream:
                print(f"\n{model}: ", end="", flush=True)
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                )
                full_reply = ""
                for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        print(delta.content, end="", flush=True)
                        full_reply += delta.content
                print()
                messages.append({"role": "assistant", "content": full_reply})
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                )
                reply = response.choices[0].message.content
                messages.append({"role": "assistant", "content": reply})
                print(f"\n{model}: {reply}")

                usage = response.usage
                if usage:
                    print(
                        f"  [{usage.prompt_tokens} in / "
                        f"{usage.completion_tokens} out / "
                        f"{usage.total_tokens} total tokens]"
                    )

        except Exception as e:
            print(f"\nError: {e}")
            messages.pop()


def main():
    parser = argparse.ArgumentParser(description="Chat with LLMs via Vuzo API")
    parser.add_argument("--key", help="Vuzo API key (vz-sk_...)")
    parser.add_argument("--model", help="Model name to use (skips picker)")
    parser.add_argument("--stream", action="store_true", help="Stream responses token-by-token")
    parser.add_argument("--base-url", default=VUZO_BASE_URL, help="Vuzo API base URL")
    args = parser.parse_args()

    api_key = args.key
    if not api_key:
        api_key = input("Enter your Vuzo API key (vz-sk_...): ").strip()
    if not api_key:
        print("No API key provided. Exiting.")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=args.base_url)

    model = args.model if args.model else pick_model()

    chat_loop(client, model, stream=args.stream)


if __name__ == "__main__":
    main()
