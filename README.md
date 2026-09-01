# NIBE Local REST – Home Assistant Custom Integration

Diese Custom Integration bindet eine NIBE-Anlage über die **lokale REST API** direkt in Home Assistant ein. Sie wurde für eine Anlage mit VVM S320, S2125 und ERS S40-400 entwickelt und wird dort im laufenden Betrieb getestet.

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
- automatische Neuauthentifizierung bei abgelehnten Zugangsdaten
- Home-Assistant-Benachrichtigungen bei Authentifizierungs- und länger anhaltenden Verbindungsfehlern
- eigene Diagnose-Entitäten für REST-API-Erreichbarkeit, Fallback-Status und Zeitpunkte erfolgreicher bzw. fehlgeschlagener Kommunikation

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

Für die Schalter **„Heizung zulassen“** und **„Kühlung zulassen“** prüft die Integration unmittelbar vor jedem Schreibversuch den aktuell von der NIBE gemeldeten Betriebsmodus:

- **Auto:** Beide Schalter sind nur lesbar. Änderungen aus Home Assistant werden gesperrt und es wird kein Schreibbefehl an die NIBE gesendet.
- **Manuell:** Sowohl **Heizung zulassen** als auch **Kühlung zulassen** dürfen aus Home Assistant geändert werden.
- **Nur Zusatzheizung:** **Heizung zulassen** darf geändert werden, **Kühlung zulassen** bleibt nur lesbar.
- **Unbekannter oder nicht verfügbarer Betriebsmodus:** Das Schreiben auf beide Freigaben wird vorsorglich gesperrt.

Der Betriebsmodus wird dafür vor dem Schalten gezielt neu von der Anlage gelesen. Ab Version 0.7.1 muss dieser gezielte Abruf erfolgreich sein. Kann der aktuelle Betriebsmodus nicht sicher geprüft werden, wird die Änderung vorsorglich nicht an die NIBE gesendet. Dadurch kann kein veralteter, zuvor gespeicherter Betriebsmodus versehentlich als Freigabe für einen Schreibvorgang verwendet werden.

## Schreibbare Zahlenwerte

Schreibbare Number-Entitäten verwenden die von der NIBE gelieferten Metadaten für Min-/Max-Grenzen und Schrittweite. Wenn diese Metadaten nicht plausibel sind, wird der Schreibvorgang aus Sicherheitsgründen blockiert.

Ab Version 0.7.1 werden nur positive Divisoren akzeptiert. Zusätzlich werden Werte abgelehnt, die nicht exakt auf die von NIBE vorgegebene Schrittweite abbildbar sind. Damit wird verhindert, dass ein über Service-Aufrufe übergebener Zwischenwert intern stillschweigend auf einen anderen Rohwert gerundet wird.

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

**Hinweis:** Die Alarmdarstellung konnte bislang noch nicht praktisch getestet werden, da während der Entwicklung und des laufenden Tests keine Alarme an der Anlage aufgetreten sind.

## Zugangsdaten und Neuauthentifizierung

Wenn die NIBE REST API die gespeicherten Zugangsdaten ablehnt, erkennt die Integration den Authentifizierungsfehler und startet den Home-Assistant-Reauthentifizierungsablauf.

Im Reauthentifizierungsdialog werden zur besseren Zuordnung der Gerätename, der konfigurierte Host und die aufgelöste IP-Adresse angezeigt. So lassen sich auch fehlerhafte Hostnamen oder Änderungen im Netzwerk leichter erkennen.

Passwort und Authorization-Header werden in den Eingabemasken maskiert dargestellt und nicht mit dem gespeicherten Wert vorausgefüllt. Bleibt eines dieser Felder leer oder besteht nur aus Leerzeichen, wird der bisher gespeicherte Wert beibehalten.

Als Alternative zu Benutzername und Passwort kann ein vollständiger HTTP-Authorization-Header verwendet werden, zum Beispiel `Basic dXNlcjpwYXNzd29ydA==`. Der Wert nach `Basic` muss Base64-codiert sein.

## Home-Assistant-Benachrichtigungen

Die Integration erzeugt bei wichtigen Verbindungsproblemen Persistent Notifications direkt in Home Assistant:

- **Zugangsdaten abgelehnt:** Die Benachrichtigung erscheint sofort und wird pro zusammenhängender Authentifizierungsstörung nur einmal erzeugt. Nach erfolgreicher Kommunikation kann eine spätere neue Störung wieder gemeldet werden.
- **REST API nicht erreichbar:** Eine Benachrichtigung erscheint erst, wenn die Verbindung mindestens **2 Minuten** durchgehend gestört ist. Kurze Netzwerkunterbrechungen erzeugen dadurch keine unnötige Meldung.
- **Verbindung wiederhergestellt:** Eine zuvor erzeugte Verbindungs- oder Authentifizierungsbenachrichtigung wird nach erfolgreicher Kommunikation automatisch entfernt.

