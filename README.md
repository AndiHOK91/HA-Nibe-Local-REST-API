# NIBE Local REST – Home Assistant Custom Integration (0.3.14)

Private Home-Assistant-Custom-Integration für den lokalen Zugriff auf die NIBE REST API.

## Installation

1. Den Ordner `custom_components/nibe_local` nach `/config/custom_components/nibe_local` kopieren.
2. Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste** die Integration **NIBE Local REST** hinzufügen.
4. Hostname bzw. IP-Adresse, Port, Geräte-ID und Zugangsdaten eintragen.
5. Bei einem lokalen selbstsignierten Zertifikat die SSL-Zertifikatsprüfung deaktiviert lassen.

## Aktueller Funktionsumfang

- Lokaler HTTPS-Zugriff auf die NIBE REST API
- Unterstützung für VVM S320 mit S2125
- Sensoren für Heizung, Kühlung, Brauchwasser und Verdichter
- Diagnosewerte für EEV, EVI und Enteisung
- Lüftungsmodus mit Normal, Aus, Reduziert, Erhöht und Maximal
- Dashboard-Schalter **Lüftung +**
  - Ein schreibt Punkt 3830 auf `3` = Erhöht
  - Aus schreibt Punkt 3830 auf `0` = Normal
  - Der Schalter gilt bei tatsächlichem Modus `3` oder `4` als aktiv
  - Der optimistische Zustand bleibt erhalten, bis NIBE den neuen Modus bestätigt
- Dashboard-Schalter **Mehr Brauchwasser**
  - Ein schreibt Punkt 4564 auf `2` = einmalige Erhöhung
  - Aus schreibt Punkt 4564 auf `0`
  - Punkt 4030 wird nur gelesen und ist der maßgebliche Zustand
  - Solange Punkt 4030 größer als `0` Minuten ist, gilt Mehr Brauchwasser als aktiv
  - Beim Ein- und Ausschalten verhindert eine verzögerte Bestätigung ein kurzes Zurückspringen der Anzeige
- **Zeit bis Enteisung**: Werte von Punkt 840 größer als 720 Minuten werden als 0 Minuten dargestellt
- Konfigurierbares Polling-Intervall
- Konfigurierbare Verzögerung für das Rücklesen nach Schaltbefehlen
- Nachträgliche Änderung von Verbindung, Zugangsdaten und Polling-Einstellungen
- NIBE-Branding für die Integration
- Pool-Entities sind bewusst ausgeschlossen

## Konfiguration

Die Verbindungseinstellungen können nach der Einrichtung unter **Einstellungen → Geräte & Dienste → NIBE Local REST → Konfigurieren** geändert werden.

Einstellbar sind unter anderem Hostname/IP-Adresse, Port, Geräte-ID, Benutzername, Passwort, SSL-Zertifikatsprüfung, Polling-Intervall und Schalt-Poll-Verzögerung.

## Version

Aktueller Entwicklungs- und Sicherungsstand: **0.3.14**

## Änderungen seit 0.3.9

### 0.3.10

- Zustand von **Mehr Brauchwasser** an Punkt 4030 gekoppelt.
- Punkt 840 **Zeit bis Enteisung**: Werte größer 720 Minuten werden als 0 dargestellt.

### 0.3.11

- Gezielte Rücklesung von Punkt 3830 für **Lüftung +** korrigiert.

### 0.3.12

- **Lüftung +** behält den optimistischen Zustand, bis NIBE den neuen Lüftungsmodus bestätigt.

### 0.3.13

- Schreibversuch auf Punkt 4030 beim Ausschalten von **Mehr Brauchwasser** entfernt, da die NIBE-Firmware diesen mit HTTP 400 ablehnt.

### 0.3.14

- **Mehr Brauchwasser** bleibt nach dem Ausschalten optisch Aus, bis Punkt 4030 tatsächlich 0 Minuten meldet. Zwischenzeitliche Polls mit dem alten Minutenwert führen nicht mehr zum Zurückspringen auf Ein.

## Hinweise

Dieses Repository ist derzeit privat und dient als Sicherung und Entwicklungsstand der Integration. Die Integration befindet sich noch vor Version 1.0.0 und wird weiter getestet und verfeinert.

Dokumentation, Versionshinweise und Commit-Beschreibungen werden in diesem Repository auf **Deutsch** geführt.
