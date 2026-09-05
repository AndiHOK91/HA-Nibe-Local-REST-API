<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/nibe_local/brand/dark_logo.png">
    <source media="(prefers-color-scheme: light)" srcset="custom_components/nibe_local/brand/logo.png">
    <img alt="NIBE Local REST API – Home Assistant Custom Integration" src="custom_components/nibe_local/brand/logo.png" width="760">
  </picture>
</p>

# NIBE Local REST API – Home Assistant Custom Integration

> 🏠 **Lokal** · 🔒 **Sicherheitsorientiert** · ☁️ **ohne Cloud-Zwang** · 🌡️ **Heizung** · ❄️ **Kühlung** · 💧 **Brauchwasser** · 🌬️ **Lüftung**

Diese Custom Integration bindet eine NIBE-S-Series-Anlage über die **lokale REST API** direkt in Home Assistant ein. Für das normale Auslesen und die ausdrücklich unterstützten Steuerfunktionen ist keine Verbindung zu myUplink erforderlich.

Die Integration wurde im realen Betrieb mit **VVM S320, S2125 und ERS S40-400** entwickelt und getestet. Andere S-Series-Konfigurationen können ebenfalls funktionieren, sind aber nicht automatisch vollständig verifiziert.

Aktuelle Integrationsversion: **0.9.6**

---

## ✨ Funktionsumfang

Unterstützt werden unter anderem:

- 🌡️ Außen-, Vorlauf-, Rücklauf-, Raum-, Brauchwasser- und Lüftungstemperaturen
- 🔥 Heizungswerte, Gradminuten und berechnete Vorlauftemperaturen
- ❄️ Kühlstatus, Kühlgradminuten und Kühlfreigabe
- 💧 Brauchwasserwerte, Mehr Brauchwasser und Brauchwasserzirkulation
- ⚙️ Verdichterstatus, Frequenz, Laufzeiten, Leistung und Kältekreiswerte
- 💨 Pumpen-, Hydraulik- und Ventilatorwerte
- 🌬️ Lüftungsmodus, Luftfeuchtigkeit und Lüftungstemperaturen
- 🧊 EEV-/EVI-, Kältekreis- und Abtauwerte
- ⚡ Energie- und Leistungswerte
- 🚨 Alarm- und Meldungsinformationen
- 🎛️ ausdrücklich freigegebene Schreibfunktionen über `switch`, `select`, `number` und `time`
- 🩺 Diagnoseinformationen für API-Erreichbarkeit, Fallback und Verbindungsfehler
- 📊 erweiterte Diagnosedatei mit aktuellen Roh-/Skalierwerten und 5 Tagen Minutenhistorie

---

## 🧩 Entitätsprofile

Nach erfolgreicher Verbindung liest die Integration die tatsächlich verfügbaren REST-Punkte des Geräts ein. Anschließend kann der gewünschte Entitätsumfang gewählt werden.

| Profil | Zweck | Verhalten |
|---|---|---|
| **Standard** | Typische Home-Assistant-Nutzung | Kuratierter Kernumfang für Temperaturen, Brauchwasser, Energie, Verdichter und wichtige Betriebswerte |
| **Erweitert** | Ausführliche Anlagenanalyse | Vollständig kuratierter, der Integration bekannter `POINTS`-Umfang einschließlich detaillierter Diagnose- und Servicewerte |
| **Komplett** | Maximale Sichtbarkeit | Alle von der lokalen API gemeldeten Punkte; unbekannte Punkte ausschließlich als Read-only-Sensor |
| **Individuell** | Volle Auswahlkontrolle | Der Nutzer wählt nach der Erkennung selbst die gewünschten Variable-IDs aus |

Das frühere Profil **Minimal** ist nicht mehr Bestandteil der Integration.

### Standard

Das Standardprofil enthält den im Alltag sinnvollsten, direkt verifizierten REST-Umfang. Dazu gehören unter anderem:

- Außentemperatur BT1
- Vorlauf BT2 und Rücklauf BT3
- Roomsensor BT50
- Brauchwassertemperaturen BT7, BT6 und BT5
- Volumenstrom BF1
- Gradminuten
- berechnete Vorlauftemperatur
- ausgewählte Außeneinheit-/Kältekreiswerte
- Verdichterfrequenz und Schutz-/Alarmzustände
- ausgewählte Lüftungstemperaturen und Luftfeuchtigkeit

### Erweitert

Erweitert enthält zusätzlich den vollständig gepflegten bekannten Punktumfang, darunter zahlreiche:

- Hydraulikwerte
- detaillierte Verdichterwerte
- EEV-/EVI-Werte
- Abtau- und Diagnosewerte
- Lüftungsparameter
- Zusatzheizungs- und Serviceinformationen

### Komplett

Komplett zeigt zusätzlich Punkte, die der Integration noch nicht als eigener `PointDef` bekannt sind.

**Wichtig:** Ein unbekannter Punkt bleibt immer **Read-only** – auch wenn die lokale REST API `isWritable=true` meldet.

Damit gilt:

> **Alle verfügbaren Werte sichtbar machen, aber nur verstandene und explizit abgesicherte Funktionen beschreibbar machen.**

### Individuell

Bei **Individuell** werden die tatsächlich vom Gerät gemeldeten Variable-IDs in einer Mehrfachauswahl angeboten. Die Auswahl wird dauerhaft im Config Entry gespeichert und bleibt bei Neustarts, Reloads und Updates erhalten.

---

## 🔎 Entitätsvorschau

Vor dem Abschluss der Einrichtung und vor dem Anwenden geänderter Optionen zeigt die Integration eine letzte Entitätsübersicht.

Sie zeigt unter anderem:

- aktive bzw. ausgewählte Punkte
- bereits registrierte und neue Entitäten
- abgewählte Punkte
- gegebenenfalls zur Registry-Löschung vorgesehene Punkt-Entitäten
- zusätzliche Integrationsentitäten wie API-Erreichbarkeit, Fallback und Meldungen

Ein angefordertes Backup und eine Registry-Bereinigung werden erst nach der finalen Bestätigung ausgeführt.

---

## 🏷️ Entitätsbenennung

Es stehen drei Benennungsmodi zur Verfügung:

- **Home-Assistant-Standard** – empfohlen, mit Übersetzungen und `translation_key`s
- **Lokale API** – Name möglichst direkt aus der lokalen REST API
- **Technisch** – lokale API-Bezeichnung plus Variable-ID

Home Assistant bestimmt weiterhin das endgültige Entity-ID-Format.

---

## 🧱 Unterstützte Home-Assistant-Plattformen

Je nach bekannter Semantik eines NIBE-Punkts verwendet die Integration:

- `sensor`
- `binary_sensor`
- `switch`
- `select`
- `number`
- `time`

Nicht jeder von der lokalen API als schreibbar gemeldete Punkt wird automatisch zu einer schreibbaren Home-Assistant-Entität.

---

## 🛡️ Schreibzugriffe und Sicherheitsmodell

Die Integration verfolgt ein bewusstes **Allowlist-Prinzip**.

Schreibbar sind nur Punkte, deren Bedeutung und zulässige Werte bekannt und in der Integration ausdrücklich definiert sind.

Unbekannte Punkte bleiben auch bei `isWritable=true` nur lesbar.

Alle schreibenden REST-Aufrufe werden über einen gemeinsamen Lock serialisiert. Nach einem Schreibbefehl wird der betroffene Punkt erneut gelesen, damit Home Assistant möglichst den tatsächlich von der Anlage bestätigten Zustand zeigt.

### Heizung und Kühlung

Die Schalter für **Heizung zulassen** und **Kühlung zulassen** werden unmittelbar vor einem Schreibversuch gegen den aktuellen Betriebsmodus geprüft.

Aktuelle Schutzlogik:

| Betriebsmodus | Heizung zulassen | Kühlung zulassen |
|---|---:|---:|
| Auto | blockiert | blockiert |
| Manuell | schreiben erlaubt | schreiben erlaubt |
| Nur Zusatzheizung | schreiben erlaubt | blockiert |
| unbekannt / nicht sicher lesbar | blockiert | blockiert |

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
- drei REST-verfügbare BWZ-Zeitperioden mit Start- und Stoppzeit

Für die Brauchwasserzirkulation werden nur Punkte verwendet, die über die lokale REST API tatsächlich verfügbar sind.

---

## ⚙️ Verdichter, Außeneinheit und Abtauung

Je nach Gerät und Profil stehen unter anderem zur Verfügung:

- Verdichterstatus
- aktuelle und angeforderte Verdichterfrequenz
- Verdichterstarts und Laufzeiten
- Heiz-, Kühl- und Brauchwasserlaufzeiten
- Rücklauf und Kondensatorvorlauf
- Heißgas-, Flüssigkeits- und Sauggastemperaturen
- Verdampfertemperaturen
- Hoch-/Niederdruckwerte
- Ventilatordrehzahl
- Schutz- und Alarmzustände
- Abtauzustand und Zeit bis Abtauung
- EEV-/EVI-Überhitzung, Sollwerte und Öffnungsgrade

Nicht über die lokale REST API exponierte Werte werden nicht künstlich ergänzt.

