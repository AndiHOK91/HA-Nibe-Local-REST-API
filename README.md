<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/nibe_local/brand/dark_logo.png">
    <source media="(prefers-color-scheme: light)" srcset="custom_components/nibe_local/brand/logo.png">
    <img alt="NIBE Local REST API – Home Assistant Custom Integration" src="custom_components/nibe_local/brand/logo.png" width="760">
  </picture>
</p>

# NIBE Local REST API – Home Assistant Custom Integration

> 🏠 **Lokal** · ⚡ **Schnell** · 🔒 **Ohne Cloud-Zwang** · 🌡️ **Heizung** · 💧 **Brauchwasser** · 🌬️ **Lüftung**

Diese Custom Integration bindet eine NIBE-Anlage über die **lokale REST API** direkt in Home Assistant ein. Sie wurde für eine Anlage mit **VVM S320, S2125 und ERS S40-400** entwickelt und wird dort im laufenden Betrieb getestet.

Die Kommunikation erfolgt lokal im eigenen Netzwerk. Für das normale Auslesen ist keine Cloud-Verbindung zu myUplink erforderlich.

## ✨ Was die Integration kann

Die Integration stellt zahlreiche Werte und Funktionen der NIBE-Anlage als Home-Assistant-Entitäten bereit, unter anderem:

- 🌡️ Temperaturen für Außenluft, Vorlauf, Rücklauf, Raum, Brauchwasser und Lüftung
- 🔥 Heizungs- und Kühlungswerte einschließlich Gradminuten und berechneten Vorlauftemperaturen
- ⚙️ Verdichterdaten wie Frequenz, Leistung, Strom, Starts und Betriebszeiten
- ⚡ Energie- und Leistungswerte
- 💧 Pumpen-, Hydraulik- und Brauchwasserwerte
- 🌬️ Lüftungswerte wie Temperaturen, Luftfeuchtigkeit und Ventilatordrehzahlen
- 🧊 Diagnosewerte der Außeneinheit, EEV/EVI und Abtauung
- 🚨 Alarm- und Meldungsinformationen
- 🎛️ Schreibbare Einstellungen als Schalter, Auswahlfelder, Zahlenwerte und Uhrzeiten
- 🔐 Automatische Neuauthentifizierung bei abgelehnten Zugangsdaten
- 🔔 Home-Assistant-Benachrichtigungen bei Authentifizierungs- und länger anhaltenden Verbindungsfehlern
- 🩺 Diagnose-Entitäten für REST-API-Erreichbarkeit, Fallback-Status und den letzten Verbindungsfehler

Die Entitäten werden regelmäßig über die lokale REST API aktualisiert. Das Polling-Intervall kann in den Optionen angepasst werden.

## 🌬️ Lüftung

Für die Lüftung stehen unter anderem Abluft, Fortluft, Zuluft, Außenlufttemperatur, Luftfeuchtigkeit, Ventilatordrehzahlen, Lüftungsmodus, Nachtabsenkung und Rückstellzeiten bereit.

### ➕ Lüftung +

Der Schalter **„Lüftung +“** setzt die Lüftung beim Einschalten auf **Erhöht** und beim Ausschalten zurück auf **Normal**. Anschließend wird der tatsächlich von der NIBE gemeldete Zustand geprüft, damit die Anzeige in Home Assistant stabil bleibt.

## 💧 Mehr Brauchwasser

Mit **„Mehr Brauchwasser“** kann die zusätzliche Brauchwasserbereitung direkt aus Home Assistant angefordert und wieder beendet werden.

Die Integration berücksichtigt zusätzlich die von der Anlage gemeldete verbleibende Laufzeit. Weitere Brauchwasserparameter umfassen Temperaturen, Bedarf, Start-/Stopptemperaturen, periodische Brauchwassererhöhung sowie Zirkulationszeiten.

## 🔥 Heizung und ❄️ Kühlung

