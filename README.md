# NIBE Local REST – Home Assistant Custom Integration

Diese Custom Integration bindet eine NIBE-Anlage über die **lokale REST API** direkt in Home Assistant ein. Sie wurde für eine Anlage mit VVM S320, S2125 und Lüftungsmodul entwickelt und wird dort im laufenden Betrieb getestet.

Die Kommunikation erfolgt lokal im eigenen Netzwerk. Für das normale Auslesen ist keine Cloud-Verbindung zu myUplink erforderlich.

## Was die Integration kann

Die Integration stellt zahlreiche Werte und Funktionen der NIBE-Anlage als Home-Assistant-Entitäten bereit. Dazu gehören unter anderem:

- Temperaturen für Außenluft, Vorlauf, Rücklauf, Raum, Brauchwasser und Lüftung
- Heizungs- und Kühlungswerte einschließlich Gradminuten und berechneten Vorlauftemperaturen
- Verdichterdaten wie Frequenz, Leistung, Strom, Starts und Betriebszeiten
- Energie- und Leistungswerte
- Pumpen- und Hydraulikwerte
- Brauchwasserwerte und Einstellungen
- Lüftungswerte wie Temperaturen, Luftfeuchtigkeit und Ventilatordrehzahlen
- Diagnosewerte der Außeneinheit, EEV/EVI und Abtauung
- Alarm- und Meldungsinformationen
- verschiedene schreibbare Einstellungen als Schalter, Auswahlfelder, Zahlenwerte und Uhrzeiten

Die Entitäten werden von Home Assistant regelmäßig über die lokale REST API aktualisiert. Das Polling-Intervall kann in den Optionen der Integration angepasst werden.

## Lüftung

Für die Lüftung stehen mehrere Mess- und Steuerwerte zur Verfügung. Dazu gehören unter anderem:

- Abluft, Fortluft, Zuluft und Außenlufttemperatur
- Luftfeuchtigkeit
- Ventilatordrehzahl für Abluft und Zuluft
- Lüftungsmodus
- Nachtabsenkung
- Rückstellzeiten für die Lüftungsstufen

### Lüftung +

Die Integration stellt zusätzlich einen komfortablen Schalter **„Lüftung +“** bereit.

Wird der Schalter eingeschaltet, wird die Lüftung auf **Erhöht** gestellt. Beim Ausschalten wird wieder auf **Normal** zurückgeschaltet.

Die Integration prüft anschließend den tatsächlich von der NIBE gemeldeten Lüftungszustand. Dadurch bleibt die Anzeige in Home Assistant auch während der kurzen Verzögerung zwischen Schaltbefehl und Rückmeldung der Anlage stabil.

## Mehr Brauchwasser

Mit **„Mehr Brauchwasser“** kann die zusätzliche Brauchwasserbereitung direkt aus Home Assistant angefordert werden.

Beim Einschalten wird die Funktion an der NIBE aktiviert. Beim Ausschalten wird die Anforderung wieder beendet.

Für die Anzeige wird nicht nur der gesendete Schaltbefehl verwendet. Die Integration berücksichtigt auch die von der Anlage gemeldete verbleibende Laufzeit für „Mehr Brauchwasser“. Dadurch zeigt Home Assistant möglichst zuverlässig den tatsächlichen Zustand der Anlage an.

Zusätzlich stehen weitere Brauchwasserparameter zur Verfügung, zum Beispiel:

- Temperaturen für Brauchwasserbereitung und Speicher oben
- Brauchwasserbedarf
- Start- und Stopptemperaturen
- periodische Brauchwassererhöhung
- Intervall und Startzeit der periodischen Brauchwassererhöhung
- Betriebs- und Stillstandszeit der Brauchwasserzirkulation

## Heizung und Kühlung

Die Integration liest unter anderem Außen-, Vorlauf-, Rücklauf- und Raumtemperaturen sowie Gradminuten und Heizkurvenwerte aus.

Einige Einstellungen können direkt aus Home Assistant geändert werden, zum Beispiel Heizkurve, Heizkurvenverschiebung sowie – abhängig vom Betriebsmodus der NIBE – die Freigabe für Heizung und Kühlung.

Vor sicherheitsrelevanten Schreibvorgängen wird der aktuelle Betriebsmodus der Anlage erneut geprüft. Wenn die NIBE das Schreiben in diesem Modus nicht erlaubt, wird kein Schreibbefehl gesendet.

## Außeneinheit und Verdichter

