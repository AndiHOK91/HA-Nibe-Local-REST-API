<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/nibe_local/brand/dark_logo.png">
    <source media="(prefers-color-scheme: light)" srcset="custom_components/nibe_local/brand/logo.png">
    <img alt="NIBE Local REST API – Home Assistant Custom Integration" src="custom_components/nibe_local/brand/logo.png" width="760">
  </picture>
</p>

# NIBE Local REST API – Home Assistant Custom Integration

> 🏠 **Lokal** · 🔒 **Sicherheitsorientiert** · ☁️ **ohne Cloud-Zwang** · 🌡️ **Heizung** · ❄️ **Kühlung** · 💧 **Brauchwasser** · 🌬️ **Lüftung**

Diese Custom Integration bindet eine NIBE-S-Series-Anlage direkt über die **lokale REST API** in Home Assistant ein. Für das normale Auslesen und die ausdrücklich unterstützten Steuerfunktionen ist keine Verbindung zu myUplink erforderlich.

Entwickelt und im realen Betrieb getestet mit **VVM S320, S2125 und ERS S40-400**. Andere S-Series-Konfigurationen können ebenfalls funktionieren, sind aber nicht automatisch vollständig verifiziert.

Aktuelle Integrationsversion: **0.12.2**

> [!WARNING]
> Die **Statistikmigration** ist experimentell und noch nicht auf einer produktiven Home-Assistant-Recorder-Datenbank praktisch erprobt. Vor der Verwendung sollte ein reguläres Home-Assistant-Backup vorhanden sein.

---

## ✨ Funktionsumfang

Unterstützt werden unter anderem:

- Heizungs-, Kühlungs-, Brauchwasser- und Lüftungswerte
- Temperaturen, Gradminuten, Volumenstrom sowie Pumpen- und Ventilatorwerte
- Verdichter-, Kältekreis-, EEV-/EVI- und Abtauwerte
- Energie- und Leistungswerte
- Alarme und Meldungen
- ausdrücklich freigegebene Steuerungen über `switch`, `select` und `number`
- automatische Erkennung optionaler Hardware wie ERS, BE6/BE7 und Brauchwasserzirkulation
- Standard- und erweiterte Diagnosedaten
- experimentelle Migration vorhandener Home-Assistant-Langzeitstatistiken

Unbekannte Punkte bleiben **read-only**, auch wenn die lokale REST API sie als schreibbar meldet. Schreibfunktionen werden nur für verstandene und gezielt abgesicherte Variablen angeboten.

---

## 🧩 Entitätsprofile

| Profil | Zweck |
|---|---|
| **Standard** | Kuratierter Kernumfang für den normalen Home-Assistant-Betrieb |
| **Erweitert** | Zusätzliche technische Diagnose-, Kältekreis- und Servicewerte |
| **Komplett** | Alle von der lokalen REST API gemeldeten Punkte; unbekannte Punkte read-only |
| **Individuell** | Freie Auswahl der gewünschten Variable-IDs |

Die Benennung kann zwischen **Home-Assistant-Standard**, **Lokale API** und **Technisch** gewählt werden.

### Verifizierte Pumpenpunkte

Auf der Referenzanlage wurden folgende Zuordnungen durch Live-Messungen bestätigt:

- **2792** – Drehzahl Heizungsumwälzpumpe **GP1**
- **1975** – Betriebszustand Heizungsmediumpumpe **GP6**
- **3138** – interne Ladepumpe **GP12**

---

## 🎛️ Bedienfunktionen

### Lüftung +

**Lüftung +** ist ein Komfortschalter für den normalen Dashboard-Betrieb und verwendet denselben NIBE-Punkt wie der Select **Lüftungsmodus** (Variable-ID **3830**).

- **Einschalten** setzt den Lüftungsmodus auf **Erhöht** (Rohwert `3`).
- Der Schalter wird als **Ein** angezeigt, wenn die Anlage auf **Erhöht** (`3`) oder **Maximal** (`4`) steht.
- **Ausschalten** setzt den Lüftungsmodus auf **Normal** (Rohwert `0`).

