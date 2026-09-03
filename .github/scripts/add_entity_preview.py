from __future__ import annotations

import inspect
import json
import re
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# --- config_flow.py -------------------------------------------------------
path = Path("custom_components/nibe_local/config_flow.py")
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    "    NIBE_DEVICE_ID,\n    POINTS,\n)",
    "    NIBE_DEVICE_ID,\n    POINTS,\n    POINT_VENTILATION_MODE,\n)",
    "POINT_VENTILATION_MODE import",
)

text = replace_once(
    text,
    'CONF_BACKUP_BEFORE_CLEANUP = "backup_before_cleanup"\n',
    'CONF_BACKUP_BEFORE_CLEANUP = "backup_before_cleanup"\nPREVIEW_LIST_LIMIT = 50\n',
    "preview limit",
)

entity_schema_end = '''def _entity_selection_schema(
    points: dict[str, Any],
    selected_ids=None,
    *,
    point_names: dict[int, str] | None = None,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_SELECTED_POINT_IDS,
                default=_selected_options(points, selected_ids),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=_point_options(points, point_names),
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            )
        }
    )
'''

preview_helpers = entity_schema_end + '''

def _registered_point_ids(hass, entry: ConfigEntry | None) -> frozenset[int]:
    """Return numeric point IDs currently present in this entry's registry."""
    if entry is None:
        return frozenset()
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    result: set[int] = set()
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        unique_id = registry_entry.unique_id
        if not unique_id.startswith(prefix):
            continue
        suffix = unique_id[len(prefix):]
        if suffix.isdigit():
            result.add(int(suffix))
    return frozenset(result)


def _preview_point_groups(
    points: dict[str, Any],
    profile: str,
    selected_ids,
    *,
    registered_ids=(),
    cleanup: bool = False,
) -> dict[str, frozenset[int]]:
    """Split discovered/registered points into the final preview groups."""
    available = normalize_selected_ids(points.keys())
    registered = normalize_selected_ids(registered_ids)
    active = frozenset(
        point_id
        for point_id in available
        if point_enabled(profile, point_id, selected_ids)
    )
    disabled_registered = frozenset(
        point_id
        for point_id in registered
        if not point_enabled(profile, point_id, selected_ids)
    )
    delete = disabled_registered if cleanup else frozenset()
    inactive = frozenset((available - active) | (disabled_registered - delete))
    return {
        "active": active,
        "active_existing": frozenset(active & registered),
        "active_new": frozenset(active - registered),
        "inactive": inactive,
        "delete": delete,
    }


def _format_preview_ids(
    point_ids,
    points: dict[str, Any],
    point_names: dict[int, str],
    *,
    german: bool,
) -> str:
    """Format a bounded, human-readable point list for a config-flow preview."""
    ordered = sorted(normalize_selected_ids(point_ids))
    if not ordered:
        return "– Keine" if german else "– None"
    visible = ordered[:PREVIEW_LIST_LIMIT]
    lines = [
        f"- {_point_label(str(point_id), points.get(str(point_id), {}), point_names)}"
        for point_id in visible
    ]
    remaining = len(ordered) - len(visible)
    if remaining:
        lines.append(
            f"- … + {remaining} weitere" if german else f"- … + {remaining} more"
        )
    return "\\n".join(lines)


def _preview_special_entities(
    points: dict[str, Any], profile: str, selected_ids, device: dict[str, Any] | None,
    *, german: bool,
) -> list[str]:
    """Return non-point helper entities that the integration will provide."""
    if german:
        result = [
            "REST API erreichbar",
            "Einzelpunkt-Fallback aktiv",
            "Meldungen / Alarme",
            "Letzter Verbindungsfehler",
        ]
    else:
        result = [
            "REST API reachable",
            "Individual-point fallback active",
            "Notifications / alarms",
            "Last connection error",
        ]

    if isinstance(device, dict) and "smartMode" in device:
        result.append("Smart Mode")

    ventilation = points.get(str(POINT_VENTILATION_MODE)) or {}
    ventilation_metadata = ventilation.get("metadata") or {}
    if (
        ventilation
        and point_enabled(profile, POINT_VENTILATION_MODE, selected_ids)
        and bool(ventilation_metadata.get("isWritable"))
    ):
        result.append("Lüftung+" if german else "Ventilation+")
    return result


def _profile_preview_label(profile: str, *, german: bool) -> str:
    labels_de = {
        "minimal": "Minimal",
        "standard": "Standard",
        "extended": "Erweitert",
        "complete": "Komplett",
        "individual": "Individuell",
    }
    labels_en = {
        "minimal": "Minimal",
        "standard": "Standard",
        "extended": "Extended",
        "complete": "Complete",
        "individual": "Individual",
    }
    return (labels_de if german else labels_en).get(profile, profile)


async def _async_entity_preview_placeholders(
    hass,
    *,
    points: dict[str, Any],
    profile: str,
    selected_ids,
    device: dict[str, Any] | None,
    entry: ConfigEntry | None = None,
    cleanup: bool = False,
    backup: bool = False,
) -> dict[str, str]:
    """Build localized placeholders for the final entity overview."""
    german = str(getattr(hass.config, "language", "")).lower().startswith("de")
    point_names = await _async_translated_point_names(hass)
    registered = _registered_point_ids(hass, entry)
    groups = _preview_point_groups(
        points,
        profile,
        selected_ids,
        registered_ids=registered,
        cleanup=cleanup,
    )
    special = _preview_special_entities(
        points, profile, selected_ids, device, german=german
    )
    yes = "Ja" if german else "Yes"
    no = "Nein" if german else "No"
    backup_value = yes if cleanup and backup else (no if cleanup else "–")
    return {
        "profile": _profile_preview_label(profile, german=german),
        "discovered": str(len(normalize_selected_ids(points.keys()))),
        "active_count": str(len(groups["active"])),
        "active_existing": str(len(groups["active_existing"])),
        "active_new": str(len(groups["active_new"])),
        "inactive_count": str(len(groups["inactive"])),
        "delete_count": str(len(groups["delete"])),
        "special_count": str(len(special)),
        "active_list": _format_preview_ids(
            groups["active"], points, point_names, german=german
        ),
        "inactive_list": _format_preview_ids(
            groups["inactive"], points, point_names, german=german
        ),
        "delete_list": _format_preview_ids(
            groups["delete"], points, point_names, german=german
        ),
        "special_list": "\\n".join(f"- {name}" for name in special),
        "cleanup": yes if cleanup else no,
        "backup": backup_value,
    }
'''
text = replace_once(text, entity_schema_end, preview_helpers, "preview helpers")

