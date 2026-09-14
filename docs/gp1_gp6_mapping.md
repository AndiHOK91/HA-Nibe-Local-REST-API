# GP1 / GP6 mapping notes

## Verified VVM S320 mapping

| Local REST point | Meaning on the verified VVM S320 installation | Integration status |
| ---: | --- | --- |
| `2792` | Heating circulation pump **GP1 speed** (`%`) | curated `sensor`; Standard + Extended |
| `1975` | Heating-medium pump **GP6 running state** (`0 % = off`, `100 % = on`) | curated `binary_sensor`; Standard + Extended + Individual |
| `10895` | Former GP6 status candidate | not exposed; current REST API returns `Point not found` |
| `3138` | Internal charge pump **GP12** | curated `binary_sensor`; Individual only (also available in Complete) |

For the verified VVM S320 installation the integration therefore uses local REST point `2792` for the variable GP1 speed and point `1975` as the GP6 running state.

## Runtime evidence

The local REST metadata labels points `1975` and `2792` similarly as GP1-related percentage values, but repeated runtime correlation against the physical pumps separates them clearly:

- GP1 off, GP6 off: `2792 = 0 %`, `1975 = 0 %`.
- GP1 running at about 38 %, GP6 off: `2792 = 38 %`, `1975 = 0 %`.
- GP1 running at 50 %, GP6 on: `2792 = 50 %`, `1975 = 100 %`.
- GP1 running at 30 %, GP6 on: `2792 = 30 %`, `1975 = 100 %`.
- GP1 running at 25 %, GP6 off: `2792 = 25 %`, `1975 = 0 %`.

This correlation shows that `2792` follows the variable-speed GP1, while `1975` follows the physical GP6 state independently and behaves as a 0/100 % run indicator on this installation.

The integration intentionally models point `1975` as a binary sensor and treats any non-zero value as running. This is robust if a future firmware ever reports a non-zero value other than 100.

## Why NIBE labels point 1975 like GP1

NIBE uses product-specific register sets and the local REST metadata is not always product-specific enough to describe the physical component correctly. The official S-series Modbus documentation contains multiple product-family mappings for similarly named GP1 values. Point `1975` is exposed as Modbus input register `1102` and belongs to NIBE's default Modbus list, so it remains part of the Standard profile. On this VVM S320 installation, runtime measurements are the decisive source for distinguishing the two exposed values.

## GP6 and obsolete point 10895

An older API/data crawl contained point `10895` named `Pumpe: Heizungsmedium (GP6)` with values `0 = Aus` and `1 = Ein`. The current VVM S320 REST API no longer exposes that point: it is absent from the bulk `/points` response and a direct `/points/10895` request returns `Point not found`.

The integration therefore does not create a GP6 entity from point `10895` and does not perform a targeted fallback request for it. GP6 is instead represented by the verified point `1975`.

A separate service/forced-control variable for GP6 may exist in menu 7.5.3. Service/test controls remain intentionally excluded and are not used as a substitute for the normal running-state sensor.

## Profile policy

Both verified pump values are available in the **Standard** and **Extended** entity lists during setup:

- `2792` — GP1 speed
- `1975` — GP6 running state

GP12 point `3138` is intentionally **not** enabled by Standard or Extended. It remains a curated point so that, when selected explicitly in the **Individual** profile, Home Assistant creates the correct binary sensor **“Interne Ladepumpe (GP12)”** with running semantics instead of a generic discovered percentage/value sensor. The Complete profile also exposes it when the local REST API provides the point.

## References

- NIBE Technical information, Modbus S-Series: https://www.nibe.eu/download/18.42a6470a1963dded290bb1/1746538843623/Technical%20information%20Modbus%20S-Series.pdf
- NIBE VVM S320 installer documentation: https://www.nibe.eu/en-eu/products/heat-pumps/air-water-heat-pumps/vvm-s320
- NIBE firmware version history: https://www.nibe.eu/myuplink_changelog/nibe-n.pdf
