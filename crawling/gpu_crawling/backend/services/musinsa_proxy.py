"""
Musinsa Proxy Helper
Rewrites Musinsa URLs to an internal reverse proxy and injects auth headers.
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Union
from urllib.parse import urlparse


def _proxy_base() -> str:
    return os.getenv("MUSINSA_PROXY_BASE_URL", "").rstrip("/")


def is_proxy_enabled() -> bool:
    return bool(_proxy_base())


def proxy_headers() -> Dict[str, str]:
    key = os.getenv("MUSINSA_PROXY_KEY", "")
    if key:
        return {"X-Proxy-Key": key}
    return {}


def httpx_proxies() -> Optional[Union[str, Dict[str, str]]]:
    """
    Return proxies config for httpx.
    - MUSINSA_SOCKS_PROXY=socks5://127.0.0.1:1080 (requires socksio)
    - MUSINSA_HTTP_PROXY / MUSINSA_HTTPS_PROXY for explicit http/https proxies
    """
    socks = os.getenv("MUSINSA_SOCKS_PROXY", "").strip()
    if socks:
        return socks

    http_proxy = os.getenv("MUSINSA_HTTP_PROXY", "").strip()
    https_proxy = os.getenv("MUSINSA_HTTPS_PROXY", "").strip()
    if http_proxy or https_proxy:
        proxies: Dict[str, str] = {}
        if http_proxy:
            proxies["http://"] = http_proxy
        if https_proxy:
            proxies["https://"] = https_proxy
        return proxies
    return None


def proxify_url(url: str) -> str:
    """
    Rewrite Musinsa URLs to go through an internal reverse proxy.
    Expected proxy routes:
      /api2/        -> https://api.musinsa.com/api2/
      /products/    -> https://www.musinsa.com/products/
      /app/goods/   -> https://www.musinsa.com/app/goods/
      /categories/  -> https://www.musinsa.com/categories/
      /goods-detail/-> https://goods-detail.musinsa.com/
      /images/      -> https://image.msscdn.net/images/
      /onelink/     -> https://musinsa.onelink.me/
      /app-link/    -> https://musinsa.app.link/
    """
    base = _proxy_base()
    if not base:
        return url

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lstrip("/")
    query = f"?{parsed.query}" if parsed.query else ""

    if host == "api.musinsa.com":
        return f"{base}/{path}{query}"

    if host in ("www.musinsa.com", "musinsa.com"):
        if path.startswith("api2/"):
            return f"{base}/{path}{query}"
        if path.startswith(("products/", "app/goods/", "categories/")):
            return f"{base}/{path}{query}"

    if host == "goods-detail.musinsa.com":
        return f"{base}/goods-detail/{path}{query}"

    if host == "image.msscdn.net":
        return f"{base}/{path}{query}"

    if host == "musinsa.onelink.me":
        return f"{base}/onelink/{path}{query}"

    if host == "musinsa.app.link":
        return f"{base}/app-link/{path}{query}"

    return url