text = replace_once(
    text,
    '''            if profile == PROFILE_INDIVIDUAL:
                return await self.async_step_entity_selection()
            return self._create_pending_entry()
''',
    '''            if profile == PROFILE_INDIVIDUAL:
                return await self.async_step_entity_selection()
            return await self.async_step_entity_preview()
''',
    "setup profile preview routing",
)

text = replace_once(
    text,
    '''        if user_input is not None:
            self._pending_data[CONF_SELECTED_POINT_IDS] = _parse_selected_options(
                user_input.get(CONF_SELECTED_POINT_IDS)
            )
            return self._create_pending_entry()

        return self.async_show_form(
            step_id="entity_selection",
            data_schema=_entity_selection_schema(points, point_names=point_names),
            description_placeholders={"count": str(len(points))},
        )

    async def async_step_reauth(self, entry_data: dict):
''',
    '''        if user_input is not None:
            self._pending_data[CONF_SELECTED_POINT_IDS] = _parse_selected_options(
                user_input.get(CONF_SELECTED_POINT_IDS)
            )
            return await self.async_step_entity_preview()

        return self.async_show_form(
            step_id="entity_selection",
            data_schema=_entity_selection_schema(points, point_names=point_names),
            description_placeholders={"count": str(len(points))},
        )

    async def async_step_entity_preview(self, user_input=None):
        if self._pending_data is None or self._pending_device is None:
            return self.async_abort(reason="setup_state_missing")
        if user_input is not None:
            return self._create_pending_entry()

        profile = str(
            self._pending_data.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE)
        )
        points = self._available_points or {}
        placeholders = await _async_entity_preview_placeholders(
            self.hass,
            points=points,
            profile=profile,
            selected_ids=self._pending_data.get(CONF_SELECTED_POINT_IDS, ()),
            device=self._pending_device,
        )
        return self.async_show_form(
            step_id="entity_preview",
            data_schema=vol.Schema({}),
            description_placeholders=placeholders,
        )

    async def async_step_reauth(self, entry_data: dict):
''',
    "setup preview step",
)

