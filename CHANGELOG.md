# Changelog

Alle wesentlichen Änderungen an **NIBE Local REST API** werden hier versionsweise zusammengefasst.

## 0.9.8

- Abtau-Sonderwerte bereinigt: Punkt **840 – Zeit bis Enteisung** zeigt `65535` nicht mehr als Minutenwert und setzt diesen Sonderzustand auch nicht künstlich auf `0 min`; die Entity bleibt erreichbar und der numerische Zustand bleibt in diesem Fall unbekannt.
- Die frühere Heuristik `>720 min → 0` für Punkt 840 wurde vollständig entfernt. Normale REST-Werte werden unverändert als Minuten übernommen.
- Punkt **2022 – Current status** wird als Diagnoseentity behandelt, da der `u32`-Wert als kodierter Status und nicht als gewöhnlicher Messwert einzuordnen ist.
- Punkt **22268 – Letzte Enteisung** kann Enum-Bezeichnungen aus der von der lokalen REST API gelieferten Punktbeschreibung übernehmen; unbekannte Bedeutungen werden nicht geraten oder fest verdrahtet.
- Diagnosedaten enthalten zusätzlich die von der lokalen REST API gelieferten Punktbeschreibungen, damit Sonderzustände und Enum-Bedeutungen nachvollziehbar verifiziert werden können.
- Regressionstests für Abtau-Sonderzustände und REST-basierte Enum-Auswertung ergänzt.
- README und Manifest auf 0.9.8 aktualisiert.

## 0.9.4

- Home-Assistant-Diagnosedaten ergänzt: Supportinformationen zu Profil, Polling, Verbindungs-/Fallback-Status, verfügbaren und aktivierten Variable-IDs sowie ungefährlichen Punkt- und Geräte-Metadaten können über **Diagnosedaten herunterladen** exportiert werden. Host/IP, Benutzername, Passwort, Authorization-Header, Seriennummern, aktuelle Mess-/Einstellwerte und Alarmtexte werden bewusst nicht ausgegeben.
- CI-Härtung ergänzt: Ruff prüft auf undefinierte Python-Namen (`F821`), zusätzlich laufen weiterhin JSON-Prüfung, `compileall` und pytest gegen **Home Assistant 2024.12.0** und **latest**.
- Migrationsschutz verbessert: Config-Entry-Versionssprünge werden per Regressionstest nur noch zugelassen, wenn ein `async_migrate_entry`-Handler vorhanden ist.
- Plattform-Smoke-Test ergänzt, der alle deklarierten Home-Assistant-Plattformmodule importiert und damit Import-/Setup-Regressionen früher sichtbar macht.
- Diagnosedaten werden per Regressionstest auf unbeabsichtigte Preisgabe sensibler Zugangsdaten und Netzwerkziele geprüft.
- README um Installationsvoraussetzungen für die lokale NIBE REST API erweitert: mindestens Home Assistant 2024.12.0, NIBE S-Series mit lokaler REST API, Firmware 4.4.7 als technische Mindestbasis und Empfehlung einer aktuellen S-Series-Firmware.
- Einrichtung der NIBE-Schnittstelle dokumentiert: Die lokale REST API muss an der Inneneinheit bzw. Steuerung unter **Menü 7 → Service → 7.5.15 – Lokale REST API** aktiviert und mit Zugangsdaten eingerichtet sein; standardmäßig wird HTTPS auf Port 8443 verwendet.
- Einrichtungs- und Optionshinweise an den aktuellen Ablauf angepasst, einschließlich Mehrfachauswahl bei **Individuell**, abschließender Entitätsübersicht und Bestätigung über **OK**.
- Erklärung der Entitätsbenennung **Home-Assistant-Standard / Lokale API / Technisch** mit verständlichen Beispielen verbessert.
- Lokale Home-Assistant-Branding-Dateien für Icon und Logo überarbeitet und an den aktuellen Integrationsauftritt angepasst.
- Versehentlich eingecheckte Python-Cache-Dateien entfernt und über `.gitignore` dauerhaft ausgeschlossen.

## 0.9.3