Der Schalter bildet also **keinen zusätzlichen NIBE-Betriebsmodus** ab, sondern ist eine vereinfachte Bedienung des vorhandenen Lüftungsmodus. Beim Ausschalten wird immer auf **Normal** zurückgeschaltet, nicht auf den zuvor verwendeten Modus.

### Mehr Brauchwasser

Der Schalter **Mehr Brauchwasser** bildet die Funktion **„Einmalige Erhöhung“** ab, wie sie auch in der **myUplink-App** angeboten wird.

- **Einschalten** schreibt für Variable-ID **4564** den Rohwert `2` und startet damit die einmalige Brauchwassererhöhung.
- **Ausschalten** schreibt den Rohwert `0` und beendet die einmalige Erhöhung.
- Der angezeigte Schalterzustand wird nicht allein aus dem geschriebenen Wert abgeleitet, sondern über die von NIBE gemeldete **Restzeit** der Funktion (Variable-ID **4030**) überprüft. Solange eine Restzeit größer als 0 Minuten gemeldet wird, gilt **Mehr Brauchwasser** als aktiv.

Damit verhält sich der Home-Assistant-Schalter wie die entsprechende **„Einmalige Erhöhung“** in myUplink und ist nicht mit einer dauerhaften Änderung des normalen Brauchwassermodus zu verwechseln.

Die in **myUplink** zusätzlich angebotene Funktion **Schnellheizen mit Zusatzheizung** ist davon getrennt. Für diese Funktion ist in der derzeit bekannten lokalen REST API **kein verlässlich bestätigter REST-Punkt bekannt**. Die Integration bietet deshalb aktuell bewusst keine entsprechende Schnellheiz-Funktion an.

---

## 💧 Brauchwasserzirkulation

Die Integration stellt – abhängig von Anlage und Firmware – unter anderem bereit:

- Betriebszustand der Zirkulationspumpe **GP11**
- Betriebs- und Stillstandszeit
- drei über die lokale REST API sichtbare Zeitperioden mit Start- und Stoppzeit

Die Zeitwerte werden derzeit bewusst **read-only** dargestellt.

> [!NOTE]
> Auf der Referenzanlage erfolgt das **Ein- bzw. Ausschalten der Brauchwasserzirkulation in Home Assistant derzeit über Modbus**. Die lokale REST API stellt zwar die Start- und Stoppzeiten der drei Perioden bereit, bislang ist jedoch **kein verlässlich bestätigter REST-Punkt bekannt, mit dem die einzelnen Perioden aktiviert oder deaktiviert werden können**.
>
> Deshalb wird diese Funktion von der REST-Integration nicht künstlich ergänzt. Die verwendete Modbus-Steuerung ist eine separate Home-Assistant-Lösung und nicht Bestandteil dieser Integration.

---

## 🛡️ Schreibzugriffe und Sicherheit

Die Integration verwendet ein Allowlist-Prinzip. Schreibzugriffe werden nur für bekannte Punkte angeboten und integrationsweit serialisiert.

Zusätzlich gilt:

- NIBEs Antwort auf einen Schreibzugriff wird ausgewertet; **HTTP 200 allein gilt nicht als Erfolg**
- fehlerhafte NIBE-Metadaten werden bei bestätigten Punkten gezielt korrigiert
- unbekannte schreibbare REST-Punkte bleiben read-only
- bekannte Zeitwerte bleiben read-only, solange deren Schreiben nicht zuverlässig verifiziert ist
- **Heizung zulassen** und **Kühlung zulassen** werden abhängig vom aktuellen Betriebsmodus geschützt
- für **Variable-ID 3702** wird wegen fehlerhafter REST-Metadaten der verifizierte Bereich **55,0–70,0 °C** verwendet

---

## 🚨 Diagnose

Home Assistant stellt Diagnoseinformationen wie API-Erreichbarkeit, Fallback-Status, Verbindungsfehler und aktive Meldungen bereit.

Über `nibe_local.export_extended_diagnostics` können bei Bedarf erweiterte Punktinformationen und optional **1, 3, 5 oder 7 Tage** Recorder-Historie exportiert werden. Zugangsdaten werden dabei nicht ausgegeben; Mess- und Einstellwerte können jedoch enthalten sein.

---

## 🧪 Experimentelle Statistikmigration

