"""Tests for API key generation and hashing utilities (app/utils/crypto.py)."""
import hashlib
import pytest
from unittest.mock import patch, MagicMock

from app.utils.crypto import generate_api_key, get_key_prefix, hash_api_key


def test_generate_api_key_format():
    key = generate_api_key()
    assert key.startswith("vz-sk_")
    hex_part = key[len("vz-sk_"):]
    assert len(hex_part) == 48
    assert all(c in "0123456789abcdef" for c in hex_part)


def test_generate_api_key_unique():
    keys = {generate_api_key() for _ in range(100)}
    assert len(keys) == 100


def test_get_key_prefix_returns_first_8_chars():
    key = "vz-sk_aabbccdd1122334455667788"
    assert get_key_prefix(key) == "vz-sk_aa"


def test_hash_api_key_is_sha256():
    key = "vz-sk_testkey"
    expected = hashlib.sha256(key.encode("utf-8")).hexdigest()
    assert hash_api_key(key) == expected


def test_hash_api_key_deterministic():
    key = generate_api_key()
    assert hash_api_key(key) == hash_api_key(key)


def test_hash_api_key_different_keys_differ():
    key_a = generate_api_key()
    key_b = generate_api_key()
    assert hash_api_key(key_a) != hash_api_key(key_b)
