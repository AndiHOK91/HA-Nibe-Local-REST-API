<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/nibe_local/brand/dark_logo.png">
    <source media="(prefers-color-scheme: light)" srcset="custom_components/nibe_local/brand/logo.png">
    <img alt="NIBE Local REST API – Home Assistant Custom Integration" src="custom_components/nibe_local/brand/logo.png" width="760">
  </picture>
</p>

# NIBE Local REST API – Home Assistant Custom Integration

> 🏠 **Lokal** · 🔒 **Sicherheitsorientiert** · ☁️ **ohne Cloud-Zwang** · 🌡️ **Heizung** · ❄️ **Kühlung** · 💧 **Brauchwasser** · 🌬️ **Lüftung**

Diese Custom Integration bindet eine NIBE-S-Series-Anlage direkt über die **lokale REST API** in Home Assistant ein. Für normales Auslesen und die ausdrücklich unterstützten Steuerfunktionen ist keine Verbindung zu myUplink erforderlich.

Die Integration wurde im realen Betrieb mit **VVM S320, S2125 und ERS S40-400** entwickelt und getestet. Andere S-Series-Konfigurationen können ebenfalls funktionieren, sind aber nicht automatisch vollständig verifiziert.

Aktuelle Integrationsversion: **0.10.1 Beta (Prerelease)**

> [!WARNING]
> Die mit v0.10.x eingeführte **Statistikmigration** ist **experimentell und noch nicht auf einer realen Home-Assistant-Installation getestet**. Vor einer Verwendung sollte ein reguläres Home-Assistant-Backup vorhanden sein. Die integrierte Sicherungsfunktion ersetzt kein vollständiges Home-Assistant-Systembackup.

---

## ✨ Funktionsumfang

Unterstützt werden unter anderem:

- Außen-, Vorlauf-, Rücklauf-, Raum-, Brauchwasser- und Lüftungstemperaturen
- Heizungswerte, Gradminuten und berechnete Vorlauftemperaturen
- Kühlstatus, Kühlgradminuten und Kühlfreigabe
- Brauchwasserwerte, Mehr Brauchwasser und Brauchwasserzirkulation
- Verdichterstatus, Frequenz, Laufzeiten, Leistung und Kältekreiswerte
- Pumpen-, Hydraulik- und Ventilatorwerte
- Lüftungsmodus, Luftfeuchtigkeit und Lüftungstemperaturen
- EEV-/EVI-, Kältekreis- und Abtauwerte
- Energie- und Leistungswerte
- Alarm- und Meldungsinformationen
- ausdrücklich freigegebene Schreibfunktionen über `switch`, `select` und `number`
- read-only `time`-Entitäten für bekannte Zeitpunkte, deren Schreiben durch die NIBE-Firmware/API nicht zuverlässig unterstützt wird
- Diagnoseinformationen für API-Erreichbarkeit, Fallback und Verbindungsfehler
- datenschutzorientierte Standarddiagnose sowie explizit anforderbare erweiterte Diagnosedaten
- automatische Erkennung optionaler Anlagenhardware in Einrichtung und Optionen
- experimentelle Vorschau und Migration vorhandener Home-Assistant-Langzeitstatistiken auf REST-Sensoren
- automatische, standardmäßig aktivierte Statistik-Sicherung vor einem Import
- Auflistung älterer Statistik-Backups und read-only Restore-Vorschau

---

## 🧩 Entitätsprofile

Nach erfolgreicher Verbindung liest die Integration die tatsächlich verfügbaren REST-Punkte des Geräts ein.