Vorhandene Langzeitstatistiken eines bisherigen Sensors – beispielsweise aus einer Modbus-Integration – können experimentell auf einen REST-Sensor übertragen werden.

Die Migration arbeitet vorsichtig:

- zunächst Vorschau
- Import nur fehlender Stundenwerte
- vorhandene Zielwerte werden nicht überschrieben
- auf Wunsch bzw. standardmäßig Sicherung vor dem Import
- kein direkter SQL-Zugriff durch die Integration

Verfügbare Aktionen:

- `nibe_local.preview_statistics_migration`
- `nibe_local.import_statistics_migration`
- `nibe_local.list_statistics_backups`
- `nibe_local.preview_statistics_restore`

Eine automatische Wiederherstellung ist derzeit bewusst nicht implementiert.

---

## ✅ Voraussetzungen

- mindestens **Home Assistant 2024.12.0**
- NIBE S-Series-Steuerung mit lokaler REST API
- aktuelle S-Series-Firmware empfohlen
- lokale Netzwerkverbindung zwischen Home Assistant und NIBE
- standardmäßig HTTPS auf Port **8443**

Die lokale REST API wird an der NIBE unter **Menü 7 → Service → 7.5.15 – Lokale REST API** aktiviert und mit Zugangsdaten eingerichtet.

Unterstützt werden:

- Benutzername + Passwort
- vollständiger Authorization-Header
- optionale Deaktivierung der TLS-Zertifikatsprüfung bei selbstsigniertem Zertifikat

---

## 🧩 Installation

### HACS

Direkt über **My Home Assistant** in HACS öffnen:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AndiHOK91&repository=HA-Nibe-Local-REST-API&category=integration)

Wenn das Repository als Custom Repository in HACS eingebunden ist, kann die Integration darüber installiert und aktualisiert werden. **v0.12.2 ist ein regulärer Release.**

### Manuell

1. `custom_components/nibe_local` nach `/config/custom_components/nibe_local` kopieren.
2. Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen** öffnen.
4. **NIBE Local REST API** auswählen.

### Einrichtung

1. Host/IP-Adresse und Port eingeben.
2. Authentifizierung, TLS-Prüfung und Polling konfigurieren.
3. Verbindung prüfen.
4. Erkannte Hardware kontrollieren.
5. Entitätsprofil und Benennung wählen.
6. Bei **Individuell** gewünschte Variable-IDs auswählen.
7. Entitätsübersicht prüfen und bestätigen.

Die API-Geräte-ID wird intern fest als `0` verwendet.

---

## ⚠️ Grenzen

Nicht automatisch unterstützt werden:

- generische Schreibsteuerung unbekannter Punkte
- Erraten unbekannter Enum-Bedeutungen
- Alarmquittierung oder Alarmreset
- myUplink-Cloudfunktionen
- generisches Schreiben von NIBE-Zeitwerten
- Aktivieren/Deaktivieren der BWZ-Zeitperioden über REST, solange dafür kein verifizierter Punkt bekannt ist
- automatische Wiederherstellung eines Statistikimports

Die tatsächlich verfügbaren Variablen hängen von Modell, Zubehör, Firmware und Anlagenkonfiguration ab.

---

## 🧪 Entwicklung und Tests

GitHub Actions prüft die Integration gegen:

- **Home Assistant 2024.12.0**
- **Home Assistant 2026.9.1**
- eine aktuelle Home-Assistant-Version (`latest`)

Regressionstests decken unter anderem API-Verarbeitung, Authentifizierung, Schreibschutz, Profile, Hardware-Erkennung, Übersetzungen, Firmware-Eigenheiten, Diagnose-Datenschutz und Statistikmigration ab.

---

## ⚖️ Projektstatus und Haftung

Dieses Repository ist ein **inoffizielles Community-Projekt** und steht in keiner Verbindung zu NIBE.

Die Software wird ohne Gewährleistung oder Garantie bereitgestellt. Bei sicherheitsrelevanten Funktionen sind im Zweifel die Anzeigen und Einstellungen am Gerät sowie die offizielle Herstellerdokumentation maßgeblich.

---

## 👥 Autoren

- AndiHOK91
- ChatGPT (OpenAI) – Unterstützung bei Entwicklung, REST-API-Auswertung, Tests und Home-Assistant-Integration