- Neuer letzter Schritt **Entitätsübersicht** bei Ersteinrichtung und Optionen: Vor dem Anwenden werden aktive/ausgewählte, abgewählte/beibehaltene und zur Registry-Löschung vorgesehene Punkt-Entitäten mit Name, Variable-ID und Einheit angezeigt.
- Bei bestehenden Installationen zeigt die Vorschau zusätzlich, wie viele aktive Punkte bereits in der Entity Registry vorhanden bzw. neu sind; Diagnose- und Spezialentitäten werden separat aufgeführt.
- Große Vorschaugruppen werden auf 50 sichtbare Einträge begrenzt, während die Zähler weiterhin den vollständigen Umfang anzeigen.
- Backup und Registry-Bereinigung werden erst nach der finalen Bestätigung ausgeführt. Ein Abbruch der Vorschau verändert die Registry nicht; ein fehlgeschlagenes angefordertes Backup verhindert weiterhin jede Löschung.
- Regressionstests für Vorschaugruppierung und die verzögerte Cleanup-Ausführung ergänzt.

## 0.9.2

- Binärsensor-Plattform repariert: `entity_unique_id` wird wieder korrekt importiert. Der fehlende Import in 0.9.1 verhinderte das Setup der gesamten `binary_sensor`-Plattform und ließ unter anderem **REST API erreichbar**, **Einzelpunkt-Fallback aktiv**, Kühl-/Abtauzustände, Pumpen- und weitere Binärsensoren als nicht verfügbar erscheinen.
- Regressionstest ergänzt, der sicherstellt, dass der für Diagnose-Binärsensoren benötigte Unique-ID-Helper im Plattformmodul verfügbar ist.

## 0.9.1

- **Individuell** verwendet jetzt eine direkt anklickbare Mehrfachliste im Home-Assistant-Listenmodus, sodass Variablen per Checkbox an- und abgewählt werden können.
- Bekannte NIBE-Punkte werden in der individuellen Auswahl mit dem lokalisierten Home-Assistant-Namen, der Variable-ID und – sofern vorhanden – der Einheit angezeigt. Bei unbekannten Punkten wird ein von der lokalen API gelieferter Name verwendet, falls die API einen bereitstellt.
- Die gespeicherte Auswahl bleibt weiterhin ausschließlich auf stabilen numerischen Variable-IDs basiert; alte 0.9.0-Auswahlwerte werden beim Einlesen weiterhin akzeptiert.

## 0.9.0

- Entitätsprofile final geschärft: **Minimal** konzentriert sich auf Betriebsmodus/-priorität, Haupt- und Brauchwassertemperaturen, Verdichterstatus und Verdichterfrequenz; **Standard** ergänzt normale Bedienung, Komfort-, Energie- und Betriebsdiagnosewerte, während technische Druck-/Elektronik-, Zusatzheizungs- und detaillierte Service-/Abtauwerte **Erweitert** vorbehalten bleiben.
- Punkt **116 – Brauchwasseraustritt (BT70)** als bekannter schreibgeschützter Temperatursensor ergänzt und in Minimal aufgenommen.
- **Mehr Brauchwasser** und **Lüftung+** bleiben im Standardprofil als alltagstaugliche Bedienfunktionen verfügbar.
- Authentifizierung in Einrichtung und Optionen in zwei Schritte getrennt: Nach Wahl der Methode werden nur Benutzername + Passwort oder nur der Authorization-Header angezeigt.
- Optionale Registry-Bereinigung ergänzt: Abgewählte Punkt-Entitäten werden nur auf ausdrücklichen Wunsch aus der Entity Registry entfernt; standardmäßig bleiben sie für stabile Entity-IDs erhalten.
- Registry-Bereinigung zusätzlich abgesichert: Home-Assistant-Backup ist davor standardmäßig aktiviert; ohne Backup muss der Nutzer die vorausgewählte Option bewusst abschalten. Bei fehlgeschlagenem Backup erfolgt keine Löschung.
- Upgrade-Kompatibilität zu bestehenden 0.8.x-Config-Entries abgesichert: Die Config-Entry-Schema-Version bleibt bei `1`, da die neuen 0.9.0-Felder optional sind und über Defaults eingelesen werden. Damit ist kein `async_migrate_entry` erforderlich; ein Regressionstest schützt vor unbeabsichtigten Versionssprüngen.
- Bei der Einrichtung und in den Optionen kann die Entitätsbenennung zwischen **Home-Assistant-Standard**, **Lokale API** und **Technisch** gewählt werden. Home Assistant behält die Kontrolle über das endgültige Entity-ID-Format.
- Die Profilauswahl zeigt die Anzahl der auf dem verbundenen Gerät tatsächlich verfügbaren Variablen für Minimal, Standard, Erweitert, Komplett und Individuell an.
- Neue Entitätsprofile **Minimal**, **Standard**, **Erweitert**, **Komplett** und **Individuell** bei der Einrichtung.
- Nach erfolgreicher Authentifizierung liest der Config Flow die aktuell verfügbaren NIBE-Variablen ein; bei **Individuell** können die gewünschten Variablen per Mehrfachauswahl festgelegt werden.
- Die Profilwahl und individuelle Variable-IDs werden dauerhaft im Config Entry gespeichert und bleiben bei Neustarts, Reloads und Integrationsupdates erhalten.
- Die Entitätsauswahl kann später über die Integrationsoptionen geändert werden. Bestehende Installationen ohne Profilfeld verwenden automatisch **Erweitert**, damit der bisherige Entitätsumfang erhalten bleibt.
- **Komplett** stellt alle vom Gerät gemeldeten Punkte bereit. Noch nicht kuratierte Variablen werden ausschließlich als generische, schreibgeschützte Sensoren angelegt; unbekannte Servicepunkte erhalten keine automatische Schreibfunktion.

