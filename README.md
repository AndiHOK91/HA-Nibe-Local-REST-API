# NIBE Local REST – Home Assistant Custom Integration (0.3.16)

Private Home-Assistant-Custom-Integration für die lokale NIBE REST API, entwickelt und getestet für eine VVM S320 mit S2125.

## Autoren

- AndiO91
- ChatGPT (OpenAI) – Unterstützung bei Entwicklung, REST-API-Auswertung und Home-Assistant-Integration

## Installation

1. Den Ordner `custom_components/nibe_local` nach `/config/custom_components/nibe_local` kopieren.
2. Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste** die Integration **NIBE Local REST** hinzufügen.
4. Host/IP-Adresse, Port, Geräte-ID und Zugangsdaten eintragen.
5. Bei einem lokal selbstsignierten Zertifikat die SSL-Zertifikatsprüfung deaktiviert lassen.

## Funktionsumfang

- Lokaler HTTPS-Zugriff auf die NIBE REST API
- Sensoren für Heizung, Kühlung, Brauchwasser, Hydraulik und S2125
- Verdichter-, EEV-, EVI- und Enteisungsdiagnose
- Lüftungsmodus mit Normal, Aus, Reduziert, Erhöht und Maximal
- Dashboard-Schalter **Lüftung +**
  - Ein schreibt `3830 = 3` (Erhöht)
  - Aus schreibt `3830 = 0` (Normal)
  - Aktiv bei tatsächlich gemeldetem Modus `3` oder `4`
  - Optimistische Anzeige bis zur Bestätigung durch die NIBE
- Dashboard-Schalter **Mehr Brauchwasser**
  - Ein schreibt `4564 = 2`
  - Aus schreibt `4564 = 0`
  - Tatsächlicher Zustand richtet sich nach `4030` (verbleibende Minuten)
  - Anzeige bleibt beim Schalten stabil, bis die NIBE den neuen Zustand bestätigt
- **Nachtabsenkung** über Punkt `4040`
- **Starttemperatur Nachtabsenkung** über Punkt `4041`
- **Aktive Meldungen** als read-only Alarm-Entity mit Alarmnummern und Detailattributen
- Werte von **Zeit bis Enteisung** über 720 Minuten werden als 0 Minuten dargestellt
- Konfigurierbares Polling-Intervall
- Konfigurierbare Verzögerung für das Rücklesen nach Schaltbefehlen
- NIBE-Branding
- Pool-Entities sind bewusst ausgeschlossen

## Alarmmeldungen

Die Entity **Aktive Meldungen** zeigt die Anzahl aktiver Meldungen. Zusätzlich stehen folgende Attribute zur Verfügung:

- `alarm_ids` – erkannte NIBE-Alarmnummern
- `alarm_summary` – kompakte Zusammenfassung aus Alarmnummer und Text
- `alarms` – normalisierte Detailinformationen wie Beschreibung, Schweregrad, Zeit und Quelle

Die Alarmfunktion ist bewusst **nur lesend**. Es wird keine Reset- oder Quittierfunktion angeboten.

## Lüftungssteuerung

Punkt `3830` wird für den Ventilationsmodus verwendet. Für die Nachtabsenkung sind zusätzlich die schreibbaren Punkte `4040` und `4041` integriert. Einheit, Skalierung, Min-/Max-Werte und Schreibbarkeit werden soweit möglich aus den REST-Metadaten der NIBE übernommen.

## Version

Aktueller Stand: **0.3.16**

## Hinweise

Dieses Repository ist privat und dient als Sicherungs- und Entwicklungsstand der Integration. Die Integration befindet sich noch vor Version 1.0.0 und wird weiter auf der realen Anlage getestet.

Dokumentation, Versionshinweise und Commit-Beschreibungen werden auf **Deutsch** geführt.
