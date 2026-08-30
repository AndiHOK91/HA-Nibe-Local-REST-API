# NIBE Local REST – Home Assistant Custom Integration (0.3.9)

Private backup repository for the current Home Assistant custom integration for the NIBE Local REST API.

## Installation

Copy `custom_components/nibe_local` to `/config/custom_components/nibe_local`, restart Home Assistant, then add **NIBE Local REST** under **Settings → Devices & services**.

## Current features

- Local HTTPS REST API access to NIBE VVM S320 / S2125
- Heating, cooling, hot water and compressor sensors
- Ventilation mode control
- `Lüftung +` dashboard switch
- `Mehr Brauchwasser` one-time boost switch
- Configurable polling and command verification delay
- Reconfigure host, credentials and polling settings after setup
- Diagnostics for EEV/EVI and defrost values
- Local NIBE brand assets
- Pool entities intentionally excluded

## Version

Current backup: **0.3.9**

The detailed development changelog is stored in `CHANGELOG.md`.