Für die Außeneinheit werden zahlreiche Betriebs- und Diagnosewerte bereitgestellt, darunter:

- Verdichterstatus
- aktuelle und angeforderte Verdichterfrequenz
- elektrische Leistung und Strom
- Verdichterstarts und Betriebszeiten
- mehrere Kältekreis-Temperaturen
- Ventilatordrehzahl
- Hoch- und Niederdruckwerte
- EEV-/EVI-Werte
- Enteisungsstatus und Enteisungsinformationen

## Energie

Die Integration stellt vorhandene Energie- und Leistungswerte der NIBE als Home-Assistant-Sensoren bereit. Dazu gehören unter anderem der Energiezähler BE6 sowie aktuelle Leistungswerte des Energieprotokolls.

Geeignete Entitäten verwenden die passenden Home-Assistant-State-Classes, damit Langzeitstatistiken und Energieverläufe genutzt werden können.

## Alarme und Meldungen

Aktive NIBE-Meldungen werden nur lesend dargestellt. Neben der Anzahl aktiver Meldungen können – soweit von der REST API geliefert – Alarmnummer, Beschreibung, Schweregrad, Zeitpunkt und Quelle angezeigt werden.

Eine Quittier- oder Reset-Funktion für Alarme ist bewusst nicht enthalten.

## Lokale Kommunikation und Polling

Im normalen Betrieb werden die verfügbaren NIBE-Punkte gesammelt über den lokalen REST-Endpunkt abgefragt. Falls diese Sammelabfrage nicht ausgewertet werden kann, nutzt die Integration einen Einzelpunkt-Fallback.

Nach einem Schreibbefehl wird der betroffene Punkt gezielt neu gelesen, anstatt jedes Mal die komplette Anlage erneut abzufragen. Dadurch werden Schaltvorgänge schneller bestätigt und unnötige REST-Anfragen vermieden.

Das Polling-Intervall und die Verzögerung für die Rückmeldung nach Schaltbefehlen können in den Optionen der Integration eingestellt werden.

## Installation

1. Den Ordner `custom_components/nibe_local` nach `/config/custom_components/nibe_local` kopieren.
2. Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste** die Integration **NIBE Local REST** hinzufügen.
4. Host/IP-Adresse, Port, Geräte-ID und Zugangsdaten eintragen.
5. Bei einem lokal selbstsignierten Zertifikat kann die SSL-Zertifikatsprüfung deaktiviert werden.

## Hinweise

Die Integration ist ein inoffizielles Community-Projekt und steht in keiner Verbindung zu NIBE.

Nicht jede NIBE-Anlage oder Firmware stellt dieselben REST-Punkte zur Verfügung. Welche Entitäten tatsächlich verfügbar sind, hängt deshalb von der jeweiligen Anlage, den angeschlossenen Komponenten und der Firmware ab.

Die Integration befindet sich weiterhin vor Version 1.0 und wird auf einer realen Anlage weiterentwickelt und getestet.

## Haftungs- und Gewährleistungsausschluss

Diese Software wird als Open-Source-Projekt **ohne Gewährleistung oder Garantie** bereitgestellt. Die Nutzung erfolgt **auf eigene Gefahr**.

Die Integration kann Einstellungen einer Heizungs-, Kühlungs-, Lüftungs- und Brauchwasseranlage verändern. Nutzer sind selbst dafür verantwortlich, Änderungen vor der Verwendung zu prüfen und sicherzustellen, dass die eingestellten Werte für ihre konkrete Anlage zulässig und sicher sind.

Bei sicherheitsrelevanten oder kritischen Funktionen dürfen die von dieser Integration angezeigten Werte und Zustände nicht als alleinige Entscheidungsgrundlage verwendet werden. Maßgeblich sind im Zweifel die Anzeigen und Einstellungen am NIBE-Gerät sowie die offizielle Dokumentation des Herstellers.

Soweit gesetzlich zulässig, haften die Autoren und Mitwirkenden nicht für Schäden oder Nachteile, die aus Installation, Konfiguration, Nutzung, Fehlfunktion oder Nichtverfügbarkeit dieser Software entstehen.

Dieser Hinweis ergänzt den Haftungs- und Gewährleistungsausschluss der **MIT-Lizenz**.

## Autoren

- AndiO91
- ChatGPT (OpenAI) – Unterstützung bei Entwicklung, REST-API-Auswertung und Home-Assistant-Integration

## Version

Aktueller Stand: **0.5.1**
