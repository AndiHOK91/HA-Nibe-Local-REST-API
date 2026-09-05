"""Constants for NIBE Local REST."""
from dataclasses import dataclass
from typing import Literal

DOMAIN = "nibe_local"
NIBE_DEVICE_ID = "0"
DEFAULT_PORT = 8443
DEFAULT_SCAN_INTERVAL = 10
MIN_SCAN_INTERVAL = 5
DEFAULT_COMMAND_POLL_DELAY_MS = 1000
COMMAND_POLL_DELAY_OPTIONS_MS = (250, 500, 750, 1000, 1500, 2000, 3000, 5000)

CONF_AUTH_METHOD = "auth_method"
CONF_AUTH_HEADER = "auth_header"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_COMMAND_POLL_DELAY_MS = "command_poll_delay_ms"
CONF_ENTITY_PROFILE = "entity_profile"
CONF_SELECTED_POINT_IDS = "selected_point_ids"
CONF_ENTITY_NAMING = "entity_naming"

ENTITY_NAMING_HOME_ASSISTANT = "home_assistant"
ENTITY_NAMING_LOCAL_API = "local_api"
ENTITY_NAMING_TECHNICAL = "technical"
ENTITY_NAMING_MODES = (
    ENTITY_NAMING_HOME_ASSISTANT,
    ENTITY_NAMING_LOCAL_API,
    ENTITY_NAMING_TECHNICAL,
)
DEFAULT_ENTITY_NAMING = ENTITY_NAMING_HOME_ASSISTANT

AUTH_METHOD_BASIC = "basic"
AUTH_METHOD_HEADER = "header"

