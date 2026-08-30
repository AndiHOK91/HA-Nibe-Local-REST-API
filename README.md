# NIBE Local REST – Home Assistant Custom Integration (0.3.9)

Privates Sicherungs-Repository für die aktuelle Home-Assistant-Custom-Integration zur lokalen NIBE REST API.

## Installation

1. Den Ordner `custom_components/nibe_local` nach `/config/custom_components/nibe_local` kopieren.
2. Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste** die Integration **NIBE Local REST** hinzufügen.
4. IP-Adresse bzw. Hostname, Port, Geräte-ID und Zugangsdaten eintragen.
5. Bei einem lokalen selbstsignierten Zertifikat die SSL-Zertifikatsprüfung deaktiviert lassen.

## Aktueller Funktionsumfang

- Lokaler HTTPS-Zugriff auf die NIBE REST API
- Unterstützung für VVM S320 mit S2125
- Sensoren für Heizung, Kühlung, Brauchwasser und Verdichter
- Lüftungsmodus mit den Stufen Normal, Aus, Reduziert, Erhöht und Maximal
- Dashboard-Schalter **Lüftung +**
  - Ein: Stufe 3 = Erhöht
  - Aus: Stufe 0 = Normal
  - Aktiv bei tatsächlicher Lüftungsstufe 3 oder 4
- Dashboard-Schalter **Mehr Brauchwasser**
  - Ein: Wert 2 = einmalige Erhöhung
  - Aus: Wert 0
- Konfigurierbares Polling-Intervall
- Konfigurierbare Verzögerung für das Rücklesen nach Schaltbefehlen
- Nachträgliche Änderung von IP-Adresse, Zugangsdaten und Polling-Einstellungen
- Diagnosewerte für EEV, EVI und Enteisung
- NIBE-Branding für die Integration
- Pool-Entities sind bewusst ausgeschlossen

## Konfiguration

Die Verbindungseinstellungen können nach der Einrichtung unter
**Einstellungen → Geräte & Dienste → NIBE Local REST → Konfigurieren** geändert werden.

Einstellbar sind unter anderem:

- IP-Adresse / Hostname
- Port
- Geräte-ID
- Benutzername
- Passwort
- SSL-Zertifikatsprüfung
- Polling-Intervall
- Schalt-Poll-Verzögerung

## Version

Aktueller Sicherungsstand: **0.3.9**

## Hinweise

Dieses Repository ist derzeit privat und dient als Sicherung und Entwicklungsstand der Integration. Die Integration befindet sich noch vor Version 1.0.0 und wird weiter getestet und verfeinert.

Die Dokumentation, Versionshinweise und Commit-Beschreibungen werden in diesem Repository auf **Deutsch** geführt.
