"""Constants for NIBE Local REST."""
from dataclasses import dataclass
from typing import Literal

DOMAIN = "nibe_local"
DEFAULT_PORT = 8443
DEFAULT_SCAN_INTERVAL = 10
MIN_SCAN_INTERVAL = 5
DEFAULT_COMMAND_POLL_DELAY_MS = 1000
COMMAND_POLL_DELAY_OPTIONS_MS = (250, 500, 750, 1000, 1500, 2000, 3000, 5000)

CONF_DEVICE_ID = "device_id"
CONF_AUTH_HEADER = "auth_header"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_COMMAND_POLL_DELAY_MS = "command_poll_delay_ms"

PLATFORMS = ["sensor", "binary_sensor", "number", "switch", "select", "time"]

Platform = Literal["sensor", "binary_sensor", "number", "switch", "select", "time"]

@dataclass(frozen=True, slots=True)
class PointDef:
    point_id: int
    key: str
    group: str
    platform: Platform = "sensor"
    diagnostic: bool = False

POINTS: tuple[PointDef, ...] = (
    PointDef(781, "degree_minutes", "System"), PointDef(1755, "aux_heat_total_time", "System"), PointDef(1756, "aux_heat_power", "System"), PointDef(1758, "operating_priority", "system", "sensor"), PointDef(1186, "prioritized_aux_heat_allowed", "System", "binary_sensor"), PointDef(1760, "aux_heat_mode", "System"), PointDef(1820, "external_blocking", "System", "binary_sensor"), PointDef(1827, "step_controlled_aux_heat_blocking", "System", "binary_sensor"), PointDef(2022, "current_status", "System"), PointDef(3751, "operating_mode_setting", "System", "select"), PointDef(3752, "hu_pump_operating_mode", "Hydraulik", "select"), PointDef(3919, "aux_heat_allowed_heating", "Heizung", "switch"), PointDef(4064, "operating_mode_status", "System"), PointDef(3375, "alarm_number", "System", diagnostic=True),
    PointDef(4, "outdoor_temperature_bt1", "Heizung"), PointDef(54, "mean_outdoor_temperature_bt1", "Heizung"), PointDef(8, "supply_temperature_bt2", "Heizung"), PointDef(10, "return_temperature_bt3", "Heizung"), PointDef(58, "flow_bf1", "Heizung"), PointDef(1708, "calculated_supply_heating", "Heizung"), PointDef(3667, "heating_curve", "Heizung", "number"), PointDef(3671, "heating_curve_offset", "Heizung", "number"), PointDef(3920, "heating_allowed", "Heizung", "switch"),
    PointDef(1716, "cooling_status", "Kühlung", "binary_sensor"), PointDef(2683, "cooling_blocked", "Kühlung", "binary_sensor"), PointDef(2691, "cooling_degree_minutes", "Kühlung"), PointDef(2695, "calculated_supply_cooling", "Kühlung"), PointDef(2729, "compressor_for_cooling", "Kühlung", "binary_sensor"), PointDef(3921, "cooling_allowed", "Kühlung", "switch"), PointDef(5025, "cooling_curve", "Kühlung", "number"), PointDef(5033, "cooling_curve_offset", "Kühlung", "number"),
    PointDef(11, "hot_water_top_bt7", "Warmwasser"), PointDef(12, "hot_water_charge_bt6", "Warmwasser"), PointDef(1829, "hot_water_circulation_gp11", "Warmwasser", "binary_sensor"), PointDef(1942, "more_hot_water_status", "Warmwasser", "binary_sensor"), PointDef(2002, "hot_water_diverter_qn10", "Warmwasser", "binary_sensor"), PointDef(2038, "hot_water_comfort_mode_status", "Warmwasser"), PointDef(3697, "hot_water_position", "Warmwasser", "select"), PointDef(3699, "hot_water_start_high", "Warmwasser", "number"), PointDef(3700, "hot_water_start_normal", "Warmwasser", "number"), PointDef(3701, "hot_water_start_low", "Warmwasser", "number"), PointDef(3702, "hot_water_stop_periodic_increase", "Warmwasser", "number"), PointDef(3703, "hot_water_stop_high", "Warmwasser", "number"), PointDef(3704, "hot_water_stop_normal", "Warmwasser", "number"), PointDef(3705, "hot_water_stop_low", "Warmwasser", "number"), PointDef(3706, "periodic_hot_water", "Warmwasser", "switch"), PointDef(3707, "periodic_hot_water_interval", "Warmwasser", "number"), PointDef(3708, "periodic_hot_water_start_time", "Warmwasser", "time"), PointDef(3710, "hot_water_operating_time", "Warmwasser", "number"), PointDef(3711, "hot_water_standstill_time", "Warmwasser", "number"), PointDef(3748, "hot_water_period_time", "Warmwasser", "number"), PointDef(3749, "heating_period_time", "Heizung", "number"), PointDef(4030, "more_hot_water_minutes", "Warmwasser"), PointDef(4564, "more_hot_water", "Warmwasser", "switch"),
    PointDef(829, "energy_meter_pulse_be6", "Energie"), PointDef(1975, "heating_circulation_pump_gp1", "Hydraulik"), PointDef(3138, "internal_charge_pump_gp12", "Hydraulik", "binary_sensor"),
    PointDef(832, "outdoor_unit_alarm", "S2125", diagnostic=True), PointDef(834, "outdoor_unit_fan_speed", "S2125"), PointDef(839, "generated_heat_power", "S2125"), PointDef(2491, "s2125_return_bt3", "S2125"), PointDef(2494, "s2125_condenser_supply_bt12", "S2125"), PointDef(2495, "s2125_hot_gas_bt14", "S2125"), PointDef(2496, "s2125_liquid_line_bt15", "S2125"), PointDef(2497, "s2125_suction_gas_bt17", "S2125"), PointDef(2500, "compressor_status", "S2125"), PointDef(2501, "compressor_time_to_start", "S2125"), PointDef(2505, "compressor_starts", "S2125"), PointDef(2506, "compressor_total_time", "S2125"), PointDef(2507, "compressor_hot_water_time", "S2125"), PointDef(2508, "compressor_alarm", "S2125", diagnostic=True), PointDef(2657, "compressor_requested", "S2125", "binary_sensor"), PointDef(2766, "s2125_outdoor_bt28", "S2125"), PointDef(2767, "s2125_evaporator_bt16", "S2125"), PointDef(3095, "s2125_low_pressure_bp8", "S2125"), PointDef(3096, "compressor_frequency", "S2125"), PointDef(3097, "protection_mode", "S2125", "binary_sensor", diagnostic=True), PointDef(3098, "defrost", "S2125", "binary_sensor", diagnostic=True), PointDef(3101, "compressor_power", "S2125"), PointDef(3170, "compressor_requested_frequency", "S2125"), PointDef(3252, "compressor_current", "S2125"), PointDef(3353, "inverter_temperature", "S2125"), PointDef(3354, "compressor_fan_speed", "S2125"),
    PointDef(840, "time_to_defrost", "EEV / Abtauung", diagnostic=True), PointDef(841, "defrost_index", "EEV / Abtauung", diagnostic=True), PointDef(842, "eev_superheat_reference", "EEV / Abtauung", diagnostic=True), PointDef(843, "eev_superheat", "EEV / Abtauung", diagnostic=True), PointDef(844, "eev_ssh_error", "EEV / Abtauung", diagnostic=True), PointDef(845, "eev_superheat_temperature_reference", "EEV / Abtauung", diagnostic=True), PointDef(846, "eev_setpoint", "EEV / Abtauung", diagnostic=True), PointDef(847, "eev_process_value", "EEV / Abtauung", diagnostic=True), PointDef(848, "eev_te_error_average_open", "EEV / Abtauung", diagnostic=True), PointDef(849, "eev_opening_degree", "EEV / Abtauung", diagnostic=True), PointDef(852, "evi_ssh_error", "EEV / Abtauung", diagnostic=True), PointDef(856, "evi_te_error_average_open", "EEV / Abtauung", diagnostic=True), PointDef(992, "low_pressure_dew", "EEV / Abtauung", diagnostic=True), PointDef(993, "high_pressure_dew", "EEV / Abtauung", diagnostic=True), PointDef(994, "injection_temperature_bt81", "EEV / Abtauung", diagnostic=True), PointDef(995, "injection_pressure_bp11", "EEV / Abtauung", diagnostic=True), PointDef(996, "evi_pressure_dew", "EEV / Abtauung", diagnostic=True), PointDef(997, "evaporator_bt84", "EEV / Abtauung", diagnostic=True), PointDef(998, "fan_status_ep14", "EEV / Abtauung", diagnostic=True), PointDef(999, "fan_rpm_ep14", "EEV / Abtauung", diagnostic=True), PointDef(8052, "start_defrost_fan", "EEV / Abtauung", diagnostic=True), PointDef(8060, "defrost_requested", "EEV / Abtauung", diagnostic=True),
    PointDef(3830, "ventilation_mode", "Lüftung", "select"), PointDef(4040, "night_reduction", "Lüftung", "switch"), PointDef(4041, "night_reduction_start_temperature", "Lüftung", "number"), PointDef(3841, "fan_reset_time_4", "Lüftung", "number"), PointDef(3842, "fan_reset_time_3", "Lüftung", "number"), PointDef(3843, "fan_reset_time_2", "Lüftung", "number"), PointDef(3844, "fan_reset_time_1", "Lüftung", "number"), PointDef(3845, "filter_change_interval", "Lüftung", "number"), PointDef(7934, "ventilation_exhaust_bt20", "Lüftung"), PointDef(7935, "ventilation_extract_bt21", "Lüftung"), PointDef(7936, "ventilation_supply_bt22", "Lüftung"), PointDef(7937, "ventilation_outdoor_bt23", "Lüftung"), PointDef(7939, "ventilation_humidity_bm20", "Lüftung"),
)

POINT_BY_ID = {p.point_id: p for p in POINTS}