POINT_OPERATING_PRIORITY = 1758
POINT_OPERATING_MODE_SETTING = 3751
POINT_OPERATING_MODE_STATUS = 4064
POINT_AUX_HEAT_ALLOWED_HEATING = 3919
POINT_HEATING_ALLOWED = 3920
POINT_COOLING_ALLOWED = 3921
POINT_MORE_HOT_WATER_MINUTES = 4030
POINT_MORE_HOT_WATER = 4564
POINT_VENTILATION_MODE = 3830
POINT_HOT_WATER_DEMAND = 3697
POINT_PERIODIC_HOT_WATER_DATE = 2685
POINT_TIME_TO_DEFROST = 840
POINT_DEFROST_REQUESTED = 8060

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
    PointDef(781, "degree_minutes", "system"),
    PointDef(1755, "aux_heat_total_time", "system"),
    PointDef(1756, "aux_heat_power", "system"),
    PointDef(1758, "operating_priority", "system", "sensor"),
    PointDef(1186, "prioritized_aux_heat_allowed", "system", "binary_sensor"),
    PointDef(1760, "aux_heat_mode", "system"),
    PointDef(1820, "external_blocking", "system", "binary_sensor"),
    PointDef(1827, "step_controlled_aux_heat_blocking", "system", "binary_sensor"),
    PointDef(2022, "current_status", "system", diagnostic=True),
    PointDef(3751, "operating_mode_setting", "system", "select"),
    PointDef(3919, "aux_heat_allowed_heating", "heating", "switch"),
    PointDef(4064, "operating_mode_status", "system"),
    PointDef(3375, "alarm_number", "system", diagnostic=True),
    PointDef(4, "outdoor_temperature_bt1", "heating"),
    PointDef(29, "room_sensor_1_1_bt50", "heating"),
    PointDef(54, "mean_outdoor_temperature_bt1", "heating"),
    PointDef(8, "supply_temperature_bt2", "heating"),
    PointDef(10, "return_temperature_bt3", "heating"),
    PointDef(58, "flow_bf1", "heating"),
    PointDef(91, "additional_heat_bt63", "heating"),
    PointDef(158, "room_average_temperature_bt50", "heating"),
    PointDef(1708, "calculated_supply_heating", "heating"),
    PointDef(3667, "heating_curve", "heating", "number"),
    PointDef(3671, "heating_curve_offset", "heating", "number"),
    PointDef(3920, "heating_allowed", "heating", "switch"),
    PointDef(1716, "cooling_status", "cooling", "binary_sensor"),
    PointDef(2683, "cooling_blocked", "cooling", "binary_sensor"),
    PointDef(2691, "cooling_degree_minutes", "cooling"),
    PointDef(2695, "calculated_supply_cooling", "cooling"),
    PointDef(2729, "compressor_for_cooling", "cooling", "binary_sensor"),
    PointDef(3921, "cooling_allowed", "cooling", "switch"),
    PointDef(5025, "cooling_curve", "cooling", "number"),
    PointDef(5033, "cooling_curve_offset", "cooling", "number"),
    PointDef(11, "hot_water_top_bt7", "hot_water"),
    PointDef(12, "hot_water_charge_bt6", "hot_water"),
    PointDef(116, "hot_water_outlet_bt70", "hot_water"),
    PointDef(10894, "hot_water_start_bt5", "hot_water"),
    PointDef(1829, "hot_water_circulation_gp11", "hot_water", "binary_sensor"),
    PointDef(1865, "aux_heat_hot_water_total_time", "hot_water"),
    PointDef(1942, "more_hot_water_status", "hot_water", "binary_sensor"),
    PointDef(2002, "hot_water_diverter_qn10", "hot_water", "binary_sensor"),
    PointDef(2685, "periodic_hot_water_date", "hot_water"),
    PointDef(3697, "hot_water_position", "hot_water", "select"),
    PointDef(3699, "hot_water_start_high", "hot_water", "number"),
    PointDef(3700, "hot_water_start_normal", "hot_water", "number"),
    PointDef(3701, "hot_water_start_low", "hot_water", "number"),
    PointDef(3702, "hot_water_stop_periodic_increase", "hot_water", "number"),
    PointDef(3703, "hot_water_stop_high", "hot_water", "number"),
    PointDef(3704, "hot_water_stop_normal", "hot_water", "number"),
    PointDef(3705, "hot_water_stop_low", "hot_water", "number"),
    PointDef(3706, "periodic_hot_water", "hot_water", "switch"),
    PointDef(3707, "periodic_hot_water_interval", "hot_water", "number"),
    PointDef(3708, "periodic_hot_water_start_time", "hot_water", "time"),
    PointDef(3710, "hot_water_operating_time", "hot_water", "number"),
    PointDef(3711, "hot_water_standstill_time", "hot_water", "number"),
    PointDef(3748, "hot_water_period_time", "hot_water", "number"),
    PointDef(3749, "heating_period_time", "heating", "number"),
    PointDef(4030, "more_hot_water_minutes", "hot_water"),
    PointDef(4564, "more_hot_water", "hot_water", "switch"),
    PointDef(7849, "hot_water_circulation_period_1_start", "hot_water", "time"),
    PointDef(7850, "hot_water_circulation_period_2_start", "hot_water", "time"),
    PointDef(7851, "hot_water_circulation_period_3_start", "hot_water", "time"),
    PointDef(7852, "hot_water_circulation_period_1_stop", "hot_water", "time"),
    PointDef(7853, "hot_water_circulation_period_2_stop", "hot_water", "time"),
    PointDef(7854, "hot_water_circulation_period_3_stop", "hot_water", "time"),
    PointDef(829, "energy_meter_pulse_be6", "energy"),
    PointDef(25165, "energy_log_current_power_consumption", "energy"),
    PointDef(25166, "energy_log_current_power_components", "energy"),
    PointDef(1975, "heating_circulation_pump_gp1", "hydraulics"),
    PointDef(2792, "heating_circulation_pump_gp1_2792", "hydraulics"),
    PointDef(3138, "internal_charge_pump_gp12", "hydraulics", "binary_sensor"),
    PointDef(832, "outdoor_unit_alarm", "heat_pump", diagnostic=True),
    PointDef(834, "outdoor_unit_fan_speed", "heat_pump"),
    PointDef(839, "generated_heat_power", "heat_pump"),
    PointDef(599, "compressor_total_time_cooling", "heat_pump"),
    PointDef(2491, "s2125_return_bt3", "heat_pump"),
    PointDef(2494, "s2125_condenser_supply_bt12", "heat_pump"),
    PointDef(2495, "s2125_hot_gas_bt14", "heat_pump"),
    PointDef(2496, "s2125_liquid_line_bt15", "heat_pump"),
    PointDef(2497, "s2125_suction_gas_bt17", "heat_pump"),
    PointDef(2500, "compressor_status", "heat_pump"),
    PointDef(2501, "compressor_time_to_start", "heat_pump"),
    PointDef(2505, "compressor_starts", "heat_pump"),
    PointDef(2506, "compressor_total_time", "heat_pump"),
    PointDef(2507, "compressor_hot_water_time", "heat_pump"),
    PointDef(2508, "compressor_alarm", "heat_pump", diagnostic=True),
    PointDef(2657, "compressor_requested", "heat_pump", "binary_sensor"),
    PointDef(2766, "s2125_outdoor_bt28", "heat_pump"),
    PointDef(2767, "s2125_evaporator_bt16", "heat_pump"),
    PointDef(3095, "s2125_low_pressure_bp8", "heat_pump"),
    PointDef(3096, "compressor_frequency", "heat_pump"),
    PointDef(3097, "protection_mode", "heat_pump", "binary_sensor", diagnostic=True),
    PointDef(3098, "defrost", "heat_pump", "binary_sensor", diagnostic=True),
    PointDef(3101, "compressor_power", "heat_pump"),
    PointDef(3170, "compressor_requested_frequency", "heat_pump"),
    PointDef(3252, "compressor_current", "heat_pump"),
    PointDef(3353, "inverter_temperature", "heat_pump"),
    PointDef(3354, "compressor_fan_speed", "heat_pump"),
    PointDef(840, "time_to_defrost", "eev_defrost", diagnostic=True),
    PointDef(841, "defrost_index", "eev_defrost", diagnostic=True),
    PointDef(842, "eev_superheat_reference", "eev_defrost", diagnostic=True),
    PointDef(843, "eev_superheat", "eev_defrost", diagnostic=True),
    PointDef(844, "eev_ssh_error_average_open", "eev_defrost", diagnostic=True),
    PointDef(845, "eev_superheat_temperature_reference", "eev_defrost", diagnostic=True),
    PointDef(846, "eev_setpoint", "eev_defrost", diagnostic=True),
    PointDef(847, "eev_process_value", "eev_defrost", diagnostic=True),
    PointDef(848, "eev_te_error_average_open", "eev_defrost", diagnostic=True),
    PointDef(849, "eev_opening_degree", "eev_defrost", diagnostic=True),
    PointDef(852, "evi_ssh_error", "eev_defrost", diagnostic=True),
    PointDef(856, "evi_te_error_average_open", "eev_defrost", diagnostic=True),
    PointDef(992, "low_pressure_dew", "eev_defrost", diagnostic=True),
    PointDef(993, "high_pressure_dew", "eev_defrost", diagnostic=True),
    PointDef(994, "injection_temperature_bt81", "eev_defrost", diagnostic=True),
    PointDef(995, "injection_pressure_bp11", "eev_defrost", diagnostic=True),
    PointDef(996, "evi_pressure_dew", "eev_defrost", diagnostic=True),
    PointDef(997, "evaporator_bt84", "eev_defrost", diagnostic=True),
    PointDef(998, "fan_status_ep14", "eev_defrost", diagnostic=True),
    PointDef(999, "fan_rpm_ep14", "eev_defrost", diagnostic=True),
    PointDef(8052, "start_defrost_fan", "eev_defrost", diagnostic=True),
    PointDef(8060, "defrost_requested", "eev_defrost", diagnostic=True),
    PointDef(22268, "last_defrost_heat_pump_1", "eev_defrost", diagnostic=True),
    PointDef(3830, "ventilation_mode", "ventilation", "select"),
    PointDef(4040, "night_reduction", "ventilation", "switch"),
    PointDef(4041, "night_reduction_start_temperature", "ventilation", "number"),
    PointDef(3841, "fan_reset_time_4", "ventilation", "number"),
    PointDef(3842, "fan_reset_time_3", "ventilation", "number"),
    PointDef(3843, "fan_reset_time_2", "ventilation", "number"),
    PointDef(3844, "fan_reset_time_1", "ventilation", "number"),
    PointDef(248, "ventilation_exhaust_fan_speed", "ventilation"),
    PointDef(249, "ventilation_supply_fan_speed", "ventilation"),
    PointDef(7934, "ventilation_exhaust_bt20", "ventilation"),
    PointDef(7935, "ventilation_extract_bt21", "ventilation"),
    PointDef(7936, "ventilation_supply_bt22", "ventilation"),
    PointDef(7937, "ventilation_outdoor_bt23", "ventilation"),
    PointDef(7939, "ventilation_humidity_bm20", "ventilation"),
)
