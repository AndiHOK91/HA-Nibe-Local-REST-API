# Changelog

Alle wesentlichen Änderungen an **NIBE Local REST** werden hier versionsweise zusammengefasst.

## 0.7.1

- Einzelpunkt-Fallback wird beim Start ohne vorhandene Punktdaten nicht mehr durch den Backoff verzögert.
- Schreibschutz für **Heizung zulassen** und **Kühlung zulassen** verschärft: Vor dem Schreiben muss der aktuelle Betriebsmodus erfolgreich neu gelesen werden.
- Bekannte Select-Werte werden auch dann korrekt zugeordnet, wenn die REST API numerische Enum-Werte als Strings liefert.
- Number-Entitäten akzeptieren nur positive Divisoren und blockieren Werte, die nicht exakt zur von NIBE vorgegebenen Schrittweite passen.
- Regressionstests für Fallback, Schreibschutz, Select-Enuums und Number-Grenzfälle erweitert.
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
