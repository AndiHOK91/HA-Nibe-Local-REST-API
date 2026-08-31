# NIBE Local REST – Home Assistant Custom Integration (0.3.18)

Private Home-Assistant-Custom-Integration für die lokale NIBE REST API, entwickelt und getestet für eine VVM S320 mit S2125.

## Autoren

- AndiO91
- ChatGPT (OpenAI) – Unterstützung bei Entwicklung, REST-API-Auswertung und Home-Assistant-Integration

## Installation

1. Den Ordner `custom_components/nibe_local` nach `/config/custom_components/nibe_local` kopieren.
2. Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste** die Integration **NIBE Local REST** hinzufügen.
4. Host/IP-Adresse, Port, Geräte-ID und Zugangsdaten eintragen.
5. Bei einem lokal selbstsignierten Zertifikat die SSL-Zertifikatsprüfung deaktiviert lassen.

## Funktionsumfang

- Lokaler HTTPS-Zugriff auf die NIBE REST API
- Sensoren für Heizung, Kühlung, Brauchwasser, Hydraulik und S2125
- Verdichter-, EEV-, EVI- und Enteisungsdiagnose
- Lüftungsmodus mit Normal, Aus, Reduziert, Erhöht und Maximal
- Dashboard-Schalter **Lüftung +**
  - Ein schreibt `3830 = 3` (Erhöht)
  - Aus schreibt `3830 = 0` (Normal)
  - Aktiv bei tatsächlich gemeldetem Modus `3` oder `4`
  - Optimistische Anzeige bis zur Bestätigung durch die NIBE
- Dashboard-Schalter **Mehr Brauchwasser**
  - Ein schreibt `4564 = 2`
  - Aus schreibt `4564 = 0`
  - Tatsächlicher Zustand richtet sich nach `4030` (verbleibende Minuten)
  - Anzeige bleibt beim Schalten stabil, bis die NIBE den neuen Zustand bestätigt
- **Nachtabsenkung** über Punkt `4040`
- **Starttemperatur Nachtabsenkung** über Punkt `4041`
- **Aktive Meldungen** als read-only Alarm-Entity mit Alarmnummern und Detailattributen
- Werte von **Zeit bis Enteisung** über 720 Minuten werden als 0 Minuten dargestellt
- Punkt `8060` wird als **Enteisung angefordert (EB101)** angezeigt:
  - `0` = Aus
  - `1` = Aktiv
  - `2` = Passiv
  - sonst = Unbekannt
- Konfigurierbares Polling-Intervall
- Konfigurierbare Verzögerung für das Rücklesen nach Schaltbefehlen
- Pool-Entities sind bewusst ausgeschlossen

## Zusätzliche Anlagenparameter in 0.3.18

Zusätzlich integriert wurden:

- Energie: Punkt `829`
- Zusatzheizung/Systemstatus: `1186`, `1820`, `1827`, `3919`, `4064`
- Brauchwasser: `3699`–`3711` sowie `3748`
- Heizung: `3749`
- Betriebs-/Pumpenmodus: `3751`, `3752`
- Lüftung: `3841`–`3845`

Die bereits vorhandenen Punkte `3697`, `3920` und `3921` bleiben erhalten. Schreibbare Temperatur-, Zeitdauer- und Intervallwerte werden als Number-Entities, Ein/Aus-Einstellungen als Switches und Betriebsmodi als Selects bereitgestellt. Read-only-Zustände werden als Sensor bzw. Binärsensor angelegt.

**Punkt 3708 „Startzeit periodisches Brauchwasser“** wird zunächst bewusst nur lesend bereitgestellt. Die NIBE-Punkteliste weist ihn zwar als schreibbar aus, das konkrete Schreibformat dieses Zeitwerts ist mit den bislang vorliegenden REST-Informationen jedoch nicht eindeutig verifiziert. Dadurch wird vermieden, ein möglicherweise falsches Zeitformat an die Anlage zu senden.

## Alarmmeldungen

Die Entity **Aktive Meldungen** zeigt die Anzahl aktiver Meldungen. Zusätzlich stehen folgende Attribute zur Verfügung:

- `alarm_ids` – erkannte NIBE-Alarmnummern
- `alarm_summary` – kompakte Zusammenfassung aus Alarmnummer und Text
- `alarms` – normalisierte Detailinformationen wie Beschreibung, Schweregrad, Zeit und Quelle

Die Alarmfunktion ist bewusst **nur lesend**. Es wird keine Reset- oder Quittierfunktion angeboten.

## Lüftungssteuerung

Punkt `3830` wird für den Ventilationsmodus verwendet. Für die Nachtabsenkung sind zusätzlich die schreibbaren Punkte `4040` und `4041` integriert. Einheit, Skalierung, Min-/Max-Werte und Schreibbarkeit werden soweit möglich aus den REST-Metadaten der NIBE übernommen.

## Haftungs- und Gewährleistungsausschluss

Diese Software wird als Open-Source-Projekt **ohne Gewährleistung oder Garantie** bereitgestellt. Die Nutzung erfolgt **auf eigene Gefahr**. Es wird insbesondere keine Gewähr für die Richtigkeit, Vollständigkeit, Aktualität oder Fehlerfreiheit der ausgelesenen, berechneten, übersetzten oder geschriebenen Werte sowie für die dauerhafte Kompatibilität mit bestimmten NIBE-Geräten, Firmware-Versionen oder Home-Assistant-Versionen übernommen.

Die Integration kann Einstellungen einer Heizungs-, Kühlungs-, Lüftungs- und Brauchwasseranlage verändern. Nutzer sind selbst dafür verantwortlich, Änderungen vor der Verwendung zu prüfen und sicherzustellen, dass die eingestellten Werte für ihre konkrete Anlage zulässig und sicher sind. Bei sicherheitsrelevanten, frostschutzrelevanten oder anderweitig kritischen Funktionen dürfen die von dieser Integration angezeigten Werte und Zustände nicht als alleinige Entscheidungsgrundlage verwendet werden. Maßgeblich sind im Zweifel die Anzeigen und Einstellungen am NIBE-Gerät sowie die offizielle Dokumentation des Herstellers.

Soweit gesetzlich zulässig, haften die Autoren und Mitwirkenden nicht für unmittelbare oder mittelbare Schäden, Folgeschäden, Sachschäden, Anlagen- oder Komponentenschäden, Datenverluste, Nutzungsausfälle, Energie- oder Mehrkosten oder sonstige Nachteile, die aus der Installation, Konfiguration, Nutzung, Fehlfunktion oder Nichtverfügbarkeit dieser Software entstehen oder damit in Zusammenhang stehen. Dies gilt auch dann, wenn auf die Möglichkeit solcher Schäden hingewiesen wurde.

Dieser Hinweis ergänzt den Haftungs- und Gewährleistungsausschluss der **MIT-Lizenz**. Zwingende gesetzliche Haftungstatbestände bleiben unberührt.

## Markenhinweis

Dieses Projekt ist ein **inoffizielles Community-Projekt** und steht in keiner Verbindung zu NIBE. Es enthält keine NIBE-Logos oder sonstigen Markengrafiken des Herstellers. Produkt- und Markennamen werden ausschließlich zur Beschreibung der technischen Kompatibilität verwendet.

## Version

Aktueller Stand: **0.3.18**

## Hinweise

Die Integration befindet sich noch vor Version 1.0.0 und wird weiter auf der realen Anlage getestet.

Dokumentation, Versionshinweise und Commit-Beschreibungen werden auf **Deutsch** geführt.
