# GP1 / GP6 mapping notes

This integration deliberately treats the VVM S320/S325 pump values as two different signals.

| Local REST point | Meaning | Home Assistant entity |
| ---: | --- | --- |
| `2792` | Heating circulation / heating-medium pump **GP1 speed** (`%`) | `sensor` |
| `10895` | Heating-medium pump **GP6 running status** (`0 = off`, `1 = on`) | `binary_sensor` |
| `1975` | Same-named GP1 speed point seen on other S-series product families / API datasets | not curated; available as a discovered point in Complete or Individual profiles |

## Why both 1975 and 2792 can exist

NIBE uses product-specific register sets. The official S-series Modbus documentation lists GP1 speed as input register `1102` for S1155/S1255-class products, while VVM S320/S325 uses input register `1636` for GP1 speed. Local REST datasets can therefore contain more than one variable carrying the same human-readable GP1 label.

For VVM S320/S325 the integration uses local REST point `2792` as the canonical GP1 speed value. Point `1975` is intentionally not placed in the curated `POINTS` catalogue or Standard profile, but the generic discovery path still allows it to be exposed explicitly when it is relevant to another system.

## GP6 is not a second GP1 speed value

Local REST point `10895` reports an unsigned 8-bit state with the observed values `0` and `1`. It is therefore represented as a running-state binary sensor, not as a percentage sensor.

A separate menu/service variable can exist for forced GP6 control. Service/test controls must not be confused with the normal read-only running status and are intentionally not exposed as ordinary controls by this integration without dedicated write validation.

## Firmware validation

A firmware update must not be assumed to change these IDs merely because pump handling changed internally. Revalidate the mapping when a firmware release explicitly changes Local REST/Modbus variables or when a post-update variable crawl shows different point metadata.

For firmware 4.13.12, the published release notes do not describe a GP1/GP6 Local REST mapping change. The mapping above should therefore remain unchanged unless a post-update device crawl demonstrates otherwise.

## References

- NIBE Technical information, Modbus S-Series: https://www.nibe.eu/download/18.42a6470a1963dded290bb1/1746538843623/Technical%20information%20Modbus%20S-Series.pdf
- NIBE VVM S320 installer documentation: https://www.nibe.eu/en-eu/products/heat-pumps/air-water-heat-pumps/vvm-s320
- NIBE firmware version history: https://www.nibe.eu/myuplink_changelog/nibe-n.pdf
