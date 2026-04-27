"""
One-time migration script:
- Disables all existing models in model_pricing
- Adds kimi-k2.6 (Moonshot provider)
- Stores encrypted Moonshot API key in provider_keys

Run from the backend/ directory with env vars set:
  cd backend && python ../scripts/seed_moonshot.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from app.models.database import get_supabase
from app.utils.crypto import encrypt_provider_key

MOONSHOT_API_KEY = "sk-UpcPpxfyZkgGKO5Rwe7jtea8ANpHPiDbJleOVL8fPwAU7uyG"

KIMI_MODEL = {
    "provider": "moonshot",
    "model_name": "kimi-k2.6",
    "input_price_per_million": 0.95,   # Moonshot kimi-k2.6 cache miss rate
    "output_price_per_million": 4.00,  # Moonshot kimi-k2.6 output rate
    "vuzo_markup_percent": 20.0,
    "is_active": True,
}


def run():
    sb = get_supabase()

    # 1. Disable all existing models
    print("Disabling all existing models...")
    sb.table("model_pricing").update({"is_active": False}).neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print("Done.")

    # 2. Insert kimi-k2.6
    print("Inserting kimi-k2.6...")
    existing = sb.table("model_pricing").select("id").eq("model_name", "kimi-k2.6").execute()
    if existing.data:
        sb.table("model_pricing").update({"is_active": True}).eq("model_name", "kimi-k2.6").execute()
        print("kimi-k2.6 already existed — re-activated.")
    else:
        sb.table("model_pricing").insert(KIMI_MODEL).execute()
        print("kimi-k2.6 inserted.")

    # 3. Store encrypted Moonshot API key
    print("Storing Moonshot API key...")
    encrypted = encrypt_provider_key(MOONSHOT_API_KEY)
    existing_key = sb.table("provider_keys").select("id").eq("provider", "moonshot").execute()
    if existing_key.data:
        sb.table("provider_keys").update({
            "api_key_encrypted": encrypted,
            "is_active": True,
        }).eq("provider", "moonshot").execute()
        print("Moonshot key updated.")
    else:
        sb.table("provider_keys").insert({
            "provider": "moonshot",
            "api_key_encrypted": encrypted,
            "is_active": True,
        }).execute()
        print("Moonshot key inserted.")

    print("\nDone. kimi-k2.6 is now the only active model.")


if __name__ == "__main__":
    run()
