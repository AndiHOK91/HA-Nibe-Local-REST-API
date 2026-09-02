"""Read-only alarm helpers for NIBE Local REST."""
from __future__ import annotations

from typing import Any

# German fallback texts verified against NIBE N firmware 4.12.8.
# Prefer device-provided text so the NIBE device language is preserved.
VERIFIED_ALARM_TEXTS_DE: dict[int, str] = {
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


def normalize_alarm(
    alarm: dict[str, Any], language: str | None = None
) -> dict[str, Any]:
    """Normalize an alarm without exposing any write/reset operation."""
    number = alarm_number(alarm)
    api_header = alarm.get("header") or alarm.get("name") or alarm.get("title")
    verified_german_text = (
        VERIFIED_ALARM_TEXTS_DE.get(number)
        if number is not None and (language or "").lower().startswith("de")
        else None
    )
    fallback_text = f"Alarm {number}" if number is not None else "Alarm"

    normalized: dict[str, Any] = {
        "alarm_id": number,
        "text": api_header or verified_german_text or fallback_text,
        "description": alarm.get("description"),
        "severity": alarm.get("severity", alarm.get("class")),
        "time": alarm.get("time"),
        "equipment": alarm.get("equipName", alarm.get("source")),
    }

    return normalized


def normalize_alarms(
    payload: Any, language: str | None = None
) -> list[dict[str, Any]]:
    """Return a normalized list for the notification payload shapes seen so far."""
    alarms: Any = payload
    if isinstance(payload, dict):
        alarms = payload.get("alarms", [])

    if not isinstance(alarms, list):
        return []

    return [
        normalize_alarm(item, language)
        for item in alarms
        if isinstance(item, dict)
    ]