text = replace_once(
    text,
    '''    _pending_options: dict | None = None
    _available_points: dict[str, Any] | None = None
    _cleanup_inactive = False
''',
    '''    _pending_options: dict | None = None
    _available_points: dict[str, Any] | None = None
    _pending_device: dict[str, Any] | None = None
    _cleanup_inactive = False
''',
    "options pending device",
)

text = replace_once(
    text,
    '''            _device, points = await _validate_and_discover(self.hass, candidate)
''',
    '''            device, points = await _validate_and_discover(self.hass, candidate)
''',
    "options device capture",
)

text = replace_once(
    text,
    '''            self._pending_options = candidate
            self._available_points = points
            if profile == PROFILE_INDIVIDUAL:
                return await self.async_step_entity_selection()
            if self._cleanup_inactive:
                if self._backup_before_cleanup:
                    try:
                        await _async_create_cleanup_backup(self.hass)
                    except Exception as err:
                        errors["base"] = "backup_failed"
                        return self.async_show_form(
                            step_id=step_id,
                            data_schema=(
                                _header_auth_schema()
                                if step_id == "auth_header"
                                else _basic_auth_schema(
                                    {**self.config_entry.data, **self.config_entry.options}
                                )
                            ),
                            errors=errors,
                        )
                await _async_remove_inactive_point_entities(
                    self.hass, self.config_entry, profile, candidate.get(CONF_SELECTED_POINT_IDS, ())
                )
            return self.async_create_entry(title="", data=candidate)
''',
    '''            self._pending_options = candidate
            self._available_points = points
            self._pending_device = device
            if profile == PROFILE_INDIVIDUAL:
                return await self.async_step_entity_selection()
            return await self.async_step_entity_preview()
''',
    "defer options cleanup",
)

old_options_selection = '''        if user_input is not None:
            self._pending_options[CONF_SELECTED_POINT_IDS] = _parse_selected_options(
                user_input.get(CONF_SELECTED_POINT_IDS)
            )
            if self._cleanup_inactive:
                if self._backup_before_cleanup:
                    try:
                        await _async_create_cleanup_backup(self.hass)
                    except Exception:
                        return self.async_show_form(
                            step_id="entity_selection",
                            data_schema=_entity_selection_schema(
                                points,
                                self._pending_options[CONF_SELECTED_POINT_IDS],
                                point_names=point_names,
                            ),
                            errors={"base": "backup_failed"},
                            description_placeholders={"count": str(len(points))},
                        )
                await _async_remove_inactive_point_entities(
                    self.hass,
                    self.config_entry,
                    PROFILE_INDIVIDUAL,
                    self._pending_options[CONF_SELECTED_POINT_IDS],
                )
            return self.async_create_entry(title="", data=self._pending_options)
'''
new_options_selection = '''        if user_input is not None:
            self._pending_options[CONF_SELECTED_POINT_IDS] = _parse_selected_options(
                user_input.get(CONF_SELECTED_POINT_IDS)
            )
            return await self.async_step_entity_preview()
'''
text = replace_once(
    text, old_options_selection, new_options_selection, "options selection preview routing"
)