| Profil | Zweck | Verhalten |
|---|---|---|
| **Standard** | Typische Home-Assistant-Nutzung | Kuratierter Kernumfang für Temperaturen, Brauchwasser, Energie, Verdichter und wichtige Betriebswerte |
| **Erweitert** | Ausführliche Anlagenanalyse | Vollständig kuratierter, der Integration bekannter `POINTS`-Umfang einschließlich detaillierter Diagnose- und Servicewerte |
| **Komplett** | Maximale Sichtbarkeit | Alle von der lokalen API gemeldeten Punkte; unbekannte Punkte ausschließlich als Read-only-Sensor |
| **Individuell** | Volle Auswahlkontrolle | Der Nutzer wählt die gewünschten Variable-IDs selbst aus |

Das frühere Profil **Minimal** ist nicht mehr Bestandteil der Integration.

Unbekannte Punkte bleiben auch dann **Read-only**, wenn die lokale REST API `isWritable=true` meldet. Schreibfunktionen werden nur für verstandene und explizit abgesicherte Punkte angeboten.

### Automatische Hardware-Erkennung

Optionale Ausstattung wird soweit zuverlässig möglich aus den normalen lokalen REST-Punkten erkannt. Dazu gehören derzeit insbesondere:

- Energiezähler BE6
- Energiezähler BE7
- Lüftungsanlage / ERS
- Brauchwasserzirkulation

Die **priorisierte externe Zusatzheizung** wird bewusst nicht automatisch allein aus Punkt 1186 abgeleitet, weil dessen Vorhandensein keine sichere Aussage über tatsächlich installierte Hardware erlaubt.

Bei der ersten Einrichtung wird erkannte Hardware mit **„(erkannt)“** gekennzeichnet und vorausgewählt.

Im späteren Optionen-Dialog wird zusätzlich mit dem zuletzt gespeicherten Erkennungsstand verglichen:

- **(erkannt – bereits hinzugefügt)**: aktuell erkannt und bereits aktiviert
- **(erkannt – neu hinzugefügt)**: seit der letzten Prüfung neu erkannt; wird automatisch vorausgewählt
- **(erkannt – nicht hinzugefügt)**: aktuell erkannt, aber zuvor bewusst nicht aktiviert; wird nicht erneut automatisch aktiviert
- **(nicht mehr erkannt – weiterhin hinzugefügt)**: aktuell nicht mehr erkannt, bleibt aus Sicherheitsgründen aber aktiviert, bis der Nutzer es bewusst abwählt
- **(erkannt)**: aktueller Fund ohne ausreichend sichere frühere Vergleichsbasis

Dadurch kann beispielsweise ein später eingebauter BE7 beim nächsten Öffnen der Optionen automatisch erkannt und vorausgewählt werden, ohne bewusst abgewählte Hardware bei jedem Öffnen wieder zu aktivieren.

---

## 🛡️ Schreibzugriffe und Sicherheitsmodell

Die Integration verwendet ein Allowlist-Prinzip. Schreibbar sind nur Punkte, deren Bedeutung und zulässige Werte bekannt und ausdrücklich implementiert sind.

Alle schreibenden REST-Aufrufe werden integrationsweit serialisiert. Nach einem Schreibbefehl wird der betroffene Punkt gezielt neu gelesen. Für einzelne bekannte Schalter, bei denen die REST API unmittelbar nach einem erfolgreichen Schreibvorgang noch einen alten Wert liefern kann, wird zusätzlich mit einem verzögerten gezielten Kontrollabruf gearbeitet.

### Heizung und Kühlung

Die Schalter **Heizung zulassen** und **Kühlung zulassen** werden unmittelbar vor dem Schreiben gegen den aktuellen Betriebsmodus geprüft.

| Betriebsmodus | Heizung zulassen | Kühlung zulassen |
|---|---:|---:|
| Auto | blockiert | blockiert |
| Manuell | schreiben erlaubt | schreiben erlaubt |
| Nur Zusatzheizung | schreiben erlaubt | blockiert |
| unbekannt / nicht sicher lesbar | blockiert | blockiert |

Der AUX-Schalter **Zusatzheizung im Heizbetrieb zulassen** ist davon unabhängig und wird nicht über diese Betriebsmodus-Sperre blockiert.

