# Changelog

Alle wesentlichen Änderungen an **NIBE Local REST API** werden hier versionsweise zusammengefasst.

## 0.8.0 (in Entwicklung)

- Legacy-Migration für alte `nibe_vvm_s320_*`-Entity-IDs entfernt. Die aktuelle `nibe_api_*`-Struktur gilt ab 0.8.0 als feste Basis.
- Automatische Entfernung des früheren Standalone-Sensors `last_successful_poll` aus der Entity Registry entfernt; die eigene Installation wurde bereits bereinigt.
- Nicht mehr benötigte Kompatibilitäts-Exporte `FRIENDLY_NAMES`, `OPERATING_MODE_MAP` und `ENUM_LABELS` entfernt.
- Nicht mehr verwendetes internes `POINT_BY_ID`-Lookup entfernt; `POINTS` bleibt die zentrale Definition aller NIBE-Punkte.
- Regressionstests auf die aktuelle, sprachneutrale Select-State-Struktur umgestellt.
- Interne Setup- und Entity-Basis vereinfacht; Point-IDs, Unique IDs, Translation Keys und aktuelle Entity-IDs bleiben unverändert.

## 0.7.5

- Deutsche und englische Entitätsnamen systematisch vereinheitlicht: Temperaturen, Pumpen, Verdichter, Lüftung, Brauchwasser sowie EEV-/Abtauwerte verwenden jetzt konsistente und besser lesbare Bezeichnungen.
- Geräte- und Einrichtungs-Fallback auf **NIBE API** neutralisiert, da der lokale `/devices/{id}`-Endpunkt nicht auf allen Anlagen einen Produktnamen liefert.
- Bereits registrierte, automatisch erzeugte Entity-IDs werden beim Setup auf sprachneutrale IDs im Schema `<domain>.nibe_api_<translation_key>` migriert. Beispielsweise wird `sensor.nibe_vvm_s320_aktuelle_aussenlufttemperatur_bt1` zu `sensor.nibe_api_outdoor_temperature_bt1`.
- Die Entity-ID-Migration basiert auf den unveränderten Unique IDs bzw. NIBE-Punktnummern. Benutzerdefinierte Entity-IDs mit einem anderen Präfix werden nicht verändert; bei Namenskollisionen wird die vorhandene Entity-ID beibehalten und eine Warnung protokolliert.
- Repository-Verweise im Manifest auf **AndiO91/HomeAssistant-Local-REST-API** aktualisiert.

## 0.7.4

- Integrationsname in HACS, Home Assistant, Übersetzungen und Dokumentation auf **NIBE Local REST API** vereinheitlicht.
- Entitätsnamen werden über Home-Assistant-Übersetzungen statt fest im Python-Code gesetzter deutscher Namen bereitgestellt.
- Deutsche und englische Übersetzungen für Sensoren, Binärsensoren, Schalter, Number-, Select- und Time-Entitäten ergänzt.
- Diagnose-Entitäten und Smart Mode vollständig in die Übersetzungsstruktur aufgenommen.
- Zustände von Betriebspriorität, Betriebsmodus und Abtauanforderung auf stabile, übersetzbare `snake_case`-Werte umgestellt.
- Select-Zustände für Betriebsmodus, Lüftung und Brauchwasserbedarf auf stabile, übersetzbare Werte umgestellt.
- Fehlende deutsche Übersetzung für `already_configured` ergänzt.
- **Letzter erfolgreicher Poll** wird nicht mehr als eigener Timestamp-Sensor angelegt, sondern als Attribut `last_successful_poll` des Diagnose-Binärsensors **REST API erreichbar** bereitgestellt. Dadurch erzeugt jeder erfolgreiche Poll keinen eigenen Eintrag mehr im Aktivitätenprotokoll.
- Hochauflösende `icon@2x.png`- und `dark_icon@2x.png`-Branding-Dateien ergänzt.

## 0.7.3

- Lokale Light-/Dark-Branding-Dateien für Home Assistant ergänzt und Dateinamen vereinheitlicht.
- Integrationsversion für die HACS-Veröffentlichung angehoben.

## 0.7.2

- Wiederholte Authentifizierungsfehler erzeugen die Persistent Notification und die zugehörige Host-/IP-Auflösung nur einmal pro zusammenhängender Störung; nach erfolgreicher Kommunikation kann eine neue Störung wieder gemeldet werden.
- Nur aus Leerzeichen bestehende Passwort- oder Authorization-Header-Eingaben gelten als leer und behalten den gespeicherten Wert bei; echte nichtleere Eingaben werden unverändert übernommen.
- Regressionstests für Auth-Benachrichtigungen und den Umgang mit Zugangsdaten erweitert.
- Integrationslogo unter `docs/logo.png` ergänzt.

## 0.7.1

- Einzelpunkt-Fallback wird beim Start ohne vorhandene Punktdaten nicht mehr durch den Backoff verzögert.
- Schreibschutz für **Heizung zulassen** und **Kühlung zulassen** verschärft: Vor dem Schreiben muss der aktuelle Betriebsmodus erfolgreich neu gelesen werden.
- Bekannte Select-Werte werden auch dann korrekt zugeordnet, wenn die REST API numerische Enum-Werte als Strings liefert.
- Number-Entitäten akzeptieren nur positive Divisoren und blockieren Werte, die nicht exakt zur von NIBE vorgegebenen Schrittweite passen.
- Regressionstests für Fallback, Schreibschutz, Select-Enums und Number-Grenzfälle erweitert.
- GitHub Actions prüft zusätzlich JSON-Dateien und Python-Syntax.
- CI-Matrix testet gegen Home Assistant 2024.12.0 und die jeweils aktuelle Home-Assistant-Version.

## 0.7.0

- Diagnose-Entitäten für **REST API erreichbar**, **Einzelpunkt-Fallback aktiv**, **Letzter erfolgreicher Poll** und **Letzter Verbindungsfehler** ergänzt.
- Diagnosewerte bleiben auch bei Verbindungsproblemen sichtbar, damit Störungen besser nachvollzogen werden können.

## 0.6.1

- Reauthentifizierungsdialog um Gerätename, konfigurierten Host und aufgelöste IP-Adresse erweitert.
- Persistent Notifications bei abgelehnten Zugangsdaten und länger anhaltenden REST-API-Verbindungsfehlern ergänzt.
- Verbindungsbenachrichtigung erscheint erst nach zwei Minuten durchgehender Störung und wird nach erfolgreicher Wiederherstellung automatisch entfernt.
- Fehlerhafte Base64-Markup-Darstellung in den Übersetzungen korrigiert.

## 0.6.0

- Fallback für nicht auswertbare `/points`-Antworten mit Backoff 30/60/120 Sekunden eingeführt.
- Bereits bekannte Werte bleiben bei unvollständigen Einzelpunkt-Fallbacks erhalten.
- Reauthentifizierung und sicherer Umgang mit gespeicherten Zugangsdaten verbessert.
- Gezieltes Nachladen einzelner Punkte nach Schreibvorgängen statt vollständigem Coordinator-Refresh.
- Erste Regressionstests und GitHub-Actions-Testworkflow ergänzt.
- Mindestversion auf Home Assistant 2024.12.0 festgelegt.