## 0.8.1

- Sicherheits-Härtung der REST-Antwortverarbeitung: JSON-Antworten sind auf 4 MiB begrenzt und übergroße Antworten werden kontrolliert als API-Fehler behandelt.
- Die Normalisierung von `/points` arbeitet iterativ mit maximaler Verschachtelungstiefe und kann dadurch nicht mehr durch extrem tief verschachtelte Antworten einen `RecursionError` auslösen.
- Entity-Unique-IDs und Persistent-Notification-IDs sind jetzt pro Config Entry getrennt, sodass mehrere NIBE-Anlagen keine Kollisionen verursachen. Bestehende Entity-IDs bleiben durch eine Registry-Migration erhalten.
- Regressionstests für Verschachtelungslimits, zyklische Strukturen, Response-Limit und Multi-Instance-Unique-IDs ergänzt.

## 0.8.0

- Die hellen Icon-Varianten besitzen jetzt einen vollständig transparenten Hintergrund.
- Die NIBE-Geräte-ID ist jetzt fest auf `0` gesetzt und wird weder bei der Einrichtung noch in den Optionen angeboten.
- Eine explizite Authentifizierungsmethode trennt **Benutzername + Passwort** und **Authorization-Header**. Beim Methodenwechsel werden Zugangsdaten der inaktiven Methode entfernt; bestehende Einträge ohne Methodenfeld werden kompatibel anhand des vorhandenen Headers eingeordnet.
- Der Reauthentifizierungsdialog fragt nur noch die Zugangsdaten der aktiven Authentifizierungsmethode ab.
- Smart Mode und die Meldungs-/Alarm-Entität werden demselben Home-Assistant-Gerät wie die übrigen NIBE-Entitäten zugeordnet.
- Das Attribut `last_successful_poll` wurde von **REST API erreichbar** entfernt. Der Zeitpunkt bleibt coordinatorintern verfügbar, ohne bei jedem erfolgreichen Poll Recorder-Änderungen an dieser Entity zu erzeugen.
- NIBE-Einheiten werden für Home Assistant normalisiert: `%RH` → `%` und `l/min` → `L/min`; Volumenstrom erhält damit eine passende Home-Assistant-Device-Class. Die Humidity-Device-Class wird nur aus der ursprünglichen NIBE-Einheit `%RH`, nicht aus beliebigen Prozentwerten abgeleitet.
- Schreibzugriffe auf die NIBE REST API werden integrationsweit über einen gemeinsamen Lock serialisiert. Zusätzlich verwenden schreibende Plattformen `PARALLEL_UPDATES = 1`, während coordinatorbasierte Leseplattformen `PARALLEL_UPDATES = 0` verwenden.
- Ungültige Select-Optionen erzeugen jetzt einen übersetzbaren `HomeAssistantError` statt eines hart codierten englischen `ValueError`.
- Das Zusatzattribut `group` verwendet sprachneutrale Schlüssel (`system`, `heating`, `cooling`, `hot_water`, `energy`, `hydraulics`, `heat_pump`, `eev_defrost`, `ventilation`).
- Alarmtexte aus der NIBE werden bevorzugt, damit die Gerätesprache erhalten bleibt. Verifizierte deutsche Alarmtexte dienen nur bei deutscher Home-Assistant-Sprache als Fallback; andere Sprachen und unbekannte Alarme ohne Gerätetext erhalten einen sprachneutralen `Alarm <Nummer>`-Fallback.
- Regressionstests für feste Geräte-ID, Authentifizierungsmethoden, serialisierte Schreibzugriffe, Parallelitätsgrenzen, Einheitennormalisierung, Alarm-Fallbacks, Gruppen und übersetzbare Select-Fehler ergänzt.
- Legacy-Migration für alte `nibe_vvm_s320_*`-Entity-IDs entfernt. Bereits bestehende aktuelle `nibe_api_*`-Entity-IDs bleiben erhalten; für eine frische Installation wird kein exaktes Entity-ID-Präfix garantiert, da Home Assistant die IDs aus Geräte- und Entitynamen erzeugt.
- Automatische Entfernung des früheren Standalone-Sensors `last_successful_poll` aus der Entity Registry entfernt; die eigene Installation wurde bereits bereinigt.
- Nicht mehr benötigte Kompatibilitäts-Exporte `FRIENDLY_NAMES`, `OPERATING_MODE_MAP` und `ENUM_LABELS` entfernt.
- Nicht mehr verwendetes internes `POINT_BY_ID`-Lookup entfernt; `POINTS` bleibt die zentrale Definition aller NIBE-Punkte.
- Spezialschalter verwenden ihre benötigten Punktdefinitionen jetzt direkt aus `POINTS`; damit bleibt der Code nach Entfernung von `POINT_BY_ID` konsistent.
- Harte deutsche Namensüberschreibungen für die BWZ-Zeitwerte entfernt; auch diese Number-Entitäten verwenden jetzt ausschließlich die vorhandenen Home-Assistant-Übersetzungen.
- Veraltete `strings.json` entfernt. Custom Integrations laden ihre Übersetzungen direkt aus `translations/<sprache>.json`.
- Sprachabhängigen Fallbacktext `nicht auflösbar` im Reauth-Dialog durch einen neutralen Gedankenstrich ersetzt.
- Spezialschalter **Lüftung +** verwendet jetzt einen eigenen Translation Key statt eines fest im Python-Code gesetzten deutschen Namens.
- Benutzernahe Fehler beim Schreiben von Switch- und Number-Entitäten werden über Home Assistants übersetzbare `HomeAssistantError`-Mechanik ausgegeben.
- Persistent Notifications für Authentifizierungs- und Verbindungsfehler verwenden die deutsche bzw. englische Übersetzungsdatei; der Notification-Titel bleibt sprachneutral.
- Alle konfigurierten Point-Selects besitzen jetzt explizite Enum-Mappings. Der ungenutzte generische Min-/Max-Fallback für unbekannte Selects wurde entfernt und durch einen Regressionstest abgesichert.
- Redundante Hilfsfunktionen für bereits separat geprüfte Schreibfreigaben, Auth-Benachrichtigungen und den Lüftungs-Punktrefresh entfernt; die Aufrufe nutzen jetzt direkt die zugrunde liegende Logik.
- Regressionstests auf die aktuelle, sprachneutrale Select-State-Struktur umgestellt.
- Interne Setup- und Entity-Basis vereinfacht; Point-IDs, Unique IDs, Translation Keys bestehender Punkt-Entitäten und aktuelle Entity-IDs bleiben unverändert.