### Zeitwerte

Bekannte NIBE-Zeitpunkte werden als `time`-Entitäten dargestellt, wenn ihre REST-Metadaten dies sinnvoll erlauben. Das Schreiben solcher Zeitwerte ist derzeit bewusst blockiert, weil sowohl die lokale REST API als auch die getestete Modbus-Schnittstelle entsprechende Schreibversuche nicht zuverlässig akzeptieren. Die Entität bleibt damit read-only, statt einen scheinbar erfolgreichen, tatsächlich aber nicht ausgeführten Schreibvorgang anzubieten.

---

## 💧 Brauchwasser und Brauchwasserzirkulation

Unterstützt werden – abhängig von Gerät und Profil – unter anderem:

- Brauchwasser oben BT7
- Brauchwasserbereitung BT6
- Brauchwasserstart BT5
- Brauchwasseraustritt BT70
- Brauchwasserbedarf
- Mehr Brauchwasser
- periodische Brauchwassererhöhung
- Brauchwasserzirkulation GP11
- Betriebs- und Stillstandszeit der Brauchwasserzirkulation
- drei über die lokale REST API verfügbare BWZ-Zeitperioden mit Start- und Stoppzeit

Nicht über die lokale REST API exponierte BWZ-Punkte werden nicht künstlich ergänzt.

---

## ⚙️ Verdichter, Außeneinheit und Abtauung

Je nach Gerät und Profil stehen unter anderem zur Verfügung:

- Verdichterstatus und Verdichterfrequenz
- Verdichterstarts und Laufzeiten
- Rücklauf und Kondensatorvorlauf
- Heißgas-, Flüssigkeits- und Sauggastemperaturen
- Verdampfertemperaturen
- Hoch-/Niederdruckwerte
- Ventilatordrehzahl
- Schutz- und Alarmzustände
- Abtauzustände und Zeit bis Enteisung
- EEV-/EVI-Überhitzung, Sollwerte und Öffnungsgrade

### Sonderwerte

NIBE kann bei einzelnen Integer-Punkten Grenzwerte des zugrunde liegenden Datentyps als Sonderzustand liefern.

- erkannte ungültige Grenzwerte wie `-32768` bei `s16` werden nicht als reale Messwerte veröffentlicht
- bei **Punkt 840 – Zeit bis Enteisung** wird `65535` nicht als `65535 min` und auch nicht künstlich als `0 min` dargestellt; die Entity bleibt erreichbar und der numerische Zustand bleibt für diesen Sonderfall unbekannt
- die frühere Heuristik `>720 min → 0` wurde vollständig entfernt
- **Punkt 2022 – Current status** wird wegen seines kodierten `u32`-Charakters als Diagnoseentity behandelt
- **Punkt 22268 – Letzte Enteisung** verwendet Enum-Bezeichnungen nur dann, wenn die lokale REST API diese in der Punktbeschreibung liefert; unbekannte Bedeutungen werden nicht geraten
- EEV-Öffnungswerte wie Punkt 849 werden unverändert entsprechend den REST-Metadaten dargestellt und nicht willkürlich als Prozentwert umgerechnet

---

## 🚨 Diagnose

### Diagnose-Entitäten

Zusätzlich stehen Diagnoseinformationen bereit, darunter:

- **REST API erreichbar**
- **Einzelpunkt-Fallback aktiv**
- **Letzter Verbindungsfehler**
- aktive Meldungen/Alarme

### Standarddiagnose

Die normale Home-Assistant-Diagnose ist datenschutzorientiert und enthält keine Zugangsdaten. Erweiterte aktuelle Messwerte und Recorder-Historie werden nicht automatisch in jede Standarddiagnose aufgenommen.

### Erweiterte Diagnosedaten