if "    async def async_step_entity_preview(self, user_input=None):\n" not in text.split("class NibeLocalOptionsFlow", 1)[1]:
    options_preview = '''

    async def async_step_entity_preview(self, user_input=None):
        if self._pending_options is None or self._pending_device is None:
            return self.async_abort(reason="setup_state_missing")

        profile = str(
            self._pending_options.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE)
        )
        points = self._available_points or {}
        placeholders = await _async_entity_preview_placeholders(
            self.hass,
            points=points,
            profile=profile,
            selected_ids=self._pending_options.get(CONF_SELECTED_POINT_IDS, ()),
            device=self._pending_device,
            entry=self.config_entry,
            cleanup=self._cleanup_inactive,
            backup=self._backup_before_cleanup,
        )

        if user_input is not None:
            if self._cleanup_inactive:
                if self._backup_before_cleanup:
                    try:
                        await _async_create_cleanup_backup(self.hass)
                    except Exception:
                        return self.async_show_form(
                            step_id="entity_preview",
                            data_schema=vol.Schema({}),
                            errors={"base": "backup_failed"},
                            description_placeholders=placeholders,
                        )
                await _async_remove_inactive_point_entities(
                    self.hass,
                    self.config_entry,
                    profile,
                    self._pending_options.get(CONF_SELECTED_POINT_IDS, ()),
                )
            return self.async_create_entry(title="", data=self._pending_options)

        return self.async_show_form(
            step_id="entity_preview",
            data_schema=vol.Schema({}),
            description_placeholders=placeholders,
        )
'''
    text = text.rstrip() + options_preview + "\n"

path.write_text(text, encoding="utf-8")

# --- translations --------------------------------------------------------
preview_descriptions = {
    "de": (
        "Prüfe die Auswahl vor dem Anwenden. **Profil:** {profile} · **erkannte "
        "Variablen:** {discovered}. **Aktiv/ausgewählt:** {active_count} "
        "(bereits in der Registry: {active_existing}, neu: {active_new}).\n\n"
        "**Aktiv / ausgewählt**\n{active_list}\n\n"
        "**Nicht ausgewählt / abgewählt ({inactive_count})**\n{inactive_list}\n\n"
        "**Zur Registry-Löschung vorgesehen ({delete_count})**\n{delete_list}\n\n"
        "**Zusätzliche Integrationsentitäten ({special_count})**\n{special_list}\n\n"
        "Registry-Bereinigung: **{cleanup}** · Backup davor: **{backup}**. "
        "Bei großen Listen werden höchstens 50 Einträge je Bereich angezeigt; "
        "die Zähler sind vollständig. Erst mit „Senden“ werden die Einstellungen "
        "angewendet und gegebenenfalls Backup und Registry-Löschung ausgeführt."
    ),
    "en": (
        "Review the selection before applying it. **Profile:** {profile} · "
        "**discovered variables:** {discovered}. **Active/selected:** {active_count} "
        "(already in the registry: {active_existing}, new: {active_new}).\n\n"
        "**Active / selected**\n{active_list}\n\n"
        "**Not selected / deselected ({inactive_count})**\n{inactive_list}\n\n"
        "**Scheduled for registry deletion ({delete_count})**\n{delete_list}\n\n"
        "**Additional integration entities ({special_count})**\n{special_list}\n\n"
        "Registry cleanup: **{cleanup}** · Backup beforehand: **{backup}**. "
        "For large lists, at most 50 entries per section are shown; the counters "
        "remain complete. Settings, backup and any registry deletion are only "
        "applied after you press Submit."
    ),
}

for lang in ("de", "en"):
    translation_path = Path(f"custom_components/nibe_local/translations/{lang}.json")
    payload = json.loads(translation_path.read_text(encoding="utf-8"))
    title = "Entitätsübersicht prüfen" if lang == "de" else "Review entity overview"
    step = {"title": title, "description": preview_descriptions[lang]}
    payload["config"]["step"]["entity_preview"] = step
    payload["options"]["step"]["entity_preview"] = step
    translation_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

# --- manifest ------------------------------------------------------------
manifest_path = Path("custom_components/nibe_local/manifest.json")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"] = "0.9.3"
manifest_path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