## 0.7.5

- Deutsche und englische Entitätsnamen systematisch vereinheitlicht: Temperaturen, Pumpen, Verdichter, Lüftung, Brauchwasser sowie EEV-/Abtauwerte verwenden jetzt konsistente und besser lesbare Bezeichnungen.
- Geräte- und Einrichtungs-Fallback auf **NIBE API** neutralisiert, da der lokale `/devices/{id}`-Endpunkt nicht auf allen Anlagen einen Produktnamen liefert.
- Bereits registrierte, automatisch erzeugte Entity-IDs werden beim Setup auf sprachneutrale IDs im Schema `<domain>.nibe_api_<translation_key>` migriert. Beispielsweise wird `sensor.nibe_vvm_s320_aktuelle_aussenlufttemperatur_bt1` zu `sensor.nibe_api_outdoor_temperature_bt1`.
- Die Entity-ID-Migration basiert auf den unveränderten Unique IDs bzw. NIBE-Punktnummern. Benutzerdefinierte Entity-IDs mit einem anderen Präfix werden nicht verändert; bei Namenskollisionen wird die vorhandene Entity-ID beibehalten und eine Warnung protokolliert.
- Repository-Verweise im Manifest auf **AndiO91/HA-Nibe-Local-REST-API** aktualisiert.

