# NIBE Local REST – Home Assistant Custom Integration (0.4.0)

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

## Betriebsmodus und Freigaben

Punkt `3751` **„Betriebsmodus“** wird mit den bestätigten Werten dargestellt:

- `0` = **Auto**
- `1` = **Manuell**
- `2` = **Nur Zusatzheizung**

Die Schreibfreigabe für **Heizung zulassen** (`3920`) und **Kühlung zulassen** (`3921`) richtet sich nach dem aktuellen Betriebsmodus:

- **Auto (0):** Heizung und Kühlung werden nur gelesen; Schreibversuche werden blockiert.
- **Manuell (1):** Heizung und Kühlung dürfen gelesen und geschrieben werden.
- **Nur Zusatzheizung (2):** Heizung darf gelesen und geschrieben werden; Kühlung wird nur gelesen.

Vor jedem Schreibversuch auf `3920` oder `3921` wird Punkt `3751` gezielt neu gelesen. Dadurch gilt auch eine kurz zuvor direkt an der Anlage oder über myUplink geänderte Betriebsart. Bei nicht erlaubtem Schreiben erzeugt Home Assistant eine Fehlermeldung und es wird kein REST-PATCH an die NIBE gesendet.

## Zusätzliche Anlagenparameter

Zusätzlich integriert wurden:

- Energie: Punkt `829`
- Zusatzheizung/Systemstatus: `1186`, `1820`, `1827`, `3919`, `4064`
- Brauchwasser: `2685`, `3699`–`3711` sowie `3748`
- Heizung: `3749`
- Betriebsmodus: `3751`
- Lüftung: `3841`–`3844`

Punkt `2038` **„Betriebsmodus Brauchwasserkomfort“** wurde ab Version **0.3.25** wieder entfernt, da seine Bedeutung für die getestete Anlage nicht hinreichend eindeutig ist.

Die Punkte `3710` und `3711` gehören zur Brauchwasserzirkulation und werden deshalb als **BWZ Betriebszeit** bzw. **BWZ Stillstandszeit** bezeichnet.

### Periodische Brauchwassererhöhung

Punkt `2685` wird als **„Nächste periodische Brauchwassererhöhung“** dargestellt. Der Rohwert ist die Anzahl der Tage seit dem **01.01.2010**. Beispiel: `6093` entspricht dem **07.09.2026**, `6096` dem **10.09.2026**. Die Anzeige erfolgt bewusst im deutschen Format **DD.MM.YYYY**.

Punkt `3708` **„Startzeit periodisches Brauchwasser“** wird als Home-Assistant-**Time-Entity** bereitgestellt. Der NIBE-Rohwert wird als Sekunden seit Mitternacht interpretiert. Damit entspricht zum Beispiel `34200` der Uhrzeit **09:30**.

Beim Schreiben wird die in Home Assistant gewählte Uhrzeit wieder in Sekunden seit Mitternacht umgerechnet. Beispiel: **09:30 → 34200**. Ab Version 0.4.0 sind beide Umrechnungsrichtungen als eigene, getestete Hilfsfunktionen gekapselt.

## Robustheit und Qualität

Seit Version 0.3.27 verwendet der Coordinator im Einzelpunkt-Fallback nur noch die öffentliche API-Methode `get_point()`. Normale Schreibvorgänge lesen anschließend gezielt nur den betroffenen Punkt zurück. Bei **Mehr Brauchwasser** und **Lüftung +** wird eine noch laufende Bestätigungsprüfung vor einer neuen Prüfung abgebrochen, damit sich schnelle Bedienfolgen nicht durch ältere Hintergrundprüfungen überholen.

Schreibbare Number-Entities verwenden nur belastbare Min-/Max-Grenzen aus den REST-Metadaten. Sind die Grenzen widersprüchlich oder offensichtlich nicht aussagekräftig, wird ein Schreibversuch aus Sicherheitsgründen blockiert.

Ab Version **0.4.0** wurden die Regressionstests erweitert. Geprüft werden unter anderem Skalierung und Rückumrechnung, die Normalisierung verschiedener REST-Antwortformen, die Datumsdekodierung von Punkt `2685`, Betriebsmodus- und Lüftungs-Mappings, die Schreibschutzmatrix für `3920`/`3921`, Zeitumrechnungen sowie die Prüfung von Number-Grenzen. Zusätzlich führt ein GitHub-Actions-Workflow diese Tests bei Pushes und Pull Requests gegen `main` automatisch aus.

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

Aktueller Stand: **0.4.0**

## Hinweise

Die Integration befindet sich noch vor Version 1.0.0 und wird weiter auf der realen Anlage getestet.

Dokumentation, Versionshinweise und Commit-Beschreibungen werden auf **Deutsch** geführt.
