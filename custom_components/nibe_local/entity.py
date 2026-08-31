"""Base entities for NIBE Local REST."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PointDef
from .coordinator import NibeCoordinator

FRIENDLY_NAMES = {
    4: "Aktuelle Außenlufttemperatur (BT1)",
    8: "Vorlauf (BT2)",
    10: "Rücklauf (BT3)",
    11: "Brauchwasser, oben (BT7)",
    12: "Brauchwasserbereitung (BT6)",
    54: "Mittlere Temperatur (BT1)",
    58: "Volumenstrommesser (BF1)",
    158: "Raumtemperatur (BT50)",
    248: "KWL Drehzahl Abluft",
    249: "KWL Drehzahl Zuluft",
    599: "Verdichter Gesamtzeit Kühlung, Wärmepumpe 1 (EP14)",
    781: "Gradminuten",
    829: "Energiezähler Impuls (BE6)",
    832: "Alarmnummer von Außenluftwärmepumpe (EB101)",
    834: "Ventilatordrehzahl (EB101)",
    839: "Erzeugte Leistung Wärme (EB101)",
    840: "Zeit bis Enteisung (EB101)",
    841: "Enteisung Index (EB101)",
    842: "Überhitzung Referenz EEV (EB101)",
    843: "Überhitzung EEV (EB101)",
    844: "EEV-ssh-error (EB101)",
    845: "Überhitzung Temp. Referenz EEV (EB101)",
    846: "Sollwert EEV (EB101)",
    847: "EEV PV (EB101)",
    848: "EEV-te-error durchschnittl. geöffnet (EB101)",
    849: "Öffnungsgrad EEV (EB101)",
    852: "EEV-ssh-error (EVI) (EB101)",
    856: "EEV-te-error durchschnittl. geöffnet in (EVI) (EB101)",
    992: "Niederdruck (EB101 BP8 dew)",
    993: "Hochdruck (EB101 BP9 dew)",
    994: "Einspritzung (EB101-BT81)",
    995: "Druckgeber, Einspritzung (EB101-BP11)",
    996: "EVI-Druck (EB101-EP14-BP11 dew)",
    997: "Verdampfer (EB101-BT84)",
    998: "Ventilatorstatus (EB101-EP14)",
    999: "Ventilator U/min (EB101-EP14)",
    1186: "Zusatzheizung mit Vorrang zulassen",
    1708: "Berechneter Vorlauf Klimatisierungssystem 1",
    1716: "Kühlung Status",
    1755: "Gesamtbetriebszeit Zusatzheizung",
    1756: "Leistung interne Zusatzheizung",
    1758: "Betriebspriorität",
    1760: "Betriebsmodus interne Zusatzheizung",
    1820: "Externe Blockierung",
    1827: "Stufengeregelte Zusatzheizung Blockierung",
    1829: "Brauchwasserzirkulation (GP11)",
    1865: "Betriebszeit elektrische Zusatzheizung für Brauchwasser",
    1942: "Mehr Brauchwasser Status",
    1975: "Drehzahl Heizungsumwälzpumpe (GP1)",
    2002: "Umschaltventil Brauchwasser (QN10)",
    2022: "Aktueller Status",
    2491: "Rücklauf (EB101-BT3)",
    2494: "Kondensatorfühler, Vorlauf (EB101-BT12)",
    2495: "Heißgas (EB101-BT14)",
    2496: "Flüssigkeitsleitung (EB101-BT15)",
    2497: "Sauggas (EB101-BT17)",
    2500: "Verdichterstatus (EB101)",
    2501: "Verdichter, Zeit bis Start (EB101-EP14)",
    2505: "Verdichter, Anzahl Starts (EB101-EP14)",
    2506: "Verdichter, Gesamtbetriebszeit (EB101-EP14)",
    2507: "Verdichter, Betriebszeit Brauchwasser (EB101-EP14)",
    2508: "Alarmnummer (EB101-EP14)",
    2657: "Verdichter, angefordert (EB101-EP14)",
    2683: "Kühlung Blockierung",
    2685: "Nächste periodische Brauchwassererhöhung",
    2691: "Kühlgradminuten",
    2695: "Berechneter Kühlungsvorlauf Klimatisierungssystem 1",
    2729: "Verdichter verwenden Kühlung",
    2766: "Außenlufttemperatur (EB101-BT28)",
    2767: "Verdampfer (EB101-BT16)",
    2792: "Drehzahl Heizungsumwälzpumpe (GP1) – Variable 2792",
    3095: "Niederdruck (EB101-BP8)",
    3096: "Aktuelle Verdichterfrequenz (EB101)",
    3097: "Schutzmodus (EB101)",
    3098: "Enteisung (EB101)",
    3101: "Leistung (EB101-EP14)",
    3138: "Interne Ladepumpe (GP12)",
    3170: "Angeforderte Verdichterfrequenz (EB101)",
    3252: "Strom (EB101-EP14)",
    3353: "Temperatur, Wechselrichter (EB101-EP14)",
    3354: "Ventilatordrehzahl (EB101-EP14)",
    3375: "Alarmnummer",
    3667: "Heizkurve Klimatisierungssystem 1",
    3671: "Verschieb. Heizkurve Klimatisierungssystem 1",
    3697: "Brauchwasserbedarf",
    3699: "Starttemperatur BW hohe Temperatur",
    3700: "Starttemperatur BW normale Temperatur",
    3701: "Starttemperatur BW niedrige Temperatur",
    3702: "Stopptemperatur BW periodische Erhöhung",
    3703: "Stopptemperatur BW hohe Temperatur",
    3704: "Stopptemperatur BW normale Temperatur",
    3705: "Stopptemperatur BW niedrige Temperatur",
    3706: "Periodisches Brauchwasser",
    3707: "Periodisches Brauchwasser-Intervall",
    3708: "Startzeit periodisches Brauchwasser",
    3710: "BWZ Betriebszeit",
    3711: "BWZ Stillstandszeit",
    3748: "Periodenzeit Brauchwasser",
    3749: "Periodenzeit Heizung",
    3751: "Betriebsmodus",
    3830: "Ventilationsmodus",
    3841: "Rückstellzeit Ventilator 4",
    3842: "Rückstellzeit Ventilator 3",
    3843: "Rückstellzeit Ventilator 2",
    3844: "Rückstellzeit Ventilator 1",
    3919: "Zusatzheizung zulassen, Heizung",
    3920: "Heizung zulassen",
    3921: "Kühlung zulassen",
    4030: "Mehr Brauchwasser (Anzahl Minuten)",
    4040: "Nachtabsenkung",
    4041: "Starttemperatur Nachtabsenkung",
    4064: "Betriebsmodus",
    4564: "Mehr Brauchwasser",
    5025: "Kühlkurve Klimatisierungssystem 1",
    5033: "Verschieb. Kühlkurve Klimatisierungssystem 1",
    7934: "Abluft (AZ30-BT20)",
    7935: "Fortluft (AZ30-BT21)",
    7936: "Zuluft (AZ30-BT22)",
    7937: "Außenlufttemperatur (AZ30-BT23)",
    7939: "Luftfeuchtigkeit (AZ30-BM20)",
    8052: "Start Enteisung Ventilator (EB101)",
    8060: "Enteisung angefordert (EB101)",
    22268: "Letzte Enteisung Wärmepumpe 1",
    25165: "Energieprotokoll – Tatsächlicher Energieverbrauch",
    25166: "Energieprotokoll – Tatsächlicher Energieverbrauch, Komponenten",
}


def _clean(text: str | None) -> str:
    return (text or "").replace("\u00ad", "").strip()


def point_value(point: dict[str, Any]) -> dict[str, Any]:
    """Return the value object.

    Current NIBE firmware uses the key "value". Older documentation/examples
    may refer to it as "datavalue", so keep both for compatibility.
    """
    return point.get("value") or point.get("datavalue") or {}


def raw_value(point: dict[str, Any]) -> int | str | None:
    dv = point_value(point)
    sv = dv.get("stringValue")
    if sv not in (None, ""):
        return sv
    return dv.get("integerValue")


def scaled_value(point: dict[str, Any]) -> int | float | str | None:
    raw = raw_value(point)
    if not isinstance(raw, (int, float)):
        return raw
    md = point.get("metadata") or {}
    divisor = md.get("divisor") or 1
    try:
        value = raw / divisor
    except (TypeError, ZeroDivisionError):
        value = raw
    decimal = md.get("decimal")
    if isinstance(decimal, int) and decimal >= 0:
        value = round(value, decimal)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def to_raw(point: dict[str, Any], value: float) -> int:
    md = point.get("metadata") or {}
    divisor = md.get("divisor") or 1
    return int(round(value * divisor))


class NibePointEntity(CoordinatorEntity[NibeCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: NibeCoordinator, definition: PointDef) -> None:
        super().__init__(coordinator)
        self.definition = definition
        self._attr_unique_id = f"{coordinator.api.device_id}_{definition.point_id}"
        if definition.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def point(self) -> dict[str, Any] | None:
        return self.coordinator.point(self.definition.point_id)

    @property
    def available(self) -> bool:
        point = self.point
        if not self.coordinator.last_update_success or not point:
            return False
        return bool(point_value(point).get("isOk", True))

    @property
    def name(self) -> str:
        # Stable German names keep entity names readable even when the NIBE API
        # switches its point titles between languages/firmware versions.
        return FRIENDLY_NAMES.get(
            self.definition.point_id,
            _clean((self.point or {}).get("title"))
            or self.definition.key.replace("_", " ").title(),
        )

    @property
    def device_info(self) -> DeviceInfo:
        device = (self.coordinator.data or {}).get("device", {})
        product = device.get("product") or {}
        serial = product.get("serialNumber") or self.coordinator.api.device_id
        return DeviceInfo(
            identifiers={(DOMAIN, str(serial))},
            manufacturer=product.get("manufacturer") or "NIBE",
            name=product.get("name") or "NIBE VVM S320",
            model=product.get("name"),
            sw_version=product.get("firmwareId"),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        point = self.point or {}
        md = point.get("metadata") or {}
        return {
            "point_id": self.definition.point_id,
            "group": self.definition.group,
            "description": _clean(point.get("description")),
            "variable_type": md.get("variableType"),
            "variable_size": md.get("variableSize"),
            "is_writable": md.get("isWritable"),
            "modbus_register_type": md.get("modbusRegisterType"),
            "modbus_register_id": md.get("modbusRegisterID"),
            "raw_value": raw_value(point),
            "divisor": md.get("divisor"),
            "decimal": md.get("decimal"),
            "min_value_raw": md.get("minValue"),
            "max_value_raw": md.get("maxValue"),
        }