## 0.7.4

- Integrationsname in HACS, Home Assistant, Übersetzungen und Dokumentation auf **NIBE Local REST API** vereinheitlicht.
- Entitätsnamen werden über Home-Assistant-Übersetzungen statt fest im Python-Code gesetzter deutscher Namen bereitgestellt.
- Deutsche und englische Übersetzungen für Sensoren, Binärsensoren, Schalter, Number-, Select- und Time-Entitäten ergänzt.
- Diagnose-Entitäten und Smart Mode vollständig in die Übersetzungsstruktur aufgenommen.
- Zustände von Betriebspriorität, Betriebsmodus und Abtauanforderung auf stabile, übersetzbare `snake_case`-Werte umgestellt.
- Select-Zustände für Betriebsmodus, Lüftung und Brauchwasserbedarf auf stabile, übersetzbare Werte umgestellt.
- Fehlende deutsche Übersetzung für `already_configured` ergänzt.
- **Letzter erfolgreicher Poll** wird nicht mehr als eigener Timestamp-Sensor angelegt, sondern als Attribut `last_successful_poll` des Diagnose-Binärsensors **REST API erreichbar** bereitgestellt. Dadurch erzeugt jeder erfolgreiche Poll keinen eigenen Eintrag mehr im Aktivitätenprotokoll.
- Hochauflösende `icon@2x.png`- und `dark_icon@2x.png`-Branding-Dateien ergänzt.

## 0.7.3

- Lokale Light-/Dark-Branding-Dateien für Home Assistant ergänzt und Dateinamen vereinheitlicht.
- Integrationsversion für die HACS-Veröffentlichung angehoben.

## 0.7.2

- Wiederholte Authentifizierungsfehler erzeugen die Persistent Notification und die zugehörige Host-/IP-Auflösung nur einmal pro zusammenhängender Störung; nach erfolgreicher Kommunikation kann eine neue Störung wieder gemeldet werden.
- Nur aus Leerzeichen bestehende Passwort- oder Authorization-Header-Eingaben gelten als leer und behalten den gespeicherten Wert bei; echte nichtleere Eingaben werden unverändert übernommen.
- Regressionstests für Auth-Benachrichtigungen und den Umgang mit Zugangsdaten erweitert.
- Integrationslogo unter `docs/logo.png` ergänzt.

## 0.7.1

- Einzelpunkt-Fallback wird beim Start ohne vorhandene Punktdaten nicht mehr durch den Backoff verzögert.
- Schreibschutz für **Heizung zulassen** und **Kühlung zulassen** verschärft: Vor dem Schreiben muss der aktuelle Betriebsmodus erfolgreich neu gelesen werden.
- Bekannte Select-Werte werden auch dann korrekt zugeordnet, wenn die REST API numerische Enum-Werte als Strings liefert.
- Number-Entitäten akzeptieren nur positive Divisoren und blockieren Werte, die nicht exakt zur von NIBE vorgegebenen Schrittweite passen.
- Regressionstests für Fallback, Schreibschutz, Select-Enums und Number-Grenzfälle erweitert.
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
