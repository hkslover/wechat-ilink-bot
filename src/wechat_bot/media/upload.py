"""CDN media upload with AES-128-ECB encryption."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote

import httpx

from .._logging import logger
from ..errors import MediaError
from ..models import GetUploadUrlRequest
from ..types import UploadMediaType
from .crypto import aes_ecb_padded_size, encrypt_aes_ecb

if TYPE_CHECKING:
    from ..client import WeChatClient

__all__ = ["upload_media", "UploadedMedia"]

_UPLOAD_MAX_RETRIES = 3


@dataclass
class UploadedMedia:
    """Information about a successfully uploaded media file."""

    filekey: str
    download_encrypted_query_param: str
    aeskey_hex: str
    file_size: int
    file_size_ciphertext: int


def _build_cdn_upload_url(cdn_base_url: str, upload_param: str, filekey: str) -> str:
    base = cdn_base_url.rstrip("/")
    return (
        f"{base}/upload"
        f"?encrypted_query_param={quote(upload_param, safe='')}"
        f"&filekey={quote(filekey, safe='')}"
    )


async def _upload_buffer_to_cdn(
    ciphertext: bytes,
    *,
    upload_full_url: str | None,
    upload_param: str | None,
    filekey: str,
    cdn_base_url: str,
) -> str:
    """POST ciphertext to CDN. Returns the download encrypted_query_param."""
    if upload_full_url:
        cdn_url = upload_full_url
    elif upload_param:
        cdn_url = _build_cdn_upload_url(cdn_base_url, upload_param, filekey)
    else:
        raise MediaError("CDN upload URL missing (need upload_full_url or upload_param)")

    download_param: str | None = None
    last_error: Exception | None = None

    async with httpx.AsyncClient() as http:
        for attempt in range(1, _UPLOAD_MAX_RETRIES + 1):
            try:
                resp = await http.post(
                    cdn_url,
                    content=ciphertext,
                    headers={"Content-Type": "application/octet-stream"},
                    timeout=30.0,
                )
                if 400 <= resp.status_code < 500:
                    err_msg = resp.headers.get("x-error-message", resp.text)
                    raise MediaError(f"CDN upload client error {resp.status_code}: {err_msg}")
                if resp.status_code != 200:
                    err_msg = resp.headers.get("x-error-message", f"status {resp.status_code}")
                    raise MediaError(f"CDN upload server error: {err_msg}")

                download_param = resp.headers.get("x-encrypted-param")
                if not download_param:
                    raise MediaError("CDN response missing x-encrypted-param header")

                logger.debug("CDN upload success attempt=%d", attempt)
                break
            except MediaError:
                raise
            except Exception as exc:
                last_error = exc  # type: ignore[assignment]
                logger.warning("CDN upload attempt %d failed: %s", attempt, exc)

    if download_param is None:
        raise last_error or MediaError("CDN upload failed")
    return download_param


async def upload_media(
    client: WeChatClient,
    *,
    file_path: str,
    to_user_id: str,
    media_type: UploadMediaType,
    cdn_base_url: str,
) -> UploadedMedia:
    """Read a local file, encrypt, upload to CDN, and return upload metadata.

    Args:
        client: The :class:`WeChatClient` used for ``getuploadurl``.
        file_path: Path to the local file.
        to_user_id: Recipient user ID.
        media_type: Type of media being uploaded.
        cdn_base_url: CDN base URL.
    """
    with open(file_path, "rb") as f:
        plaintext = f.read()

    rawsize = len(plaintext)
    rawfilemd5 = hashlib.md5(plaintext).hexdigest()
    filesize = aes_ecb_padded_size(rawsize)
    filekey = os.urandom(16).hex()
    aeskey = os.urandom(16)

    req = GetUploadUrlRequest(
        filekey=filekey,
        media_type=int(media_type),
        to_user_id=to_user_id,
        rawsize=rawsize,
        rawfilemd5=rawfilemd5,
        filesize=filesize,
        no_need_thumb=True,
        aeskey=aeskey.hex(),
    )
    resp = await client.get_upload_url(req)

    upload_full_url = (resp.upload_full_url or "").strip() or None
    upload_param = resp.upload_param

    ciphertext = encrypt_aes_ecb(plaintext, aeskey)

    download_param = await _upload_buffer_to_cdn(
        ciphertext,
        upload_full_url=upload_full_url,
        upload_param=upload_param,
        filekey=filekey,
        cdn_base_url=cdn_base_url,
    )

    return UploadedMedia(
        filekey=filekey,
        download_encrypted_query_param=download_param,
        aeskey_hex=aeskey.hex(),
        file_size=rawsize,
        file_size_ciphertext=filesize,
    )
