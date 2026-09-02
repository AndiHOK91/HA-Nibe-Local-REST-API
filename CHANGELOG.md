# Changelog

Alle wesentlichen Änderungen an **NIBE Local REST API** werden hier versionsweise zusammengefasst.

## 0.8.0 (in Entwicklung)

- Das lokale Branding verwendet jetzt eine kompakte quadratische Bildmarke, damit es in Home Assistant deutlich größer dargestellt wird. Die hellen Icon- und Logo-Varianten besitzen einen vollständig transparenten Hintergrund; alle Branding-Dateien liegen zusätzlich in passenden 1x-/2x-Auflösungen vor.
- Die NIBE-Geräte-ID ist jetzt fest auf `0` gesetzt und wird weder bei der Einrichtung noch in den Optionen angeboten.
- Eine explizite Authentifizierungsmethode trennt **Benutzername + Passwort** und **Authorization-Header**. Beim Methodenwechsel werden Zugangsdaten der inaktiven Methode entfernt; bestehende Einträge ohne Methodenfeld werden kompatibel anhand des vorhandenen Headers eingeordnet.
- Der Reauthentifizierungsdialog fragt nur noch die Zugangsdaten der aktiven Authentifizierungsmethode ab.
- Smart Mode und die Meldungs-/Alarm-Entität werden demselben Home-Assistant-Gerät wie die übrigen NIBE-Entitäten zugeordnet.
- Das Attribut `last_successful_poll` wurde von **REST API erreichbar** entfernt. Der Zeitpunkt bleibt coordinatorintern verfügbar, ohne bei jedem erfolgreichen Poll Recorder-Änderungen an dieser Entity zu erzeugen.
- NIBE-Einheiten werden für Home Assistant normalisiert: `%RH` → `%` und `l/min` → `L/min`; Volumenstrom erhält damit eine passende Home-Assistant-Device-Class. Die Humidity-Device-Class wird nur aus der ursprünglichen NIBE-Einheit `%RH`, nicht aus beliebigen Prozentwerten abgeleitet.
- Schreibzugriffe auf die NIBE REST API werden integrationsweit über einen gemeinsamen Lock serialisiert. Zusätzlich verwenden schreibende Plattformen `PARALLEL_UPDATES = 1`, während coordinatorbasierte Leseplattformen `PARALLEL_UPDATES = 0` verwenden.
- Ungültige Select-Optionen erzeugen jetzt einen übersetzbaren `HomeAssistantError` statt eines hart codierten englischen `ValueError`.
- Das Zusatzattribut `group` verwendet sprachneutrale Schlüssel (`system`, `heating`, `cooling`, `hot_water`, `energy`, `hydraulics`, `heat_pump`, `eev_defrost`, `ventilation`).
- Alarmtexte aus der NIBE werden bevorzugt, damit die Gerätesprache erhalten bleibt. Verifizierte deutsche Alarmtexte dienen nur bei deutscher Home-Assistant-Sprache als Fallback; andere Sprachen und unbekannte Alarme ohne Gerätetext erhalten einen sprachneutralen `Alarm <Nummer>`-Fallback.
- Regressionstests für feste Geräte-ID, Authentifizierungsmethoden, serialisierte Schreibzugriffe, Parallelitätsgrenzen, Einheitennormalisierung, Alarm-Fallbacks, Gruppen und übersetzbare Select-Fehler ergänzt.
- Legacy-Migration für alte `nibe_vvm_s320_*`-Entity-IDs entfernt. Bereits bestehende aktuelle `nibe_api_*`-Entity-IDs bleiben erhalten; für eine frische Installation wird kein exaktes Entity-ID-Präfix garantiert, da Home Assistant die IDs aus Geräte- und Entitynamen erzeugt.
- Automatische Entfernung des früheren Standalone-Sensors `last_successful_poll` aus der Entity Registry entfernt; die eigene Installation wurde bereits bereinigt.
- Nicht mehr benötigte Kompatibilitäts-Exporte `FRIENDLY_NAMES`, `OPERATING_MODE_MAP` und `ENUM_LABELS` entfernt.
- Nicht mehr verwendetes internes `POINT_BY_ID`-Lookup entfernt; `POINTS` bleibt die zentrale Definition aller NIBE-Punkte.
- Spezialschalter verwenden ihre benötigten Punktdefinitionen jetzt direkt aus `POINTS`; damit bleibt der Code nach Entfernung von `POINT_BY_ID` konsistent.
- Harte deutsche Namensüberschreibungen für die BWZ-Zeitwerte entfernt; auch diese Number-Entitäten verwenden jetzt ausschließlich die vorhandenen Home-Assistant-Übersetzungen.
- Veraltete `strings.json` entfernt. Custom Integrations laden ihre Übersetzungen direkt aus `translations/<sprache>.json`.
- Sprachabhängigen Fallbacktext `nicht auflösbar` im Reauth-Dialog durch einen neutralen Gedankenstrich ersetzt.
- Spezialschalter **Lüftung +** verwendet jetzt einen eigenen Translation Key statt eines fest im Python-Code gesetzten deutschen Namens.
- Benutzernahe Fehler beim Schreiben von Switch- und Number-Entitäten werden über Home Assistants übersetzbare `HomeAssistantError`-Mechanik ausgegeben.
- Persistent Notifications für Authentifizierungs- und Verbindungsfehler verwenden die deutsche bzw. englische Übersetzungsdatei; der Notification-Titel bleibt sprachneutral.
- Alle konfigurierten Point-Selects besitzen jetzt explizite Enum-Mappings. Der ungenutzte generische Min-/Max-Fallback für unbekannte Selects wurde entfernt und durch einen Regressionstest abgesichert.
- Redundante Hilfsfunktionen für bereits separat geprüfte Schreibfreigaben, Auth-Benachrichtigungen und den Lüftungs-Punktrefresh entfernt; die Aufrufe nutzen jetzt direkt die zugrunde liegende Logik.
- Regressionstests auf die aktuelle, sprachneutrale Select-State-Struktur umgestellt.
- Interne Setup- und Entity-Basis vereinfacht; Point-IDs, Unique IDs, Translation Keys bestehender Punkt-Entitäten und aktuelle Entity-IDs bleiben unverändert.

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
