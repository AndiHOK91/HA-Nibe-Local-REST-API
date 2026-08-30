"""Read-only alarm helpers for NIBE Local REST."""
from __future__ import annotations

from typing import Any

# Alarm texts verified against NIBE N firmware 4.12.8.
# Keep this table keyed by the actual NIBE alarm number, not by translation ID.
ALARM_TEXTS_DE: dict[int, str] = {
    224: "Kom.fehler mit Zubehör Brauchwasserkomfort",
}


def alarm_number(alarm: dict[str, Any]) -> int | None:
    """Return the actual NIBE alarm number from known API field names."""
    for key in ("alarmId", "alarmNo", "alarmNumber", "number"):
        value = alarm.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def normalize_alarm(alarm: dict[str, Any]) -> dict[str, Any]:
    """Normalize an alarm without exposing any write/reset operation."""
    number = alarm_number(alarm)
    api_header = alarm.get("header") or alarm.get("name") or alarm.get("title")
    mapped_header = ALARM_TEXTS_DE.get(number) if number is not None else None

    normalized: dict[str, Any] = {
        "alarm_id": number,
        "text": mapped_header or api_header or "Unbekannter Alarm",
        "description": alarm.get("description"),
        "severity": alarm.get("severity", alarm.get("class")),
        "time": alarm.get("time"),
        "equipment": alarm.get("equipName", alarm.get("source")),
    }

    # Preserve the device-provided header when it differs from our verified
    # firmware mapping. This makes firmware/language differences visible while
    # still providing a stable German text for known alarm numbers.
    if api_header and api_header != normalized["text"]:
        normalized["device_text"] = api_header

    return normalized


def normalize_alarms(payload: Any) -> list[dict[str, Any]]:
    """Return a normalized list for the notification payload shapes seen so far."""
    alarms: Any = payload
    if isinstance(payload, dict):
        alarms = payload.get("alarms", [])

    if not isinstance(alarms, list):
        return []

    return [normalize_alarm(item) for item in alarms if isinstance(item, dict)]
