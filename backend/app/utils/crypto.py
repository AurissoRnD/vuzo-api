import hashlib
import secrets
from cryptography.fernet import Fernet
from app.config import get_settings

KEY_PREFIX_LENGTH = 8


def generate_api_key() -> str:
    """Generate a Vuzo API key in the format: vz-sk_<random_48_hex_chars>"""
    random_part = secrets.token_hex(24)
    return f"vz-sk_{random_part}"


def get_key_prefix(api_key: str) -> str:
    """Extract the lookup prefix (first 8 chars) from an API key."""
    return api_key[:KEY_PREFIX_LENGTH]


def hash_api_key(api_key: str) -> str:
    """SHA-256 hash an API key for secure storage."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.provider_encryption_key.encode("utf-8"))


def encrypt_provider_key(plaintext_key: str) -> str:
    """Encrypt a provider API key for storage."""
    f = _get_fernet()
    return f.encrypt(plaintext_key.encode("utf-8")).decode("utf-8")


def decrypt_provider_key(encrypted_key: str) -> str:
    """Decrypt a provider API key from storage."""
    f = _get_fernet()
    return f.decrypt(encrypted_key.encode("utf-8")).decode("utf-8")