Über die Aktion `nibe_local.export_extended_diagnostics` können bewusst erweiterte Diagnosedaten angefordert werden. Dabei lässt sich die Recorder-Historie auf **1, 3, 5 oder 7 Tage** begrenzen; Standard ist **1 Tag**.

Der erweiterte Export enthält für aktivierte NIBE-Punkte – soweit vorhanden – unter anderem:

- Variable-ID
- REST-Titel und REST-Beschreibung
- Einheit
- Datentyp und Variablengröße
- Divisor und Dezimalstellen
- Schreibbarkeitskennzeichen
- aktuellen Rohwert
- aktuell von der Integration berechneten skalierten Wert
- `isOk`-Status
- Kennzeichnung erkannter Integer-Sentinelwerte
- daraus abgeleitete Gültigkeit des aktuellen Werts
- die ausdrücklich ausgewählte Recorder-Historie

Aus Datenschutz- und Sicherheitsgründen werden Zugangsdaten nicht exportiert. Erweiterte Diagnosedaten können jedoch Mess- und Einstellwerte enthalten und sollten vor öffentlicher Weitergabe geprüft werden.

---

## 🧪 Experimentelle Statistikmigration

> [!CAUTION]
> **Experimentell / noch nicht real getestet:** Die Statistikmigration wurde mit Regressionstests und gegen mehrere Home-Assistant-Versionen entwickelt, aber noch nicht auf einer produktiven Home-Assistant-Recorder-Datenbank praktisch erprobt. Verwende sie zunächst nur mit besonderer Vorsicht.

Ziel der Funktion ist es, vorhandene **Langzeitstatistiken** eines bisherigen Sensors – zum Beispiel aus einer Modbus-Integration – auf den entsprechenden Sensor dieser REST-Integration zu übernehmen, ohne bereits vorhandene REST-Statistiken zu überschreiben.

### Sicherheitsprinzip

Die Migration ist absichtlich mehrstufig aufgebaut:

1. **Vorschau** der Quelle und des REST-Ziels
2. Prüfung von Einheit, Statistiktyp, Metadaten, vorhandenen Zeiträumen und Überschneidungen
3. optionaler Import ausschließlich fehlender Stundenwerte
4. standardmäßig vorherige Sicherung der Ziel-Langzeitstatistik
5. vorhandene Zielzeitpunkte werden nicht überschrieben
6. kein direkter SQL-/SQLite-/MariaDB-/PostgreSQL-Zugriff durch die Integration

### Verfügbare Aktionen

#### `nibe_local.preview_statistics_migration`

Read-only-Vorschau für ein ausgewähltes Sensorpaar. Es werden keine Recorder-Daten verändert.

Die Antwort enthält unter anderem:

- Quell- und Zielsensor
- vorhandene Langzeitstatistik-Metadaten
- Anzahl und Zeitraum der Quell- und Zielstatistiken
- bereits vorhandene Überschneidungen
- voraussichtlich importierbare Stundenwerte
- Kompatibilitätswarnungen

#### `nibe_local.import_statistics_migration`

**Experimentelle Schreibaktion. Noch nicht real getestet.**

Importiert ausschließlich fehlende stündliche Langzeitstatistiken. Bereits vorhandene Zielzeitpunkte werden übersprungen.

Optionen:

- `source_entity_id`: bisheriger Quellsensor
- `target_entity_id`: REST-Zielsensor
- `create_backup`: Sicherung vor dem Import; **standardmäßig aktiviert**, kann bewusst deaktiviert werden

Wenn die Sicherung aktiviert ist und nicht erstellt werden kann, wird der Import abgebrochen.

### Statistik-Backup

Das integrierte Backup ist **kein vollständiges Home-Assistant-Systembackup**. Es ist ein gezielter JSON-Snapshot für die Statistikmigration und wird unter `nibe_local_backups` im Home-Assistant-Konfigurationsverzeichnis gespeichert.

Gesichert werden insbesondere:

