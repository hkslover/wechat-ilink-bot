"""CDN media download with AES-128-ECB decryption."""

from __future__ import annotations

import asyncio
import os
from urllib.parse import quote

import httpx

from .._logging import logger
from ..errors import MediaError
from ..models import CDNMedia
from .crypto import decrypt_aes_ecb, parse_aes_key

__all__ = ["download_and_decrypt", "download_plain"]

_CDN_MAX_RETRIES = 3
_CDN_RETRY_DELAY_S = 0.8


def _build_cdn_download_url(encrypted_query_param: str, cdn_base_url: str) -> str:
    base = cdn_base_url.rstrip("/")
    return f"{base}/download?encrypted_query_param={quote(encrypted_query_param, safe='')}"


async def _fetch_cdn_bytes(url: str) -> bytes:
    last_error: MediaError | None = None
    for attempt in range(1, _CDN_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(follow_redirects=True) as http:
                resp = await http.get(url, timeout=60.0)
        except httpx.HTTPError as exc:
            msg = f"CDN download network error: {exc}"
            last_error = MediaError(msg)
            if attempt < _CDN_MAX_RETRIES:
                logger.warning(
                    "CDN download attempt %d/%d failed (%s), retrying",
                    attempt,
                    _CDN_MAX_RETRIES,
                    msg,
                )
                await asyncio.sleep(_CDN_RETRY_DELAY_S)
                continue
            raise last_error from exc

        if resp.is_success:
            return resp.content

        body_preview = resp.text[:200].replace("\n", " ").strip() if resp.text else ""
        msg = f"CDN download failed: {resp.status_code} {resp.reason_phrase}"
        if body_preview:
            msg = f"{msg} body={body_preview}"
        last_error = MediaError(msg)

        retryable = 500 <= resp.status_code < 600
        if retryable and attempt < _CDN_MAX_RETRIES:
            logger.warning(
                "CDN download attempt %d/%d got %s, retrying",
                attempt,
                _CDN_MAX_RETRIES,
                resp.status_code,
            )
            await asyncio.sleep(_CDN_RETRY_DELAY_S)
            continue
        raise last_error

    raise last_error or MediaError("CDN download failed")


async def download_and_decrypt(
    media: CDNMedia,
    cdn_base_url: str,
    *,
    aeskey_hex_override: str | None = None,
) -> bytes:
    """Download an encrypted media file from CDN and decrypt it.

    Args:
        media: CDNMedia reference from an inbound message item.
        cdn_base_url: CDN base URL.
        aeskey_hex_override: Optional hex-encoded AES key (e.g. from
            ``ImageItem.aeskey``). Takes precedence over ``media.aes_key``.

    Returns:
        Decrypted file bytes.
    """
    if aeskey_hex_override:
        key = bytes.fromhex(aeskey_hex_override)
        if len(key) != 16:
            raise MediaError(f"aeskey_hex must be 32 hex chars (16 bytes), got {len(key)}")
    elif media.aes_key:
        key = parse_aes_key(media.aes_key)
    else:
        raise MediaError("No AES key available for decryption")

    if media.full_url:
        url = media.full_url
    elif media.encrypt_query_param:
        url = _build_cdn_download_url(media.encrypt_query_param, cdn_base_url)
    else:
        raise MediaError("No download URL or encrypt_query_param available")

    encrypted = await _fetch_cdn_bytes(url)
    logger.debug("Downloaded %d bytes, decrypting", len(encrypted))
    decrypted = decrypt_aes_ecb(encrypted, key)
    logger.debug("Decrypted to %d bytes", len(decrypted))
    return decrypted


async def download_plain(
    media: CDNMedia,
    cdn_base_url: str,
) -> bytes:
    """Download an unencrypted media file from CDN.

    Args:
        media: CDNMedia reference.
        cdn_base_url: CDN base URL.

    Returns:
        Raw file bytes.
    """
    if media.full_url:
        url = media.full_url
    elif media.encrypt_query_param:
        url = _build_cdn_download_url(media.encrypt_query_param, cdn_base_url)
    else:
        raise MediaError("No download URL or encrypt_query_param available")

    return await _fetch_cdn_bytes(url)


async def download_media_to_file(
    media: CDNMedia,
    cdn_base_url: str,
    save_dir: str,
    filename: str = "media.bin",
    *,
    aeskey_hex_override: str | None = None,
) -> str:
    """Download, optionally decrypt, and save a media file.

    Returns:
        The path to the saved file.
    """
    has_key = bool(aeskey_hex_override or media.aes_key)
    if has_key:
        data = await download_and_decrypt(
            media, cdn_base_url, aeskey_hex_override=aeskey_hex_override
        )
    else:
        data = await download_plain(media, cdn_base_url)

    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, filename)
    with open(path, "wb") as f:
        f.write(data)
    logger.debug("Saved media to %s (%d bytes)", path, len(data))
    return path