---

## ⚡ Energie und Einheiten

Vorhandene Energie- und Leistungswerte werden – soweit fachlich eindeutig – mit passenden Home-Assistant-Klassen versehen.

Geeignete Zähler verwenden `TOTAL_INCREASING`.

Einheiten werden bei Bedarf normalisiert, beispielsweise:

- `%RH` → `%`
- `l/min` → `L/min`

---

## 🚨 Alarme und Diagnose

Aktive Meldungen werden nur lesend dargestellt. Eine automatische Alarmquittierung oder ein Alarm-Reset ist bewusst nicht implementiert.

### Diagnose-Entitäten

Zusätzlich stehen Diagnoseinformationen bereit, darunter:

- **REST API erreichbar**
- **Einzelpunkt-Fallback aktiv**
- **Letzter Verbindungsfehler**
- aktive Meldungen/Alarme

### Diagnosedaten herunterladen

Ab **0.9.6** enthält die Home-Assistant-Diagnosedatei zusätzlich die Daten, die für die Analyse unplausibler Werte benötigt werden.

Für jeden aktivierten NIBE-Punkt werden – soweit vorhanden – ausgegeben:

- Variable-ID
- Titel/Beschreibung
- Einheit
- Datentyp und Variablengröße
- Divisor und Dezimalstellen
- Schreibbarkeitskennzeichen
- aktueller **Rohwert**
- aktuell von der Integration berechneter **skalierter Wert**
- `isOk`-Status der REST-Antwort

Zusätzlich wird eine **5-Tage-Historie in 1-Minuten-Buckets** aus dem Home-Assistant-Recorder erzeugt. Pro Minute werden kompakt gespeichert:

- Minimum
- Maximum
- Mittelwert
- letzter Wert
- Anzahl der berücksichtigten Samples

Damit lassen sich kurze Ausreißer und typische Skalierungs-/Signed-Integer-Probleme wesentlich besser erkennen als mit einer reinen Momentaufnahme.

Die Historie ist nur verfügbar, wenn die jeweilige Entity im Home-Assistant-Recorder vorhanden ist.

Aus Datenschutz- und Sicherheitsgründen werden weiterhin bewusst **nicht** exportiert:

- Hostname oder IP-Adresse der NIBE
- Benutzername und Passwort
- Authorization-Header oder andere Zugangsdaten
- Seriennummern
- Alarmtexte

Die aktuellen NIBE-Mess- und Einstellwerte sind seit 0.9.6 dagegen bewusst Bestandteil der Diagnosedatei, da sie für technische Fehleranalyse erforderlich sind. Eine Diagnosedatei sollte daher vor öffentlicher Weitergabe geprüft werden.

---

## 🔐 Authentifizierung und TLS

Unterstützte Authentifizierungsmethoden:

- **Benutzername + Passwort**
- **vollständiger Authorization-Header**

Die lokale REST API verwendet häufig ein selbstsigniertes Zertifikat. Die TLS-Zertifikatsprüfung kann deshalb deaktiviert werden. Wenn eine vertrauenswürdige Zertifikatskette verfügbar ist, sollte die Prüfung aktiviert bleiben.

---

## 🌐 Kommunikation, Polling und Robustheit

Im Normalbetrieb werden Werte gesammelt über den lokalen `/points`-Endpunkt gelesen.

Kann eine Sammelantwort nicht sinnvoll verwendet werden, kann die Integration auf Einzelpunktabfragen zurückfallen.

Weitere Schutzmechanismen:

- REST-Antworten auf maximal 4 MiB begrenzt
- maximale JSON-Verschachtelungstiefe 64
- iterative Normalisierung statt unbegrenzter Rekursion
- Backoff beim vollständigen Einzelpunkt-Fallback
- serialisierte Schreibzugriffe

Die Laufzeitintegration verwendet ausschließlich die lokale REST API.

---

## ✅ Voraussetzungen

- mindestens **Home Assistant 2024.12.0**
- NIBE S-Series-Steuerung mit lokaler REST API
- empfohlene aktuelle S-Series-Firmware
- lokale Erreichbarkeit von Home Assistant zur NIBE
- standardmäßig HTTPS auf Port **8443**

Die lokale REST API muss direkt an der NIBE-Steuerung unter **Menü 7 → Service → 7.5.15 – Lokale REST API** aktiviert und mit Zugangsdaten eingerichtet sein.

Die Aktivierung von Modbus allein genügt nicht.

---

## 🧩 Installation

### Manuell

1. `custom_components/nibe_local` nach `/config/custom_components/nibe_local` kopieren.
2. Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen** öffnen.
4. **NIBE Local REST API** auswählen.