Die Meldungen enthalten Gerätename, konfigurierten Host und aufgelöste IP-Adresse. Zugangsdaten oder Authorization-Header werden dabei nicht ausgegeben.

## Diagnose und Verbindungsstatus

Ab Version 0.7.0 stellt die Integration zusätzliche Diagnose-Entitäten am bestehenden NIBE-Gerät bereit. Sie sollen vor allem bei Netzwerkproblemen, Firmware-Updates oder Auffälligkeiten der lokalen REST API helfen.

- **REST API erreichbar:** zeigt, ob der letzte reguläre Coordinator-Abruf erfolgreich war.
- **Einzelpunkt-Fallback aktiv:** zeigt an, ob der Sammel-Endpunkt `/points` aktuell keine verwertbaren Daten liefert und deshalb der Einzelpunkt-Fallback verwendet wird.
- **Letzter erfolgreicher Poll:** Zeitstempel des zuletzt vollständig erfolgreichen regulären Abrufs.
- **Letzter Verbindungsfehler:** Zeitstempel des zuletzt erkannten Verbindungsfehlers zur REST API. Der Wert bleibt auch nach einer erfolgreichen Wiederherstellung erhalten, damit der letzte Ausfall nachvollziehbar bleibt.

Diese Entitäten sind in Home Assistant als **Diagnose-Entitäten** gekennzeichnet. Der Fallback-Status bedeutet nicht automatisch, dass die gesamte REST API ausgefallen ist: Die Integration kann weiterhin Daten über Einzelpunktabfragen liefern, obwohl der Sammel-Endpunkt vorübergehend nicht nutzbar ist.

## Lokale Kommunikation und Polling

Im normalen Betrieb werden die verfügbaren NIBE-Punkte gesammelt über den lokalen REST-Endpunkt abgefragt. Falls diese Sammelabfrage nicht ausgewertet werden kann, nutzt die Integration einen Einzelpunkt-Fallback.

Damit ein dauerhaft gestörter Sammel-Endpunkt nicht unnötig viele Einzelabfragen verursacht, wird der vollständige Einzelpunkt-Fallback mit zunehmender Wartezeit ausgeführt: zunächst nach 30 Sekunden, danach nach 60 Sekunden und anschließend maximal alle 120 Sekunden. Die Sammelabfrage selbst wird weiterhin bei jedem regulären Poll versucht, sodass eine wieder funktionierende REST API sofort erkannt wird.

Der Backoff wird nur verwendet, wenn bereits Punktdaten vorhanden sind, die während der Wartezeit weiter genutzt werden können. Beim Start ohne vorhandene Punktdaten wird der Einzelpunkt-Fallback bei jedem regulären Poll erneut versucht, damit die Integration nicht wegen des Backoffs ohne Daten bleibt.

Wenn während eines Einzelpunkt-Fallbacks nur ein Teil der Werte erfolgreich gelesen werden kann, bleiben zuvor bekannte Werte der übrigen Punkte erhalten.

Nach einem Schreibbefehl wird der betroffene Punkt gezielt neu gelesen, anstatt jedes Mal die komplette Anlage erneut abzufragen. Dadurch werden Schaltvorgänge schneller bestätigt und unnötige REST-Anfragen vermieden.

Bekannte Auswahlwerte werden robust verarbeitet, auch wenn eine Firmware numerische Enum-Werte als Strings statt als Zahlen liefert.

Das Polling-Intervall und die Verzögerung für die Rückmeldung nach Schaltbefehlen können in den Optionen der Integration eingestellt werden.

## Installation

1. Den Ordner `custom_components/nibe_local` nach `/config/custom_components/nibe_local` kopieren.
2. Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste** die Integration **NIBE Local REST** hinzufügen.
4. Host/IP-Adresse, Port, Geräte-ID und Zugangsdaten eintragen.
5. Bei einem lokal selbstsignierten Zertifikat kann die SSL-Zertifikatsprüfung deaktiviert werden.

Ab Version 0.6.0 ist mindestens **Home Assistant 2024.12.0** vorgesehen. Der GitHub-Actions-Testworkflow prüft die Integration sowohl mit dieser Mindestversion als auch mit der jeweils aktuellen Home-Assistant-Version.

## Changelog

Die wesentlichen Änderungen pro Version sind in [`CHANGELOG.md`](CHANGELOG.md) zusammengefasst.

## Hinweise

Die Integration ist ein inoffizielles Community-Projekt und steht in keiner Verbindung zu NIBE.

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

Aktueller Stand: **0.7.2**
