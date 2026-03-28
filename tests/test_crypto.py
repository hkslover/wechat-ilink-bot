"""Tests for AES-128-ECB crypto utilities."""

import base64
import os

import pytest

from wechat_bot.media.crypto import (
    aes_ecb_padded_size,
    decrypt_aes_ecb,
    encrypt_aes_ecb,
    parse_aes_key,
)


class TestAesEcb:
    def test_encrypt_decrypt_roundtrip(self):
        key = os.urandom(16)
        plaintext = b"Hello, WeChat Bot!"
        ciphertext = encrypt_aes_ecb(plaintext, key)
        assert ciphertext != plaintext
        decrypted = decrypt_aes_ecb(ciphertext, key)
        assert decrypted == plaintext

    def test_encrypt_empty(self):
        key = os.urandom(16)
        ciphertext = encrypt_aes_ecb(b"", key)
        assert len(ciphertext) == 16  # one block of padding
        decrypted = decrypt_aes_ecb(ciphertext, key)
        assert decrypted == b""

    def test_encrypt_block_aligned(self):
        key = os.urandom(16)
        plaintext = b"A" * 16
        ciphertext = encrypt_aes_ecb(plaintext, key)
        assert len(ciphertext) == 32  # 16 bytes data + 16 bytes PKCS7 padding
        assert decrypt_aes_ecb(ciphertext, key) == plaintext

    def test_large_data(self):
        key = os.urandom(16)
        plaintext = os.urandom(10000)
        ciphertext = encrypt_aes_ecb(plaintext, key)
        assert decrypt_aes_ecb(ciphertext, key) == plaintext


class TestAesEcbPaddedSize:
    def test_various_sizes(self):
        assert aes_ecb_padded_size(0) == 16
        assert aes_ecb_padded_size(1) == 16
        assert aes_ecb_padded_size(15) == 16
        assert aes_ecb_padded_size(16) == 32
        assert aes_ecb_padded_size(17) == 32


class TestParseAesKey:
    def test_raw_16_bytes(self):
        raw_key = os.urandom(16)
        encoded = base64.b64encode(raw_key).decode()
        parsed = parse_aes_key(encoded)
        assert parsed == raw_key

    def test_hex_encoded_key(self):
        raw_key = os.urandom(16)
        hex_str = raw_key.hex()  # 32 hex chars
        encoded = base64.b64encode(hex_str.encode("ascii")).decode()
        parsed = parse_aes_key(encoded)
        assert parsed == raw_key

    def test_invalid_length_raises(self):
        bad = base64.b64encode(b"too_short").decode()
        with pytest.raises(ValueError):
            parse_aes_key(bad)