Die Integration liest unter anderem Außen-, Vorlauf-, Rücklauf- und Raumtemperaturen sowie Gradminuten und Heizkurvenwerte aus.

Für **„Heizung zulassen“** und **„Kühlung zulassen“** wird vor jedem Schreibversuch der aktuelle Betriebsmodus der NIBE gezielt neu gelesen:

- **Auto:** beide Schalter nur lesbar
- **Manuell:** Heizung und Kühlung schreibbar
- **Nur Zusatzheizung:** Heizung schreibbar, Kühlung nur lesbar
- **Unbekannter oder nicht verfügbarer Betriebsmodus:** beide Schreibvorgänge werden blockiert

Kann der Betriebsmodus nicht sicher neu gelesen werden, wird vorsorglich **kein Schreibbefehl** gesendet.

## 🎚️ Schreibbare Zahlenwerte

Number-Entitäten verwenden die von der NIBE gelieferten Metadaten für Min-/Max-Grenzen und Schrittweite. Unplausible Metadaten werden aus Sicherheitsgründen nicht zum Schreiben verwendet.

Es werden nur positive Divisoren akzeptiert. Werte, die sich nicht exakt auf die von NIBE vorgegebene Rohwert-Schrittweite abbilden lassen, werden blockiert statt stillschweigend gerundet.

## ⚙️ Außeneinheit und Verdichter

Bereitgestellt werden unter anderem:

- Verdichterstatus und -frequenzen
- elektrische Leistung und Strom
- Verdichterstarts und Betriebszeiten
- Kältekreis-Temperaturen
- Ventilatordrehzahl
- Hoch- und Niederdruckwerte
- EEV-/EVI-Werte
- Enteisungsstatus und Enteisungsinformationen

## ⚡ Energie

Vorhandene Energie- und Leistungswerte der NIBE werden als Home-Assistant-Sensoren bereitgestellt, darunter der Energiezähler BE6 und aktuelle Leistungswerte des Energieprotokolls.

Geeignete Entitäten verwenden passende Home-Assistant-State-Classes für Langzeitstatistiken und Energieverläufe.

Von NIBE gelieferte Einheiten werden, wo nötig, auf Home-Assistant-konforme Schreibweisen normalisiert. Dazu gehören insbesondere `%RH` → `%` für Luftfeuchtigkeit und `l/min` → `L/min` für Volumenstrom. Die Luftfeuchtigkeits-Device-Class wird nur gesetzt, wenn NIBE den Wert ursprünglich ausdrücklich als `%RH` kennzeichnet; andere Prozentwerte bleiben unverändert klassifiziert.

## 🚨 Alarme und Meldungen

Aktive NIBE-Meldungen werden nur lesend dargestellt. Soweit von der REST API geliefert, können Alarmnummer, Beschreibung, Schweregrad, Zeitpunkt und Quelle angezeigt werden.

Wenn die NIBE einen eigenen Alarmtext liefert, wird dieser bevorzugt. Dadurch bleibt die am Gerät verwendete Sprache erhalten. Bei deutscher Home-Assistant-Sprache kann für bekannte Alarmnummern ein verifizierter deutscher Fallbacktext verwendet werden, falls die API selbst keinen Text liefert. In anderen Sprachen sowie bei unbekannten Alarmnummern bleibt der Fallback sprachneutral, zum Beispiel `Alarm 1234`.

Eine Quittier- oder Reset-Funktion ist bewusst nicht enthalten.

> ℹ️ Die Alarmdarstellung konnte bislang noch nicht praktisch getestet werden, da während der Entwicklung keine Alarme an der Anlage aufgetreten sind.

## 🔐 Zugangsdaten und Neuauthentifizierung

Bei Einrichtung und in den Optionen wird eine eindeutige Authentifizierungsmethode gewählt:

- **Benutzername + Passwort**
- **Authorization-Header**