# --- README --------------------------------------------------------------
readme_path = Path("README.md")
readme = readme_path.read_text(encoding="utf-8")
readme = readme.replace(
    "Aktuelle Integrationsversion: **0.9.2**",
    "Aktuelle Integrationsversion: **0.9.3**",
    1,
)
if "- [Entitätsvorschau vor dem Anwenden]" not in readme:
    readme = readme.replace(
        "- [Individuelle Auswahl](#-individuelle-auswahl)\n",
        "- [Individuelle Auswahl](#-individuelle-auswahl)\n"
        "- [Entitätsvorschau vor dem Anwenden](#-entitätsvorschau-vor-dem-anwenden)\n",
        1,
    )

if "## 🔎 Entitätsvorschau vor dem Anwenden" not in readme:
    marker = "\n---\n\n## 🏷️ Benennung der Entitäten\n"
    section = '''
---

## 🔎 Entitätsvorschau vor dem Anwenden

Vor dem Abschluss der Ersteinrichtung und vor dem Speichern geänderter Optionen zeigt die Integration eine letzte **Entitätsübersicht**. Dadurch ist vorab sichtbar, welche Auswirkungen das gewählte Profil oder die individuelle Auswahl hat.

Die Vorschau zeigt:

- **aktiv / ausgewählt** – erkannte Punkte, die nach dem Bestätigen bereitgestellt werden
- bei bestehenden Installationen zusätzlich, wie viele davon **bereits in der Entity Registry** vorhanden und wie viele **neu** sind
- **nicht ausgewählt / abgewählt** – Punkte, die nicht zum gewählten Umfang gehören und nicht zur Löschung vorgesehen sind
- **zur Registry-Löschung vorgesehen** – ausschließlich die numerischen Punkt-Entitäten, die die optionale Registry-Bereinigung tatsächlich entfernen würde
- **zusätzliche Integrationsentitäten** wie API-Erreichbarkeit, Fallback-Status, Meldungen/Alarme und – falls verfügbar – Smart Mode oder Lüftung+

Die Einträge werden mit **Name, Variable-ID und Einheit** dargestellt. Bei sehr großen Anlagen werden pro Bereich höchstens 50 Einträge angezeigt; die angezeigten Zähler enthalten trotzdem immer den vollständigen Umfang.

**Wichtig:** Ein angefordertes Backup und die Registry-Bereinigung werden erst nach der Bestätigung dieses letzten Dialogs ausgeführt. Wird der Dialog verlassen, bevor bestätigt wurde, erfolgt keine Registry-Löschung. Schlägt das angeforderte Backup fehl, bleibt die bereits vorhandene Schutzlogik bestehen und es wird nichts aus der Registry gelöscht.

---

## 🏷️ Benennung der Entitäten
'''
    if marker not in readme:
        raise RuntimeError("README insertion marker not found")
    readme = readme.replace(marker, "\n" + section, 1)
readme_path.write_text(readme, encoding="utf-8")

# --- CHANGELOG -----------------------------------------------------------
changelog_path = Path("CHANGELOG.md")
changelog = changelog_path.read_text(encoding="utf-8")
if "## 0.9.3" not in changelog:
    marker = "## 0.9.2\n"
    section = '''## 0.9.3

- Neuer letzter Schritt **Entitätsübersicht** bei Ersteinrichtung und Optionen: Vor dem Anwenden werden aktive/ausgewählte, abgewählte/beibehaltene und zur Registry-Löschung vorgesehene Punkt-Entitäten mit Name, Variable-ID und Einheit angezeigt.
- Bei bestehenden Installationen zeigt die Vorschau zusätzlich, wie viele aktive Punkte bereits in der Entity Registry vorhanden bzw. neu sind; Diagnose- und Spezialentitäten werden separat aufgeführt.
- Große Vorschaugruppen werden auf 50 sichtbare Einträge begrenzt, während die Zähler weiterhin den vollständigen Umfang anzeigen.
- Backup und Registry-Bereinigung werden erst nach der finalen Bestätigung ausgeführt. Ein Abbruch der Vorschau verändert die Registry nicht; ein fehlgeschlagenes angefordertes Backup verhindert weiterhin jede Löschung.
- Regressionstests für Vorschaugruppierung und die verzögerte Cleanup-Ausführung ergänzt.

'''
    if marker not in changelog:
        raise RuntimeError("CHANGELOG marker not found")
    changelog = changelog.replace(marker, section + marker, 1)
