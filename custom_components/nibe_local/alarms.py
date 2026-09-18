"""Alarm helpers for NIBE Local REST."""
from __future__ import annotations

from hashlib import sha1
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

    api_description = alarm.get("description")
    normalized: dict[str, Any] = {
        "alarm_id": number,
        "text": api_header
        or api_description
        or verified_german_text
        or fallback_text,
        "description": api_description,
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


def alarm_notification_id(instance_id: str, alarm: dict[str, Any]) -> str:
    """Return a stable Home Assistant persistent-notification ID for one alarm."""
    number = alarm.get("alarm_id")
    if number is not None:
        suffix = str(number)
    else:
        fingerprint = "|".join(
            str(alarm.get(key) or "")
            for key in ("text", "description", "time", "equipment")
        )
        suffix = sha1(fingerprint.encode("utf-8")).hexdigest()[:12]
    return f"nibe_local_{instance_id}_alarm_{suffix}"


def alarm_notification_title(
    alarm: dict[str, Any],
    *,
    device_name: str,
) -> str:
    """Return a concise title for a Home Assistant alarm notification."""
    number = alarm.get("alarm_id")
    text = str(alarm.get("text") or "").strip()
    prefix = f"NIBE Alarm {number}" if number is not None else "NIBE Alarm"
    if text and text not in {prefix, f"Alarm {number}" if number is not None else "Alarm"}:
        return f"{prefix} - {text}"
    return f"{device_name} - {prefix}"


def alarm_severity_label(value: Any, *, german: bool) -> str | None:
    """Return a readable severity label without guessing undocumented numeric meanings."""
    if value in (None, ""):
        return None

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None

        labels = (
            {
                "info": "Information",
                "information": "Information",
                "notice": "Hinweis",
                "warning": "Warnung",
                "warn": "Warnung",
                "error": "Fehler",
                "fault": "Fehler",
                "alarm": "Alarm",
                "critical": "Kritisch",
                "crit": "Kritisch",
            }
            if german
            else {
                "info": "Information",
                "information": "Information",
                "notice": "Notice",
                "warning": "Warning",
                "warn": "Warning",
                "error": "Error",
                "fault": "Fault",
                "alarm": "Alarm",
                "critical": "Critical",
                "crit": "Critical",
            }
        )
        mapped = labels.get(stripped.casefold())
        if mapped is not None:
            return mapped

        try:
            numeric = int(stripped)
        except ValueError:
            return stripped
        value = numeric

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = int(value) if isinstance(value, float) and value.is_integer() else value
        return (
            f"NIBE-Stufe {numeric}"
            if german
            else f"NIBE level {numeric}"
        )

    return str(value)


def alarm_notification_message(
    alarm: dict[str, Any],
    *,
    german: bool,
) -> str:
    """Build a readable persistent-notification message from REST alarm fields."""
    labels = (
        {
            "alarm": "Alarm",
            "description": "Beschreibung",
            "severity": "Schweregrad",
            "equipment": "Gerät / Quelle",
            "time": "Zeit",
            "action": "Aktion",
            "reset_hint": (
                "Falls die Taste **„Alarme zurücksetzen“** verfügbar ist, können "
                "darüber zurücksetzbare Alarme quittiert werden."
            ),
        }
        if german
        else {
            "alarm": "Alarm",
            "description": "Description",
            "severity": "Severity",
            "equipment": "Device / source",
            "time": "Time",
            "action": "Action",
            "reset_hint": (
                "If the **“Reset alarms”** button is available, resettable alarms "
                "can be acknowledged with it."
            ),
        }
    )

    lines: list[str] = []
    number = alarm.get("alarm_id")
    text = str(alarm.get("text") or "").strip()
    description = str(alarm.get("description") or "").strip()

    if number is not None:
        lines.append(f"**{labels['alarm']} {number}**")

    fallback_text = f"Alarm {number}" if number is not None else "Alarm"
    if text and text != fallback_text:
        lines.append(f"**{text}**")
    elif text and number is None:
        lines.append(f"**{text}**")

    if description and description != text:
        lines.append(f"**{labels['description']}:** {description}")

    severity = alarm_severity_label(alarm.get("severity"), german=german)
    if severity is not None:
        lines.append(f"**{labels['severity']}:** {severity}")

    for key in ("equipment", "time"):
        value = alarm.get(key)
        if value not in (None, ""):
            lines.append(f"**{labels[key]}:** {value}")

    lines.append(f"**{labels['action']}:** {labels['reset_hint']}")

    return "\n\n".join(lines) if lines else ("NIBE Alarm" if not german else "NIBE-Alarm")