Es ist immer nur die ausgewählte Methode aktiv. Wird die Authentifizierungsmethode gewechselt, werden die gespeicherten Zugangsdaten der vorherigen Methode entfernt. Damit kann beispielsweise kein alter Authorization-Header unbemerkt ein neu eingetragenes Passwort übersteuern.

Für bestehende Konfigurationen ohne gespeicherte Authentifizierungsmethode wird ein vorhandener Authorization-Header weiterhin als Header-Authentifizierung erkannt; andernfalls wird Benutzername + Passwort verwendet.

Wenn die NIBE REST API die gespeicherten Zugangsdaten ablehnt, startet Home Assistant den Reauthentifizierungsablauf. Dabei werden nur die Felder der aktuell verwendeten Authentifizierungsmethode abgefragt. Ein leeres geheimes Feld behält den bisherigen gespeicherten Wert bei.

Im Dialog werden Gerätename, konfigurierter Host und aufgelöste IP-Adresse angezeigt. Passwort und Authorization-Header werden maskiert dargestellt.

Bei Header-Authentifizierung wird ein vollständiger HTTP-Authorization-Header verwendet, zum Beispiel `Basic dXNlcjpwYXNzd29ydA==`.

Die lokale NIBE-Geräte-ID ist in der Integration fest auf **`0`** gesetzt und wird nicht als Benutzereinstellung angeboten.

## 🔔 Home-Assistant-Benachrichtigungen

- **Zugangsdaten abgelehnt:** sofortige Meldung, pro zusammenhängender Authentifizierungsstörung nur einmal
- **REST API nicht erreichbar:** Meldung erst nach mindestens **2 Minuten** durchgehender Störung
- **Verbindung wiederhergestellt:** bestehende Auth-/Verbindungsbenachrichtigungen werden automatisch entfernt

Die Meldungen enthalten Gerätename, Host und aufgelöste IP-Adresse, aber keine Zugangsdaten.

## 🩺 Diagnose und Verbindungsstatus

Zusätzliche Diagnose-Entitäten am bestehenden NIBE-Gerät:

- **REST API erreichbar**
- **Einzelpunkt-Fallback aktiv**
- **Letzter Verbindungsfehler**

Der frühere separate Sensor **„Letzter erfolgreicher Poll“** wird nicht mehr angelegt. Auch das frühere Attribut `last_successful_poll` von **„REST API erreichbar“** wird nicht mehr nach außen geschrieben. Der Coordinator führt den Zeitpunkt intern weiter, ohne dadurch bei jedem erfolgreichen Poll einen neuen Recorder-Zustand für die Diagnose-Entität zu erzeugen.

Der Fallback-Status bedeutet nicht automatisch, dass die gesamte REST API ausgefallen ist. Daten können weiterhin über Einzelpunktabfragen geliefert werden.

## 🔄 Lokale Kommunikation und Polling

Im Normalbetrieb werden die Punkte gesammelt über den lokalen `/points`-Endpunkt abgefragt. Kann dessen Antwort nicht ausgewertet werden, nutzt die Integration einen Einzelpunkt-Fallback.

Der vollständige Fallback verwendet einen Backoff von **30 / 60 / 120 Sekunden**. Die Sammelabfrage selbst wird weiterhin bei jedem regulären Poll versucht. Bereits bekannte Punktwerte bleiben bei unvollständigen Fallbacks erhalten.

Nach einem Schreibbefehl wird der betroffene Punkt gezielt neu gelesen, statt jedes Mal die komplette Anlage abzufragen.

Alle schreibenden REST-Aufrufe werden zusätzlich integrationsweit serialisiert. Dadurch erhält die NIBE auch dann keine parallelen `PATCH`-/`POST`-Befehle, wenn mehrere Home-Assistant-Automationen gleichzeitig Einstellungen ändern. Die schreibenden Entity-Plattformen sind zusätzlich auf einen parallelen Vorgang pro Plattform begrenzt; reine Leseplattformen werden vollständig über den Coordinator versorgt.