- Quell- und Zielsensor
- Statistik-Metadaten
- die vor dem Import vorhandene Ziel-Langzeitstatistik
- die Zeitpunkte, die beim anschließenden Import hinzugefügt werden sollen

Jede Sicherung erhält einen eigenen Zeitstempel; ältere Sicherungen werden nicht automatisch überschrieben.

#### `nibe_local.list_statistics_backups`

Listet alle vorhandenen, von der Integration erzeugten Statistik-Backups auf. Die neuesten Sicherungen erscheinen zuerst. Beschädigte oder nicht lesbare Backup-Dateien werden separat gemeldet.

#### `nibe_local.preview_statistics_restore`

Read-only-Prüfung eines ausgewählten älteren Backups. Es findet **keine tatsächliche Wiederherstellung** statt.

Die Vorschau vergleicht den damaligen Zustand mit der heute vorhandenen Zielstatistik und zeigt unter anderem:

- ursprünglich gesicherte Zielwerte
- damals geplante Importwerte
- aktuell noch vorhandene importierte Zeitpunkte
- inzwischen fehlende ursprüngliche Werte
- seitdem neu entstandene bzw. nicht zum damaligen Import gehörende Werte
- `safe_to_restore`
- konkrete Blockierungsgründe

Die Restore-Bewertung arbeitet **fail-closed**: Sobald ein Zustand nicht eindeutig sicher bewertet werden kann, wird eine automatische Wiederherstellung blockiert.

### Warum es noch keine automatische Restore-Aktion gibt

Home Assistant stellt eine unterstützte API zum Importieren von Langzeitstatistiken bereit, aber derzeit keinen ebenso sauberen öffentlichen Gegenpart zum gezielten Löschen nur bestimmter einzelner importierter Stundenwerte. Ein vollständiges Löschen und anschließender Neuaufbau der Zielstatistik wäre für das hier verfolgte Ziel maximaler Datensicherheit zu invasiv.

Deshalb existieren derzeit bewusst nur Backup, Backup-Liste und Restore-Vorschau. Eine echte Restore-Aktion soll erst ergänzt werden, wenn die betroffenen importierten Zeitpunkte sicher und ohne Gefährdung später entstandener legitimer Recorder-Daten zurückgesetzt werden können.

---

## 🔐 Authentifizierung und TLS

Unterstützte Authentifizierungsmethoden:

- Benutzername + Passwort
- vollständiger Authorization-Header

Die lokale REST API verwendet häufig ein selbstsigniertes Zertifikat. Die TLS-Zertifikatsprüfung kann deshalb deaktiviert werden. Wenn eine vertrauenswürdige Zertifikatskette verfügbar ist, sollte die Prüfung aktiviert bleiben.

---

## 🌐 Kommunikation und Robustheit

Im Normalbetrieb werden Werte gesammelt über den lokalen `/points`-Endpunkt gelesen. Kann eine Sammelantwort nicht sinnvoll verwendet werden, kann die Integration auf Einzelpunktabfragen zurückfallen.

Weitere Schutzmechanismen:

- REST-Antworten auf maximal 4 MiB begrenzt
- maximale JSON-Verschachtelungstiefe 64
- iterative Normalisierung statt unbegrenzter Rekursion
- Backoff beim vollständigen Einzelpunkt-Fallback
- serialisierte Schreibzugriffe
- technische Authentifizierungsfehler erzeugen keine dauerhafte Benachrichtigungsflut

Die Laufzeitintegration verwendet ausschließlich die lokale REST API.

---

## ✅ Voraussetzungen

- mindestens **Home Assistant 2024.12.0**
- NIBE S-Series-Steuerung mit lokaler REST API
- empfohlene aktuelle S-Series-Firmware
- lokale Erreichbarkeit von Home Assistant zur NIBE
- standardmäßig HTTPS auf Port **8443**

Die lokale REST API muss direkt an der NIBE-Steuerung unter **Menü 7 → Service → 7.5.15 – Lokale REST API** aktiviert und mit Zugangsdaten eingerichtet sein.

