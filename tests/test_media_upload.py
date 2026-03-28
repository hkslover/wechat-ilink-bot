"""Tests for outbound media upload helpers."""

import base64

from wechat_bot.context import _build_media_item
from wechat_bot.media.upload import UploadedMedia, _build_cdn_upload_url
from wechat_bot.types import MessageItemType, UploadMediaType


def test_build_cdn_upload_url_percent_encodes_query_parts():
    url = _build_cdn_upload_url("https://cdn.example/c2c", "a/b&c=d", "k/x")
    assert "encrypted_query_param=a%2Fb%26c%3Dd" in url
    assert "filekey=k%2Fx" in url


def test_build_media_item_uses_hex_string_base64_for_aes_key():
    uploaded = UploadedMedia(
        filekey="f" * 32,
        download_encrypted_query_param="enc_param",
        aeskey_hex="00112233445566778899aabbccddeeff",
        file_size=123,
        file_size_ciphertext=128,
    )

    item = _build_media_item(uploaded, UploadMediaType.IMAGE, "/tmp/a.jpg")
    assert item.type == MessageItemType.IMAGE
    assert item.image_item is not None
    assert item.image_item.media is not None
    assert item.image_item.media.aes_key == base64.b64encode(
        uploaded.aeskey_hex.encode("ascii")
    ).decode()