Bekannte Auswahlwerte werden auch dann korrekt verarbeitet, wenn die Firmware numerische Enum-Werte als Strings liefert.

Das zusätzliche Entity-Attribut `group` verwendet sprachneutrale technische Schlüssel: `system`, `heating`, `cooling`, `hot_water`, `energy`, `hydraulics`, `heat_pump`, `eev_defrost` und `ventilation`.

## 🧩 Installation

1. Den Ordner `custom_components/nibe_local` nach `/config/custom_components/nibe_local` kopieren oder die Integration über HACS installieren.
2. Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste** die Integration **NIBE Local REST API** hinzufügen.
4. Host/IP-Adresse und Port eintragen, die Authentifizierungsmethode auswählen und die dazugehörigen Zugangsdaten angeben.
5. Bei einem lokal selbstsignierten Zertifikat kann die SSL-Zertifikatsprüfung deaktiviert werden.

Die NIBE-Geräte-ID wird nicht abgefragt. Die Integration verwendet fest die Geräte-ID **`0`**.

Mindestens **Home Assistant 2024.12.0** ist vorgesehen. Der GitHub-Actions-Testworkflow prüft die Integration gegen diese Mindestversion und gegen die jeweils aktuelle Home-Assistant-Version.

## 🎨 Branding

Die Integration bringt ihre Brand-Dateien direkt im Integrationsordner mit:

- `custom_components/nibe_local/brand/icon.png`
- `custom_components/nibe_local/brand/dark_icon.png`
- `custom_components/nibe_local/brand/icon@2x.png`
- `custom_components/nibe_local/brand/dark_icon@2x.png`
- `custom_components/nibe_local/brand/logo.png`
- `custom_components/nibe_local/brand/dark_logo.png`

Home Assistant ab 2026.3 kann diese lokalen Brand-Dateien direkt verwenden. Die README wechselt das Logo automatisch passend zum Light-/Dark-Mode.

## 📝 Changelog

Die wesentlichen Änderungen pro Version sind in [`CHANGELOG.md`](CHANGELOG.md) zusammengefasst.

## ⚠️ Hinweise

Die Integration ist ein **inoffizielles Community-Projekt** und steht in keiner Verbindung zu NIBE.

Die Integration befindet sich weiterhin vor Version 1.0 und wird auf einer realen Anlage weiterentwickelt und getestet.

## 🛡️ Haftungs- und Gewährleistungsausschluss

Diese Software wird als Open-Source-Projekt **ohne Gewährleistung oder Garantie** bereitgestellt. Die Nutzung erfolgt **auf eigene Gefahr**.

Die Integration kann Einstellungen einer Heizungs-, Kühlungs-, Lüftungs- und Brauchwasseranlage verändern. Nutzer sind selbst dafür verantwortlich, Änderungen vor der Verwendung zu prüfen und sicherzustellen, dass die eingestellten Werte für ihre konkrete Anlage zulässig und sicher sind.

Bei sicherheitsrelevanten oder kritischen Funktionen dürfen die von dieser Integration angezeigten Werte und Zustände nicht als alleinige Entscheidungsgrundlage verwendet werden. Maßgeblich sind im Zweifel die Anzeigen und Einstellungen am NIBE-Gerät sowie die offizielle Dokumentation des Herstellers.

Soweit gesetzlich zulässig, haften die Autoren und Mitwirkenden nicht für Schäden oder Nachteile, die aus Installation, Konfiguration, Nutzung, Fehlfunktion oder Nichtverfügbarkeit dieser Software entstehen.

Dieser Hinweis ergänzt den Haftungs- und Gewährleistungsausschluss der **MIT-Lizenz**.

## 👥 Autoren

- AndiO91
- ChatGPT (OpenAI) – Unterstützung bei Entwicklung, REST-API-Auswertung und Home-Assistant-Integration
