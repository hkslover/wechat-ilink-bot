"""Tests for CDN media download URL handling."""

from wechat_bot.media.download import _build_cdn_download_url


def test_build_cdn_download_url_percent_encodes_param():
    url = _build_cdn_download_url("a/b&c=d", "https://novac2c.cdn.weixin.qq.com/c2c")
    assert "encrypted_query_param=a%2Fb%26c%3Dd" in url