changelog_path.write_text(changelog, encoding="utf-8")

# --- tests ---------------------------------------------------------------
tests_path = Path("tests/test_logic.py")
tests = tests_path.read_text(encoding="utf-8")
if "import inspect\n" not in tests:
    tests = tests.replace("import json\n", "import inspect\nimport json\n", 1)

tests = replace_once(
    tests,
    '''from custom_components.nibe_local.config_flow import (
    CONF_BACKUP_BEFORE_CLEANUP,
''',
    '''from custom_components.nibe_local.config_flow import (
    CONF_BACKUP_BEFORE_CLEANUP,
    NibeLocalConfigFlow,
    NibeLocalOptionsFlow,
''',
    "test config flow class imports",
)

tests = replace_once(
    tests,
    '''    _point_options,
    _reauth_schema,
''',
    '''    _point_options,
    _preview_point_groups,
    _reauth_schema,
''',
    "preview helper test import",
)

if "def test_entity_preview_groups_match_cleanup_scope" not in tests:
    anchor = '''def test_individual_profile_uses_only_persisted_ids() -> None:
    selected = [4, "8", 3096]
    assert point_enabled(PROFILE_INDIVIDUAL, 4, selected)
    assert point_enabled(PROFILE_INDIVIDUAL, 8, selected)
    assert point_enabled(PROFILE_INDIVIDUAL, 3096, selected)
    assert not point_enabled(PROFILE_INDIVIDUAL, 10, selected)


'''
    addition = anchor + '''def test_entity_preview_groups_match_cleanup_scope() -> None:
    points = {"4": {}, "8": {}, "1755": {}, "999999": {}}
    preview = _preview_point_groups(
        points,
        PROFILE_MINIMAL,
        (),
        registered_ids={4, 1755, 999999},
        cleanup=True,
    )
    assert preview["active"] == frozenset({4, 8})
    assert preview["active_existing"] == frozenset({4})
    assert preview["active_new"] == frozenset({8})
    assert preview["delete"] == frozenset({1755, 999999})
    assert preview["inactive"] == frozenset()


def test_entity_preview_retains_deselected_registry_entries_without_cleanup() -> None:
    points = {"4": {}, "8": {}, "1755": {}, "999999": {}}
    preview = _preview_point_groups(
        points,
        PROFILE_MINIMAL,
        (),
        registered_ids={4, 1755, 999999},
        cleanup=False,
    )
    assert preview["delete"] == frozenset()
    assert preview["inactive"] == frozenset({1755, 999999})


def test_registry_cleanup_is_deferred_to_final_preview() -> None:
    selection_source = inspect.getsource(NibeLocalOptionsFlow.async_step_entity_selection)
    finish_source = inspect.getsource(NibeLocalOptionsFlow._async_finish_auth)
    preview_source = inspect.getsource(NibeLocalOptionsFlow.async_step_entity_preview)
    assert "_async_create_cleanup_backup" not in selection_source
    assert "_async_remove_inactive_point_entities" not in selection_source
    assert "_async_remove_inactive_point_entities" not in finish_source
    assert "_async_create_cleanup_backup" in preview_source
    assert "_async_remove_inactive_point_entities" in preview_source


def test_setup_waits_for_preview_before_creating_entry() -> None:
    profile_source = inspect.getsource(NibeLocalConfigFlow.async_step_entity_profile)
    selection_source = inspect.getsource(NibeLocalConfigFlow.async_step_entity_selection)
    preview_source = inspect.getsource(NibeLocalConfigFlow.async_step_entity_preview)
    assert "async_step_entity_preview" in profile_source
    assert "async_step_entity_preview" in selection_source
    assert "_create_pending_entry()" in preview_source


'''
    if anchor not in tests:
        raise RuntimeError("test insertion anchor not found")
    tests = tests.replace(anchor, addition, 1)

tests_path.write_text(tests, encoding="utf-8")

print("v0.9.3 entity preview changes prepared")
