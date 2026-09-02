"""Async client for the NIBE local REST API."""
from __future__ import annotations

import asyncio
import socket
import ssl
from typing import Any

from aiohttp import BasicAuth, ClientResponseError, ClientSession, ClientTimeout

from .const import AUTH_METHOD_BASIC, AUTH_METHOD_HEADER, NIBE_DEVICE_ID


async def async_resolve_host_ip(host: str) -> str | None:
    """Resolve a configured host to an IP address without blocking Home Assistant."""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            host,
            None,
            type=socket.SOCK_STREAM,
        )
    except OSError:
        return None

    for _family, _socktype, _proto, _canonname, sockaddr in infos:
        if sockaddr:
            return str(sockaddr[0])
    return None


class NibeApiError(Exception):
    """Base API error."""


class NibeAuthError(NibeApiError):
    """Authentication error."""


class NibeLocalApi:
    def __init__(
        self,
        session: ClientSession,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        auth_header: str | None = None,
        auth_method: str | None = None,
        verify_ssl: bool = False,
    ) -> None:
        self._session = session
        self.host = host.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        self.port = port
        self.device_id = NIBE_DEVICE_ID
        if auth_method == AUTH_METHOD_BASIC:
            self._auth = BasicAuth(username, password or "") if username else None
            self._auth_header = None
        elif auth_method == AUTH_METHOD_HEADER:
            self._auth = None
            self._auth_header = auth_header.strip() if auth_header else None
        else:
            # Compatibility for config entries created before auth_method existed:
            # a stored header keeps its historical precedence over Basic Auth.
            self._auth = BasicAuth(username, password or "") if username else None
            self._auth_header = auth_header.strip() if auth_header else None
        self._ssl: bool | ssl.SSLContext = True if verify_ssl else False
        self._timeout = ClientTimeout(total=15)
        self._write_lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        return f"https://{self.host}:{self.port}/api/v1"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._auth_header:
            headers["Authorization"] = self._auth_header
        return headers

    async def _request(self, method: str, path: str, *, json: Any | None = None) -> Any:
        try:
            async with self._session.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(),
                auth=None if self._auth_header else self._auth,
                ssl=self._ssl,
                timeout=self._timeout,
                json=json,
            ) as response:
                if response.status == 401:
                    raise NibeAuthError("NIBE API rejected the credentials")
                response.raise_for_status()
                if response.status == 204:
                    return None
                return await response.json(content_type=None)
        except NibeAuthError:
            raise
        except ClientResponseError as err:
            raise NibeApiError(f"HTTP {err.status}: {err.message}") from err
        except Exception as err:
            raise NibeApiError(str(err)) from err

    async def _write_request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
    ) -> Any:
        """Serialize writes so the NIBE API never receives concurrent commands."""
        async with self._write_lock:
            return await self._request(method, path, json=json)

    async def get_device(self) -> dict[str, Any]:
        return await self._request("GET", f"/devices/{self.device_id}")

    async def get_points(self) -> dict[str, Any]:
        payload = await self._request("GET", f"/devices/{self.device_id}/points")
        return self._normalize_points(payload)

    async def get_point(self, variable_id: int) -> dict[str, Any]:
        """Fetch one point only.

        This is intentionally used for latency-sensitive controls so Home
        Assistant does not need to wait for a complete /points + device +
        notifications coordinator refresh.
        """
        return await self._request(
            "GET", f"/devices/{self.device_id}/points/{variable_id}"
        )

    @staticmethod
    def _normalize_points(payload: Any) -> dict[str, Any]:
        """Normalize NIBE point responses from different firmware/API shapes."""
        result: dict[str, Any] = {}

        def visit(node: Any) -> None:
            if isinstance(node, list):
                for item in node:
                    visit(item)
                return

            if not isinstance(node, dict):
                return

            metadata = node.get("metadata")
            if isinstance(metadata, dict) and metadata.get("variableId") is not None:
                point_id = str(metadata["variableId"])
                result[point_id] = node
                return

            for wrapper in ("points", "data", "items", "values"):
                wrapped = node.get(wrapper)
                if isinstance(wrapped, (dict, list)):
                    visit(wrapped)

            for key, value in node.items():
                if isinstance(value, dict):
                    md = value.get("metadata")
                    if isinstance(md, dict) and md.get("variableId") is not None:
                        result[str(md["variableId"])] = value
                    elif str(key).isdigit() and (
                        "value" in value or "datavalue" in value or "metadata" in value
                    ):
                        result[str(key)] = value

        visit(payload)
        return result

    async def get_notifications(self) -> dict[str, Any]:
        return await self._request("GET", f"/devices/{self.device_id}/notifications")

    async def patch_point(self, variable_id: int, raw_value: int | str) -> Any:
        value: dict[str, Any] = {
            "type": "datavalue",
            "isOk": True,
            "variableId": variable_id,
        }
        if isinstance(raw_value, str):
            value["stringValue"] = raw_value
            value["integerValue"] = 0
        else:
            value["integerValue"] = int(raw_value)
            value["stringValue"] = ""
        return await self._write_request(
            "PATCH", f"/devices/{self.device_id}/points", json=[value]
        )

    async def set_smart_mode(self, mode: str) -> Any:
        return await self._write_request(
            "POST", f"/devices/{self.device_id}/smartmode", json={"smartMode": mode}
        )
