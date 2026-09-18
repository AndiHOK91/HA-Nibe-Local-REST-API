"""Temporary signed JSON downloads for extended diagnostics."""
from __future__ import annotations

from datetime import timedelta
import json
import secrets
import time
from typing import Any

from aiohttp import web

from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util, slugify

from .const import DOMAIN

DOWNLOAD_TTL_SECONDS = 600
DATA_DIAGNOSTICS_DOWNLOADS = f"{DOMAIN}_diagnostics_downloads"
DOWNLOAD_URL = "/api/nibe_local/extended_diagnostics/{token}"


def _store(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Return the in-memory diagnostics download store."""
    return hass.data.setdefault(DATA_DIAGNOSTICS_DOWNLOADS, {})


def _cleanup_expired(store: dict[str, dict[str, Any]]) -> None:
    """Remove expired download payloads."""
    now = time.monotonic()
    for token in [
        token
        for token, item in store.items()
        if float(item.get("expires_at", 0)) <= now
    ]:
        store.pop(token, None)


def _serialize_diagnostics(payload: dict[str, Any]) -> bytes:
    """Serialize diagnostics to stable UTF-8 JSON bytes."""
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n"
    ).encode("utf-8")


def _download_filename(entry: ConfigEntry) -> str:
    """Build a safe diagnostics filename."""
    label = slugify(entry.title or "nibe") or "nibe"
    stamp = dt_util.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"nibe_extended_diagnostics_{label}_{stamp}.json"


def create_extended_diagnostics_download(
    hass: HomeAssistant,
    entry: ConfigEntry,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Store diagnostics temporarily and return a signed download path."""
    store = _store(hass)
    _cleanup_expired(store)

    token = secrets.token_urlsafe(24)
    filename = _download_filename(entry)
    store[token] = {
        "content": _serialize_diagnostics(payload),
        "filename": filename,
        "expires_at": time.monotonic() + DOWNLOAD_TTL_SECONDS,
    }

    path = DOWNLOAD_URL.format(token=token)
    return {
        "filename": filename,
        "url": async_sign_path(
            hass,
            path,
            timedelta(seconds=DOWNLOAD_TTL_SECONDS),
        ),
        "expires_in_seconds": DOWNLOAD_TTL_SECONDS,
    }


class ExtendedDiagnosticsDownloadView(HomeAssistantView):
    """Serve one temporary extended diagnostics JSON file."""

    url = DOWNLOAD_URL
    name = "api:nibe_local:extended_diagnostics_download"
    requires_auth = True

    async def get(self, request: web.Request, token: str) -> web.Response:
        """Download one generated diagnostics JSON payload."""
        hass: HomeAssistant = request.app[KEY_HASS]
        store = _store(hass)
        _cleanup_expired(store)

        item = store.get(token)
        if item is None:
            raise web.HTTPNotFound(text="Diagnostics download not found or expired")

        return web.Response(
            body=item["content"],
            content_type="application/json",
            charset="utf-8",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": (
                    f'attachment; filename="{item["filename"]}"'
                ),
            },
        )
