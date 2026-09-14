# GP1 / GP6 mapping notes

## Verified VVM S320/S325 mapping

| Local REST point | Meaning | Integration status |
| ---: | --- | --- |
| `2792` | Heating circulation pump **GP1 speed** (`%`) | curated `sensor` |
| `1975` | Same GP1-labelled percentage value on another NIBE register set | not curated; still available through Complete/Individual discovery |
| `10895` | Former GP6 status candidate | **not exposed**; current VVM S320 REST API returns `Point not found` |

For VVM S320/S325 the integration therefore uses local REST point `2792` as the canonical GP1 speed value.

## Why both 1975 and 2792 exist

NIBE uses product-specific register sets. The official S-series Modbus documentation lists a GP1-labelled speed at input register `1102`, while the VVM S320/S325 register set exposes the variable-speed GP1 value at input register `1636`. The local REST API maps these to points `1975` and `2792` respectively.

Historically this integration exposed point `1975` as `heating_circulation_pump_gp1` and point `2792` as an alternative GP1 sensor. On the VVM S320 installation, however, the useful variable-speed value is `2792`. Point `1975` was observed by the user to behave only like `0/100 %`, which makes it a candidate for further investigation against the physical GP6 state, but that relationship is **not yet proven** by the current REST metadata and must not be presented as a GP6 status.

## GP6

An older API/data crawl contained point `10895` named `Pumpe: Heizungsmedium (GP6)` with values `0 = Aus` and `1 = Ein`. The current VVM S320 REST API no longer exposes that point: it is absent from the bulk `/points` response and a direct `/points/10895` request returns `Point not found`.

The integration therefore does not create a GP6 entity from point `10895` and does not perform a targeted fallback request for it.

A separate service/forced-control variable for GP6 may exist in menu 7.5.3. Service/test controls are intentionally excluded and must not be used as a substitute for a normal running-state sensor.

## Open investigation

The historical point `1975` deserves a dedicated runtime correlation test because it was previously shown as GP1 but reportedly switched only between `0 %` and `100 %`. If its transitions consistently match the physical GP6 pump while point `2792` continues to show the true variable GP1 speed, we can document that behavior separately. Until that is demonstrated, `1975` remains uncurated rather than being relabelled as GP6.

## References

- NIBE Technical information, Modbus S-Series: https://www.nibe.eu/download/18.42a6470a1963dded290bb1/1746538843623/Technical%20information%20Modbus%20S-Series.pdf
- NIBE VVM S320 installer documentation: https://www.nibe.eu/en-eu/products/heat-pumps/air-water-heat-pumps/vvm-s320
- NIBE firmware version history: https://www.nibe.eu/myuplink_changelog/nibe-n.pdf
