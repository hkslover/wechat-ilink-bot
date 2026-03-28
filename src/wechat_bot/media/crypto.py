"""AES-128-ECB encryption / decryption utilities for WeChat CDN media."""

from __future__ import annotations

import base64
import re

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

__all__ = [
    "encrypt_aes_ecb",
    "decrypt_aes_ecb",
    "aes_ecb_padded_size",
    "parse_aes_key",
]

_BLOCK_BITS = 128


def encrypt_aes_ecb(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt with AES-128-ECB + PKCS7 padding."""
    padder = PKCS7(_BLOCK_BITS).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    enc = cipher.encryptor()
    return enc.update(padded) + enc.finalize()


def decrypt_aes_ecb(ciphertext: bytes, key: bytes) -> bytes:
    """Decrypt AES-128-ECB + PKCS7 padding."""
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    dec = cipher.decryptor()
    padded = dec.update(ciphertext) + dec.finalize()
    unpadder = PKCS7(_BLOCK_BITS).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def aes_ecb_padded_size(plaintext_size: int) -> int:
    """Compute ciphertext size after AES-128-ECB with PKCS7 padding."""
    return ((plaintext_size // 16) + 1) * 16


_HEX32_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def parse_aes_key(aes_key_base64: str) -> bytes:
    """Parse a CDNMedia ``aes_key`` field into a raw 16-byte AES key.

    Two encodings exist:
      - base64(raw 16 bytes) -- images
      - base64(hex string of 16 bytes, i.e. 32 hex chars) -- file / voice / video
    """
    decoded = base64.b64decode(aes_key_base64)
    if len(decoded) == 16:
        return decoded
    if len(decoded) == 32 and _HEX32_RE.match(decoded.decode("ascii", errors="replace")):
        return bytes.fromhex(decoded.decode("ascii"))
    raise ValueError(
        f"aes_key must decode to 16 raw bytes or 32-char hex string, got {len(decoded)} bytes"
    )
