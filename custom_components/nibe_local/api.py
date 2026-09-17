"""Async client for the NIBE local REST API."""
from __future__ import annotations

import asyncio
from base64 import b64encode
from dataclasses import dataclass
from json import JSONDecodeError, loads
import logging
import socket
import ssl
from typing import Any

from aiohttp import ClientResponseError, ClientSession, ClientTimeout

from .const import AUTH_METHOD_BASIC, AUTH_METHOD_HEADER, NIBE_DEVICE_ID

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_NORMALIZE_DEPTH = 64
NIBE_LANGUAGE_POINT_ID = 3745
NIBE_LANGUAGE_CODES: dict[int, str] = {
    0: "en",
    1: "sv",
    2: "de",
    3: "fr",
    4: "es",
    5: "fi",
    6: "lt",
    7: "cs",
    8: "pl",
    9: "nl",
    10: "no",
    11: "da",
    12: "et",
    13: "lv",
    14: "ru",
    15: "it",
    16: "hu",
    17: "sl",
    18: "tr",
    19: "hr",
    20: "ro",
    21: "is",
    22: "sk",
    23: "uk",
    24: "bg",
}

# Confirmed NIBE firmware metadata defects. Keep these corrections close to the
# API boundary so every consumer sees the corrected metadata consistently.
FIRMWARE_METADATA_OVERRIDES: dict[int, dict[str, Any]] = {
    # Production (PV Power): firmware reports kW/divisor 1 although one raw
    # step equals 10 W, so kW scaling requires divisor 100.
    29258: {"divisor": 100},
    # Older firmware reported these power values as kWh. Current firmware has
    # corrected them, but forcing kW keeps older installations safe as well.
    25165: {"unit": "kW", "shortUnit": "kW"},
    25166: {"unit": "kW", "shortUnit": "kW"},
}

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _BasicCredentials:
    """Minimal Basic-Auth credential container without aiohttp.BasicAuth."""

    login: str
    password: str


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
            self._auth = _BasicCredentials(username, password or "") if username else None
            self._auth_header = None
        elif auth_method == AUTH_METHOD_HEADER:
            self._auth = None
            self._auth_header = auth_header.strip() if auth_header else None
        else:
            # Compatibility for config entries created before auth_method existed:
            # a stored header keeps its historical precedence over Basic Auth.
            self._auth = _BasicCredentials(username, password or "") if username else None
            self._auth_header = auth_header.strip() if auth_header else None
        self._ssl: bool | ssl.SSLContext = True if verify_ssl else False
        self._timeout = ClientTimeout(total=15)
        self._write_lock = asyncio.Lock()
        self._language: str | None = None
        self._language_checked = False

    @property
    def base_url(self) -> str:
        return f"https://{self.host}:{self.port}/api/v1"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._language:
            headers["Accept-Language"] = self._language
        if self._auth_header:
            headers["Authorization"] = self._auth_header
        elif self._auth:
            token = b64encode(
                f"{self._auth.login}:{self._auth.password}".encode("utf-8")
            ).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
        return headers

    async def _request(self, method: str, path: str, *, json: Any | None = None) -> Any:
        try:
            async with self._session.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(),
                auth=None,
                ssl=self._ssl,
                timeout=self._timeout,
                json=json,
            ) as response:
                if response.status == 401:
                    raise NibeAuthError("NIBE API rejected the credentials")
                response.raise_for_status()
                if response.status == 204:
                    return None

                if (
                    response.content_length is not None
                    and response.content_length > MAX_RESPONSE_BYTES
                ):
                    raise NibeApiError(
                        f"NIBE API response exceeds {MAX_RESPONSE_BYTES} bytes"
                    )

                body = bytearray()
                async for chunk in response.content.iter_chunked(64 * 1024):
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise NibeApiError(
                            f"NIBE API response exceeds {MAX_RESPONSE_BYTES} bytes"
                        )
                    body.extend(chunk)

                try:
                    return loads(body)
                except (JSONDecodeError, UnicodeDecodeError) as err:
                    raise NibeApiError("NIBE API returned invalid JSON") from err
        except (NibeAuthError, NibeApiError):
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

    async def _ensure_language(self) -> None:
        """Use the language configured in the NIBE firmware for REST labels."""
        if self._language_checked:
            return
        self._language_checked = True
        try:
            point = await self._request(
                "GET", f"/devices/{self.device_id}/points/{NIBE_LANGUAGE_POINT_ID}"
            )
        except NibeAuthError:
            raise
        except NibeApiError as err:
            _LOGGER.debug("Could not determine NIBE UI language: %s", err)
            return
        self._update_language_from_point(point)

    def _update_language_from_point(self, point: Any) -> None:
        """Update the REST Accept-Language value from NIBE point 3745."""
        raw = self._point_raw_value(point)
        try:
            language_id = int(raw)
        except (TypeError, ValueError):
            return
        language = NIBE_LANGUAGE_CODES.get(language_id)
        if language:
            self._language = language

    @staticmethod
    def _apply_firmware_metadata_override(variable_id: int, point: Any) -> Any:
        """Apply confirmed firmware metadata corrections to one point."""
        if not isinstance(point, dict):
            return point
        override = FIRMWARE_METADATA_OVERRIDES.get(variable_id)
        if not override:
            return point
        metadata = point.get("metadata")
        if not isinstance(metadata, dict):
            return point
        metadata.update(override)
        return point

    @classmethod
    def _apply_firmware_metadata_overrides(cls, points: dict[str, Any]) -> None:
        """Apply confirmed firmware metadata corrections to a bulk response."""
        for variable_id in FIRMWARE_METADATA_OVERRIDES:
            point = points.get(str(variable_id))
            if point is not None:
                cls._apply_firmware_metadata_override(variable_id, point)

    @classmethod
    def _validate_patch_response(cls, variable_id: int, response: Any) -> Any:
        """Reject HTTP-200 PATCH responses when NIBE refused the write."""
        if not isinstance(response, dict):
            raise NibeApiError(
                f"NIBE API returned unexpected PATCH response for point {variable_id}"
            )

        point_response = response.get(str(variable_id))
        if point_response == "modified":
            return response

        # Some firmware returns the full point object instead of the documented
        # string. Treat it as success only when the embedded data value is OK.
        if isinstance(point_response, dict):
            value = point_response.get("value") or point_response.get("datavalue") or {}
            if isinstance(value, dict) and value.get("isOk") is True:
                return response
            raise NibeApiError(
                f"NIBE rejected write for point {variable_id}: point response is not OK"
            )

        if isinstance(point_response, str) and point_response.lower().startswith("error"):
            raise NibeApiError(
                f"NIBE rejected write for point {variable_id}: {point_response}"
            )

        raise NibeApiError(
            f"NIBE API returned unexpected PATCH result for point {variable_id}: "
            f"{point_response!r}"
        )

    async def get_device(self) -> dict[str, Any]:
        return await self._request("GET", f"/devices/{self.device_id}")

    async def get_points(self) -> dict[str, Any]:
        """Fetch and normalize the bulk point endpoint."""
        await self._ensure_language()
        payload = await self._request("GET", f"/devices/{self.device_id}/points")
        points = self._normalize_points(payload)
        self._apply_firmware_metadata_overrides(points)
        language_point = points.get(str(NIBE_LANGUAGE_POINT_ID))
        if language_point:
            self._update_language_from_point(language_point)
        return points

    async def get_point(self, variable_id: int) -> dict[str, Any]:
        """Fetch one point only.

        This is intentionally used for latency-sensitive controls so Home
        Assistant does not need to wait for a complete /points + device +
        notifications coordinator refresh.
        """
        point = await self._request(
            "GET", f"/devices/{self.device_id}/points/{variable_id}"
        )
        return self._apply_firmware_metadata_override(variable_id, point)

    @staticmethod
    def _normalize_points(payload: Any) -> dict[str, Any]:
        """Normalize NIBE point responses with bounded nesting depth."""
        result: dict[str, Any] = {}
        stack: list[tuple[Any, int]] = [(payload, 0)]
        visited: set[int] = set()

        while stack:
            node, depth = stack.pop()
            if depth > MAX_NORMALIZE_DEPTH:
                raise NibeApiError(
                    f"NIBE point response exceeds nesting depth {MAX_NORMALIZE_DEPTH}"
                )

            if not isinstance(node, (dict, list)):
                continue

            node_id = id(node)
            if node_id in visited:
                continue
            visited.add(node_id)

            if isinstance(node, list):
                stack.extend((item, depth + 1) for item in reversed(node))
                continue

            metadata = node.get("metadata")
            if isinstance(metadata, dict) and metadata.get("variableId") is not None:
                result[str(metadata["variableId"])] = node
                continue

            for wrapper in ("points", "data", "items", "values"):
                wrapped = node.get(wrapper)
                if isinstance(wrapped, (dict, list)):
                    stack.append((wrapped, depth + 1))

            for key, value in node.items():
                if not isinstance(value, dict):
                    continue
                md = value.get("metadata")
                if isinstance(md, dict) and md.get("variableId") is not None:
                    result[str(md["variableId"])] = value
                elif str(key).isdigit() and (
                    "value" in value or "datavalue" in value or "metadata" in value
                ):
                    result[str(key)] = value

        return result

    @staticmethod
    def _point_raw_value(point: Any) -> int | str | None:
        """Return the raw value from one point response for write comparison."""
        if not isinstance(point, dict):
            return None
        value = point.get("value") or point.get("datavalue") or {}
        if not isinstance(value, dict):
            return None
        string_value = value.get("stringValue")
        if string_value not in (None, ""):
            return string_value
        return value.get("integerValue")

    async def get_notifications(self) -> dict[str, Any]:
        return await self._request("GET", f"/devices/{self.device_id}/notifications")

    async def patch_point(self, variable_id: int, raw_value: int | str) -> Any:
        """Write one point only when its freshly read raw value differs.

        The pre-write GET and the optional PATCH share the same write lock. This
        prevents duplicate writes when two identical commands arrive at nearly
        the same time. If the pre-write GET fails, preserve the previous command
        behaviour and attempt the requested PATCH instead of silently dropping it.
        """
        normalized_value: int | str
        if isinstance(raw_value, str):
            normalized_value = raw_value
        else:
            normalized_value = int(raw_value)

        value: dict[str, Any] = {
            "type": "datavalue",
            "isOk": True,
            "variableId": variable_id,
        }
        if isinstance(normalized_value, str):
            value["stringValue"] = normalized_value
            value["integerValue"] = 0
        else:
            value["integerValue"] = normalized_value
            value["stringValue"] = ""

        async with self._write_lock:
            try:
                current_point = await self.get_point(variable_id)
            except NibeApiError as err:
                _LOGGER.debug(
                    "Pre-write read of NIBE point %s failed; proceeding with PATCH: %s",
                    variable_id,
                    err,
                )
            else:
                if self._point_raw_value(current_point) == normalized_value:
                    _LOGGER.debug(
                        "Skipping redundant PATCH for NIBE point %s; raw value is already %r",
                        variable_id,
                        normalized_value,
                    )
                    return None

            response = await self._request(
                "PATCH", f"/devices/{self.device_id}/points", json=[value]
            )
            return self._validate_patch_response(variable_id, response)

    async def set_smart_mode(self, mode: str) -> Any:
        return await self._write_request(
            "POST", f"/devices/{self.device_id}/smartmode", json={"smartMode": mode}
        )