---

## 🧩 Installation

### Manuell

1. `custom_components/nibe_local` nach `/config/custom_components/nibe_local` kopieren.
2. Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen** öffnen.
4. **NIBE Local REST API** auswählen.

### HACS

Wenn das Repository als Custom Repository in HACS eingebunden ist, kann die Integration darüber installiert und aktualisiert werden. Bei **v0.10.1** handelt es sich um ein **Prerelease/Beta**.

### Einrichtungsablauf

1. Host/IP-Adresse und Port eingeben.
2. Authentifizierungsmethode wählen.
3. Zugangsdaten eingeben.
4. TLS-Zertifikatsprüfung festlegen.
5. Polling-Einstellungen wählen.
6. Verbindung prüfen.
7. Verfügbare REST-Punkte laden.
8. **Standard / Erweitert / Komplett / Individuell** auswählen.
9. Automatisch erkannte Anlagenoptionen prüfen und bei Bedarf manuell korrigieren.
10. Benennung auswählen.
11. Bei **Individuell** die gewünschten Variable-IDs auswählen.
12. Entitätsübersicht prüfen.
13. Mit **OK** anwenden.

Die API-Geräte-ID wird intern fest als `0` verwendet.

---

## 🧪 Entwicklung und Tests

GitHub Actions prüft die Integration gegen:

- **Home Assistant 2024.12.0**
- **Home Assistant 2026.9.1**
- eine aktuelle Home-Assistant-Version (`latest`)

Die Regressionstests decken unter anderem API-Normalisierung, Authentifizierung, Schreibschutz, Profile, Hardware-Erkennung, Diagnose-Datenschutz, Sentinelwerte, Abtau-Sonderzustände sowie die Schutzlogik für Statistikmigration, Backups und Restore-Vorschau ab.

Die vorhandenen automatisierten Tests ersetzen ausdrücklich **keinen realen Migrationstest auf einer produktiven Recorder-Datenbank**.

---

## ⚠️ Grenzen

Nicht automatisch unterstützt werden:

- unbekannte schreibbare Punkte als generische Steuerung
- automatisches Erraten unbekannter Enum-Semantik
- automatisches Freischalten unbekannter Service-/Installerparameter
- Alarmquittierung oder Alarmreset
- myUplink-Cloudfunktionen
- generisches Schreiben von NIBE-Zeitwerten
- Migration detaillierter Rohzustände aus der normalen Recorder-Historie; die experimentelle Migration bezieht sich auf Langzeitstatistiken
- automatische Wiederherstellung eines Statistikimports, solange Home Assistant keine ausreichend sichere selektive Recorder-API dafür bereitstellt

Die tatsächlich verfügbaren Variablen hängen von Modell, angeschlossenen Modulen, Firmware und Anlagenkonfiguration ab.

---

## ⚖️ Projektstatus und Haftung

Diese Integration ist ein **inoffizielles Community-Projekt** und steht in keiner Verbindung zu NIBE. Sie befindet sich weiterhin vor Version 1.0 und wird auf einer realen Anlage weiterentwickelt und getestet.

**v0.10.1 ist eine Beta-/Prerelease-Version.** Insbesondere die Statistikmigration ist experimentell und bisher nicht praktisch auf einer realen Home-Assistant-Recorder-Datenbank verifiziert.

Die Software wird ohne Gewährleistung oder Garantie bereitgestellt. Die Nutzung erfolgt auf eigene Gefahr. Bei sicherheitsrelevanten Funktionen sind im Zweifel die Anzeigen und Einstellungen am Gerät sowie die offizielle Herstellerdokumentation maßgeblich.

---

## 👥 Autoren

- AndiHOK91
- ChatGPT (OpenAI) – Unterstützung bei Entwicklung, REST-API-Auswertung, Tests und Home-Assistant-Integration