### HACS

Wenn das Repository als Custom Repository in HACS eingebunden ist, kann die Integration darüber installiert und aktualisiert werden.

### Einrichtungsablauf

1. Host/IP-Adresse und Port eingeben.
2. Authentifizierungsmethode wählen.
3. Zugangsdaten eingeben.
4. TLS-Zertifikatsprüfung festlegen.
5. Polling-Einstellungen wählen.
6. Verbindung prüfen.
7. Verfügbare REST-Punkte laden.
8. **Standard / Erweitert / Komplett / Individuell** auswählen.
9. Benennung auswählen.
10. Bei **Individuell** die gewünschten Variable-IDs auswählen.
11. Entitätsübersicht prüfen.
12. Mit **OK** anwenden.

Die API-Geräte-ID wird intern fest als `0` verwendet.

---

## ⚙️ Optionen nach der Einrichtung

Später änderbar sind unter anderem:

- Host / IP-Adresse
- Port
- Authentifizierungsmethode
- Zugangsdaten
- TLS-Zertifikatsprüfung
- Polling-Intervall
- Verzögerung nach Schreibbefehlen
- Entitätsprofil
- Benennungsmodus
- individuelle Variable-Auswahl

---

## 🔄 Updates und Beständigkeit

Bei **Standard** und **Erweitert** wird das gewählte Profil gespeichert. Wenn eine spätere Version einen zusätzlichen bekannten und verifizierten Punkt einem Profil zuordnet und das Gerät ihn liefert, kann er automatisch erscheinen.

Bei **Individuell** werden nur die explizit gespeicherten Variable-IDs verwendet.

Entity-Unique-IDs sind pro Config Entry getrennt, sodass mehrere NIBE-Anlagen parallel betrieben werden können.

---

## ⚠️ Grenzen und bekannte Einschränkungen

Nicht automatisch unterstützt werden:

- unbekannte schreibbare Punkte als generische Steuerung
- automatisches Erraten unbekannter Enum-Semantik
- automatisches Freischalten unbekannter Service-/Installerparameter
- Alarmquittierung oder Alarmreset
- myUplink-Cloudfunktionen

Die tatsächlich verfügbaren Variablen hängen von Modell, angeschlossenen Modulen, Firmware und Anlagenkonfiguration ab.

---

## 🧪 Entwicklung und Tests

GitHub Actions prüft die Integration gegen:

- **Home Assistant 2024.12.0**
- eine aktuelle Home-Assistant-Version

Die Regressionstests decken unter anderem ab:

- API-Antwortnormalisierung
- Antwortgrößen- und Verschachtelungslimits
- Authentifizierungslogik
- Schreibserialisierung
- Number-Grenzen
- Enum-/Select-Verhalten
- Entitätsprofile
- Geräte-/Equipment-Erkennung
- Diagnose-Datenschutz
- aktuelle Diagnosewerte und 5-Tage-Minutenhistorie
- Import-Smoke-Test aller Plattformen
- Ruff `F821`

---

## 🎨 Branding

Lokale Brand-Dateien befinden sich unter `custom_components/nibe_local/brand/` und enthalten helle sowie dunkle Icon-/Logo-Varianten.

---

## 📝 Changelog

Die wesentlichen Änderungen pro Version stehen in [`CHANGELOG.md`](CHANGELOG.md).

---

## ⚖️ Projektstatus

Diese Integration ist ein **inoffizielles Community-Projekt** und steht in keiner Verbindung zu NIBE.

Sie befindet sich weiterhin vor Version 1.0 und wird auf einer realen Anlage weiterentwickelt und getestet.

---

## 🛡️ Haftung

Diese Software wird als Open-Source-Projekt **ohne Gewährleistung oder Garantie** bereitgestellt. Die Nutzung erfolgt auf eigene Gefahr.

Die Integration kann Einstellungen einer Heizungs-, Kühlungs-, Lüftungs- und Brauchwasseranlage verändern. Nutzer müssen selbst sicherstellen, dass Änderungen für die konkrete Anlage zulässig und sicher sind.

Bei sicherheitsrelevanten oder kritischen Funktionen dürfen die von dieser Integration angezeigten Werte und Zustände nicht als alleinige Entscheidungsgrundlage verwendet werden. Maßgeblich sind im Zweifel die Anzeigen und Einstellungen am Gerät sowie die offizielle Herstellerdokumentation.

---

## 👥 Autoren

- AndiHOK91
- ChatGPT (OpenAI) – Unterstützung bei Entwicklung, REST-API-Auswertung, Tests und Home-Assistant-Integration
