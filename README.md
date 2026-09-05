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

Aktuelle Integrationsversion: **0.9.8**

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
- ausdrücklich freigegebene Schreibfunktionen über `switch`, `select`, `number` und `time`
- Diagnoseinformationen für API-Erreichbarkeit, Fallback und Verbindungsfehler
- Diagnosedatei mit aktuellen Roh-/Skalierwerten und 24 Stunden Minutenhistorie

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

---

## 🛡️ Schreibzugriffe und Sicherheitsmodell

Die Integration verwendet ein Allowlist-Prinzip. Schreibbar sind nur Punkte, deren Bedeutung und zulässige Werte bekannt und ausdrücklich implementiert sind.

Alle schreibenden REST-Aufrufe werden integrationsweit serialisiert. Nach einem Schreibbefehl wird der betroffene Punkt gezielt neu gelesen.

### Heizung und Kühlung

Die Schalter **Heizung zulassen** und **Kühlung zulassen** werden unmittelbar vor dem Schreiben gegen den aktuellen Betriebsmodus geprüft.

| Betriebsmodus | Heizung zulassen | Kühlung zulassen |
|---|---:|---:|
| Auto | blockiert | blockiert |
| Manuell | schreiben erlaubt | schreiben erlaubt |
| Nur Zusatzheizung | schreiben erlaubt | blockiert |
| unbekannt / nicht sicher lesbar | blockiert | blockiert |

Der AUX-Schalter für die Zusatzheizung ist davon unabhängig und wird nicht über diese Betriebsmodus-Sperre blockiert.

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

### Diagnosedaten herunterladen

Die Diagnosedatei enthält für aktivierte NIBE-Punkte – soweit vorhanden – unter anderem:

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

Zusätzlich wird eine **24-Stunden-Historie in 1-Minuten-Buckets** aus dem Home-Assistant-Recorder erzeugt. Pro Minute werden Minimum, Maximum, Mittelwert, letzter Wert und Sample-Anzahl gespeichert.

Aus Datenschutz- und Sicherheitsgründen werden bewusst nicht exportiert:

- Hostname oder IP-Adresse der NIBE
- Benutzername und Passwort
- Authorization-Header oder andere Zugangsdaten
- Seriennummern
- Alarmtexte

Die aktuellen NIBE-Mess- und Einstellwerte sind bewusst Bestandteil der Diagnosedatei, weil sie für technische Fehleranalyse erforderlich sind. Vor öffentlicher Weitergabe sollte die Datei geprüft werden.

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

## 🧪 Entwicklung und Tests

GitHub Actions prüft die Integration gegen:

- **Home Assistant 2024.12.0**
- eine aktuelle Home-Assistant-Version

Die Regressionstests decken unter anderem API-Normalisierung, Authentifizierung, Schreibschutz, Profile, Diagnose-Datenschutz, Sentinelwerte und Abtau-Sonderzustände ab.

---

## ⚠️ Grenzen

Nicht automatisch unterstützt werden:

- unbekannte schreibbare Punkte als generische Steuerung
- automatisches Erraten unbekannter Enum-Semantik
- automatisches Freischalten unbekannter Service-/Installerparameter
- Alarmquittierung oder Alarmreset
- myUplink-Cloudfunktionen

Die tatsächlich verfügbaren Variablen hängen von Modell, angeschlossenen Modulen, Firmware und Anlagenkonfiguration ab.

---

## ⚖️ Projektstatus und Haftung

Diese Integration ist ein **inoffizielles Community-Projekt** und steht in keiner Verbindung zu NIBE. Sie befindet sich weiterhin vor Version 1.0 und wird auf einer realen Anlage weiterentwickelt und getestet.

Die Software wird ohne Gewährleistung oder Garantie bereitgestellt. Die Nutzung erfolgt auf eigene Gefahr. Bei sicherheitsrelevanten Funktionen sind im Zweifel die Anzeigen und Einstellungen am Gerät sowie die offizielle Herstellerdokumentation maßgeblich.

---

## 👥 Autoren

- AndiHOK91
- ChatGPT (OpenAI) – Unterstützung bei Entwicklung, REST-API-Auswertung, Tests und Home-Assistant-Integration
