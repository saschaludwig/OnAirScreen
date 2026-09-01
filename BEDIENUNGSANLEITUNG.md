# OnAirScreen – Bedienungsanleitung

**Version:** 1.0.0beta5  
**Autor:** Sascha Ludwig, [astrastudio.de](http://www.astrastudio.de)  
**Projekt:** [OnAirScreen](https://www.astrastudio.de/onairscreen/)  
**English version:** [USER_MANUAL.md](USER_MANUAL.md)

---

## Inhaltsverzeichnis

1. [Überblick](#1-überblick)
2. [Installation und Start](#2-installation-und-start)
3. [Hauptbildschirm](#3-hauptbildschirm)
4. [Tastaturkürzel (Hotkeys)](#4-tastaturkürzel-hotkeys)
5. [Einstellungsdialog](#5-einstellungsdialog)
6. [Funktionen im Detail](#6-funktionen-im-detail)
7. [Fernsteuerung und API](#7-fernsteuerung-und-api)
8. [Presets (Profile)](#8-presets-profile)
9. [Kommandozeilenoptionen](#9-kommandozeilenoptionen)
10. [Konfigurationsspeicherort](#10-konfigurationsspeicherort)
11. [Fehlerbehebung](#11-fehlerbehebung)

---



## 1. Überblick

OnAirScreen ist eine vielseitige **On-Air-Lampe** für professionelle Broadcast-Umgebungen. Die Anwendung kombiniert:

- **4 Status-LEDs** (ein-/ausschaltbar, blinkend, zeitgesteuert)
- **4 AIR-Timer** (Mikrofon, Telefon, Radio-Timer, Stream-Timer); AIR3 mit ▲/▼ und Top-of-Hour
- **Digitale oder analoge Uhr** mit optionalem Textuhr-Modus und Lock-LED (Local / NTP / PTP / LTC)
- **Stereo-Audio-Meter** (lokaler Eingang, Axia Livewire oder AES67 AoIP): L/R, Programme-LUFS oder beides, optional I+LRA
- **Silence Detection** mit optionalem WARN auf dem Bildschirm und Boolean in API/MQTT
- **Instanzname** (DNS-sicher, z. B. `Studio-1`) zur Unterscheidung mehrerer OnAirScreens
- **Textzeilen** NOW, NEXT und WARN (mit Prioritätssystem)
- **Wetter-Widget** (OpenWeatherMap)
- **Fernsteuerung** per Tastatur, Maus (Doppelklick/Rechtsklick), UDP, HTTP, Web-UI, MQTT, OSC, REST-API und Bitfocus Companion
- **Home-Assistant-Integration** via MQTT Autodiscovery

Die Anwendung startet standardmäßig im **Vollbildmodus** mit ausgeblendetem Mauszeiger und eignet sich für dedizierte Studio-Monitore, Raspberry-Pi-Setups und Touch-freie Bedienung.

OnAirScreen passt sich automatisch an verschiedene Monitor-Seitenverhältnisse an und funktioniert sowohl auf **4:3**- als auch auf **16:9/16:10**-Displays.

---



## 2. Installation und Start



### Voraussetzungen

- **Python 3.11+** mit PySide6 (bei Installation aus dem Quellcode)
- Abhängigkeiten: siehe `requirements.txt`
- Netzwerkzugriff für UDP/HTTP/MQTT/OSC-Fernsteuerung (optional)



### Start aus dem Quellcode

```bash
python start.py
```



### Vorkompilierte Versionen

Fertige Binaries für Windows, Linux, macOS und Raspberry Pi sind über [astrastudio.de/shop](https://www.astrastudio.de/shop/) erhältlich.

### Erster Start

Beim ersten Start werden Standardeinstellungen geladen. Der Einstellungsdialog öffnet sich mit `Ctrl+S` (macOS: `Cmd+S`). Änderungen werden erst nach Klick auf **Apply** übernommen und gespeichert.

---



## 3. Hauptbildschirm

Der Hauptbildschirm ist in folgende Bereiche gegliedert:

![OnAirScreen Hauptbildschirm](https://www.astrastudio.de/wp-content/uploads/2026/08/OAS_Screenshot_1.0.0.png)


### Bereiche im Detail


| Bereich             | Widget                    | Funktion                                                   |
| ------------------- | ------------------------- | ---------------------------------------------------------- |
| **Stationsname**    | `labelStation`            | Name des Senders, Farbe konfigurierbar                     |
| **Slogan**          | `labelSlogan`             | Untertitel / Claim des Senders                             |
| **Status-LEDs 1–4** | `buttonLED1`–`buttonLED4` | Große farbige Statusanzeigen (ON AIR, PHONE, …)            |
| **Audio-Meter**      | `audioMeterWidget`       | L/R und/oder Programme-LUFS am linken Rand (optional)     |
| **Uhr**             | `clockWidget`             | Digital oder analog, mit Logo und optionalem Wetter-Widget |
| **Lock-LED**        | Clock lock                | Unten rechts: `PTP/NTP/LTC LOCK` oder `LOCAL`              |
| **AIR-Timer 1–4**   | `AirLED_1`–`AirLED_4`     | Stoppuhr-Timer mit Icon, Label, MM:SS; AIR3 mit ▲/▼       |
| **NOW**             | `labelCurrentSong`        | Erste Fußzeile (z. B. aktueller Songtitel)                 |
| **NEXT**            | `labelNews`               | Zweite Fußzeile (z. B. nächster Titel)                     |
| **WARN**            | `labelWarning`            | Warnmeldung; blendet NOW/NEXT aus, wenn aktiv              |


> **Hinweis:** Die Status-LEDs und AIR-Timer werden primär per **Tastatur** oder **Fernsteuerung** bedient.



### Vollbildmodus

- Standard: Vollbild mit verstecktem Mauszeiger
- Umschalten: `F` oder `Ctrl+F` (macOS: `Cmd+F`), **Doppelklick** auf den Hauptbildschirm, oder Rechtsklick → **Toggle Fullscreen**
- **Rechtsklick-Menü:** Toggle Fullscreen, Settings; bei aktiven Metern zusätzlich **Reset I+LRA**
- Der Vollbild-Zustand wird in den Einstellungen (`General/fullscreen`) gespeichert
- Im Fenstermodus werden Position und Größe gespeichert (`Window/geometry`) und beim nächsten Start wiederhergestellt

---



## 4. Tastaturkürzel (Hotkeys)

> Auf **macOS** wird `Ctrl` durch `Cmd (⌘)` ersetzt.



### Anwendung


| Taste(n)                          | Funktion                                         |
| --------------------------------- | ------------------------------------------------ |
| `F` / `Ctrl+F`                    | Vollbild ein/aus                                 |
| `Ctrl+S` / `Ctrl+,`               | Einstellungsdialog öffnen                        |
| `Q` / `Ctrl+Q` / `Ctrl+C` / `ESC` | OnAirScreen beenden                              |
| `I`                               | IP-Adressen für 10 Sekunden in NOW/NEXT anzeigen |




### Status-LEDs


| Taste | Funktion      |
| ----- | ------------- |
| `1`   | LED 1 ein/aus |
| `2`   | LED 2 ein/aus |
| `3`   | LED 3 ein/aus |
| `4`   | LED 4 ein/aus |




### AIR-Timer


| Taste(n)                | Funktion                      | Timer               |
| ----------------------- | ----------------------------- | ------------------- |
| `M` / `/`               | Start/Stopp                   | AIR1 (Mikrofon)     |
| `P` / `*`               | Start/Stopp                   | AIR2 (Telefon)      |
| `Leertaste` / `,` / `.` | Start/Stopp                   | AIR3 (Radio-Timer)  |
| `S`                     | Start/Stopp                   | AIR4 (Stream-Timer) |
| `0` / `R`               | Zurücksetzen auf 0:00         | AIR3 (Radio-Timer)  |
| `Alt+S`                 | Zurücksetzen auf 0:00         | AIR4 (Stream-Timer) |
| `T`                     | Top-of-Hour-Countdown ein/aus | AIR3                |
| `Enter` / `Return`      | Timer-Eingabedialog öffnen    | AIR3                |




### OAS-USB-Tastatur (Sonderbelegung)


| Taste            | Funktion                              |
| ---------------- | ------------------------------------- |
| Display-Taste    | Vollbild ein/aus                      |
| Calculator-Taste | Host herunterfahren (`shutdown_host`) |


---



## 5. Einstellungsdialog

Der Einstellungsdialog öffnet sich mit `Ctrl+S` oder `Ctrl+,` (oder Rechtsklick → **Settings**). Ist er bereits offen, kommt das Fenster nach vorne, ohne die Werte neu zu laden. Laufende AIR-Timer (inkl. TOTH) bleiben dabei unverändert. Der Dialog enthält **mehrere Registerkarten** (vertikal links angeordnet):


| Register              | Inhalt                                 |
| --------------------- | -------------------------------------- |
| **General**           | Instanzname, Station, LEDs, Uhr, Logo, Updates |
| **Network**           | UDP, HTTP, Multicast, MQTT, OSC       |
| **Time Source**       | Local / NTP / PTPv2 / LTC, NTP-Prüfung |
| **Advanced**          | Formatierung, Wetter                   |
| **Timers**            | AIR-Timer 1–4                          |
| **Fonts**             | Schriftarten für alle Elemente         |
| **Audio Meters**      | Pegelanzeige, Quelle, TooLoud, Silence Detection |
| **About**             | Version, Lizenzinfo, Log-Level, Log-Ordner, Reset  |
| **License**           | OASL 1.0 und Third-Party-Hinweise (PySide6/Qt, Fonts, Beispiele) |




### Schaltflächen (unten)


| Schaltfläche         | Funktion                                                      |
| -------------------- | ------------------------------------------------------------- |
| **Quit**             | OnAirScreen beenden                                           |
| **Delete Preset...** | Gespeichertes Preset löschen                                  |
| **Load Preset...**   | Preset laden                                                  |
| **Save Preset...**   | Aktuelle Konfiguration als Preset speichern                   |
| **Close**            | Dialog schließen **ohne** zu speichern (Änderungen verwerfen) |
| **Apply**            | Alle Einstellungen übernehmen, speichern und Dialog schließen |


---



### 5.1 General



#### Instanzname


| Einstellung   | Schlüssel              | Standard    | Beschreibung |
| ------------- | ---------------------- | ----------- | ------------ |
| Instance Name | `General/instancename` | `Studio-1`  | DNS-sicheres Label (1–32 Zeichen, Buchstaben/Ziffern/Bindestrich, kein führendes oder nachgestelltes `-`) zur Identifikation dieses OnAirScreens |


Der Instanzname erscheint in der Web-UI (Titel und Status), in `/api/status` (`instance`), auf MQTT `{base}/instance/state` und als Home-Assistant-Sensor. Der HA-Gerätename wird zu `OnAirScreen (Studio-1)`, sofern der Instanzname nicht schon im Device Name steht. Remote: `CONF:General:instancename=TEXT`.

#### Stationsname und Slogan


| Einstellung   | Schlüssel              | Standard                          | Beschreibung           |
| ------------- | ---------------------- | --------------------------------- | ---------------------- |
| Station Name  | `General/stationname`  | `Radio Eriwan`                    | Name des Senders       |
| Station Color | `General/stationcolor` | `#FFAA00`                         | Textfarbe Stationsname |
| Slogan        | `General/slogan`       | `Your question is our motivation` | Slogan / Claim         |
| Slogan Color  | `General/slogancolor`  | `#FFAA00`                         | Textfarbe Slogan       |


Eine Live-Vorschau (`StationNameDemo`, `SloganDemo`) zeigt die Eingaben sofort an.

#### Status-LEDs 1–4

Für jede LED (Gruppen `LED1`–`LED4`):


| Einstellung       | Schlüssel         | Standard    | Beschreibung                              |
| ----------------- | ----------------- | ----------- | ----------------------------------------- |
| Aktiviert         | `used`            | `true`      | LED auf dem Hauptbildschirm anzeigen      |
| Text              | `text`            | siehe unten | Beschriftung der LED                      |
| Active BG Color   | `activebgcolor`   | `#FF0000`   | Hintergrundfarbe (aktiv)                  |
| Active Text Color | `activetextcolor` | `#FFFFFF`   | Textfarbe (aktiv)                         |
| Autoflash         | `autoflash`       | `false`     | Dauerblinken alle 500 ms                  |
| 20sec flash       | `timedflash`      | `false`     | 20 Sekunden blinken, dann automatisch aus |


**Standard-LED-Texte:**


| LED  | Text       |
| ---- | ---------- |
| LED1 | ON AIR     |
| LED2 | PHONE      |
| LED3 | DOORBELL   |
| LED4 | EAS ACTIVE |


**Gemeinsame inaktive Farben** (Gruppe `LEDS`):


| Einstellung         | Schlüssel           | Standard  |
| ------------------- | ------------------- | --------- |
| Inactive BG Color   | `inactivebgcolor`   | `#222222` |
| Inactive Text Color | `inactivetextcolor` | `#555555` |




#### Logo


| Einstellung   | Schlüssel         | Standard                 | Beschreibung                    |
| ------------- | ----------------- | ------------------------ | ------------------------------- |
| Logo Path     | `Clock/logopath`  | `:/astrastudio_logo/...` | Pfad zum Logo-Bild              |
| Logo Position | `Clock/logoUpper` | `false` (unten)          | Logo oben oder unten in der Uhr |


Schaltflächen: `...` (Dateiauswahl), `reset` (Standard-Logo wiederherstellen).

#### OnAir Clock Mode / Colors


| Einstellung           | Schlüssel                    | Standard         | Beschreibung                          |
| --------------------- | ---------------------------- | ---------------- | ------------------------------------- |
| Digital / Analog      | `Clock/digital`              | `true` (Digital) | Uhrenmodus                            |
| Hours LEDs            | `Clock/digitalhourcolor`     | `#3232FF`        | Farbe Stunden-LEDs                    |
| Seconds LEDs          | `Clock/digitalsecondcolor`   | `#FF9900`        | Farbe Sekunden-LEDs                   |
| Digits LEDs           | `Clock/digitaldigitcolor`    | `#3232FF`        | Farbe aller Ziffern                   |
| Show seconds          | `Clock/showSeconds`          | `false`          | Sekunden anzeigen                     |
| Seconds Layout        | `Clock/showSecondsInOneLine` | `false`          | `separate` oder `in one line`         |
| Static colon          | `Clock/staticColon`          | `false`          | Doppelpunkt statisch (nicht blinkend) |
| Use textclock         | `Clock/useTextClock`         | `true`           | Textuhr (z. B. „it's 3 o'clock")      |
| Replace IPs after 10s | `General/replacenow`         | `false`          | Nach IP-Anzeige Text ersetzen         |
| Replace with text     | `General/replacenowtext`     | *(leer)*         | Ersatztext für NOW-Zeile              |




#### Update-Prüfung (kompilierte Versionen)


| Einstellung           | Schlüssel                   | Standard | Beschreibung                                                          |
| --------------------- | --------------------------- | -------- | --------------------------------------------------------------------- |
| Check for updates     | `General/updatecheck`       | `false`  | Automatische Update-Prüfung beim Start                                |
| Update Key            | `General/updatekey`         | *(leer)* | Update-Schlüssel für kostenpflichtige Versionen (siehe Hinweis unten) |
| Include Beta Versions | `General/updateincludebeta` | `false`  | Beta-Versionen einschließen                                           |


> Die Update-Funktion ist für **vorkompilierte (kostenpflichtige) Versionen** gedacht.
>
> Für die Update-Prüfung in der kostenpflichtigen Version muss ein **Update Key** eingegeben werden. Diesen erhältst du nach der Bestellung im Kundenportal unter [customer.astrastudio.de](https://customer.astrastudio.de). Das Feld ist maskiert; mit dem durchgestrichenen Auge wird es sichtbar.

---

### 5.2 Network



#### UDP / HTTP / Multicast


| Einstellung       | Schlüssel                   | Standard      | Beschreibung              |
| ----------------- | --------------------------- | ------------- | ------------------------- |
| UDP Port          | `Network/udpport`           | `3310`        | Port für UDP-Befehle      |
| HTTP Port         | `Network/httpport`          | `8010`        | Port für HTTP/Web-UI      |
| Multicast Address | `Network/multicast_address` | `239.194.0.1` | Multicast-Adresse für UDP  |


#### MQTT


| Einstellung         | Schlüssel             | Standard      | Beschreibung                  |
| ------------------- | --------------------- | ------------- | ----------------------------- |
| enable MQTT support | `MQTT/enablemqtt`     | `false`       | MQTT-Integration einschalten  |
| MQTT Server         | `MQTT/mqttserver`     | `localhost`   | Broker-Hostname/IP           |
| MQTT Server Port    | `MQTT/mqttport`       | `1883`        | Broker-Port                   |
| MQTT User           | `MQTT/mqttuser`       | *(leer)*      | Benutzername (optional)      |
| MQTT Password       | `MQTT/mqttpassword`   | *(leer)*      | Passwort (optional)           |
| MQTT Device Name    | `MQTT/mqttdevicename` | `OnAirScreen` | Gerätename in Home Assistant  |


MQTT-Passwort und API-Keys sind maskiert; mit dem durchgestrichenen Auge werden sie sichtbar.

**MQTT Base Topic:** `onairscreen` + letzte 6 Hex-Zeichen der MAC-Adresse, z. B. `onairscreen_a1b2c3`.

#### OSC


| Einstellung        | Schlüssel          | Standard  | Beschreibung                                                |
| ------------------ | ------------------ | --------- | ----------------------------------------------------------- |
| enable OSC support  | `OSC/enableosc`    | `false`   | OSC-Fernsteuerung einschalten                               |
| OSC Listen Port    | `OSC/oscport`      | `8000`    | UDP-Port für eingehende OSC                                 |
| OSC Send Host      | `OSC/oscsendhost`  | *(leer)*  | Ziel für Status-Push (Companion-IP); leer = kein Push       |
| OSC Send Port      | `OSC/oscsendport`  | `9000`    | Ziel-UDP-Port (Companion-Feedback-Port)                    |


Send Host wird nur für unaufgeforderten Status-Push gebraucht (Companion-Button-Feedback). Abfragen antworten immer an den UDP-Absender.

---

### 5.3 Time Source

Die Anzeigeuhr kann der lokalen Systemuhr, einem NTP-Server, einem PTPv2-Master (IEEE 1588-2008) oder SMPTE-LTC folgen (Leo-Bodnar-LBE-1110-USB-Serial **oder** Dekodierung von einem lokalen Audioeingang). **OnAirScreen ändert die Betriebssystem-Uhr nie.** NTP und PTP steuern eine eigene Zeitbasis (`time.monotonic()`); ein Sprung der Systemuhr bewegt die Studio-Uhr nicht. LTC darf springen, stehenbleiben und enthält Frames (`HH:MM:SS:FF`).

Datum, Textuhr und AIR3-Top-of-Hour folgen derselben Wandzeit wie die große Uhr, wenn die Quelle Local, NTP oder PTP ist. Bei LTC bleiben sie auf der Systemzeit, weil LTC kein Kalenderdatum hat.


| Einstellung      | Schlüssel              | Standard       | Beschreibung |
| ---------------- | ---------------------- | -------------- | ------------ |
| Time Source      | `TimeSource/source`    | `local`        | `local`, `ntp`, `ptp` oder `ltc` |
| Enable NTP-Check | `NTP/ntpcheck`         | `true`         | Warnung bei Abweichung vom NTP-Server oder wenn der Server nicht erreichbar ist |
| NTP Server       | `NTP/ntpcheckserver`   | `pool.ntp.org` | NTP-Server für NTP als Zeitquelle **und** für die optionale NTP-Prüfung |
| PTP Interface    | `TimeSource/ptp_iface` | *(leer)*       | IPv4-Adresse des PTP-Netzwerkinterfaces (unabhängig von AoIP) |
| PTP Domain       | `TimeSource/ptp_domain`| `0`            | IEEE-1588-Domain (0–255) |
| LTC Input        | `TimeSource/ltc_input` | `serial`       | `serial` (LBE-1110) oder `audio` (lokale PortAudio-Dekodierung) |
| LTC Serial Port  | `TimeSource/ltc_port`  | *(leer)*       | USB-Serial-Gerät des LBE-1110; leer = Auto |
| LTC Audio Device | `TimeSource/ltc_audio_device` | *(leer)* | Lokales Capture-Gerät; leer = System-Default |
| LTC Channel      | `TimeSource/ltc_audio_channel` | `0`     | `0` = Links, `1` = Rechts |
| LTC-Unlock-Warnung | `TimeSource/ltc_warn` | `false` | WARN-Text bei LTC-Verlust; die LED `LTC NOT LOCKED` bleibt immer aktiv |


**Local System Clock:** Anzeige = Systemuhr. Mit NTP-Check wird die Systemuhr mit dem NTP-Server verglichen (Abweichung > 0,3 s oder Fehler → Warnung, Priorität -1).

**NTP Server:** OnAirScreen fragt das Feld NTP Server ab und steuert eine eigene Uhr. Nach dem ersten gültigen Sample wird die OS-Zeit nicht mehr verwendet. Das Feld bleibt editierbar, auch wenn NTP-Check aus ist. Bei NTP-Verlust läuft die letzte Zeit weiter, plus Warnung.

**PTPv2 IEEE 1588-2008:** Software-Slave auf Multicast `224.0.1.129` UDP 319/320, Delay-Mechanismus E2E. Typische Genauigkeit im Millisekundenbereich (kein Hardware-Timestamping). Das Interface unabhängig vom AoIP-Interface der Audio Meters wählen. Bei Sync-Verlust: letzte Zeit läuft weiter, plus Warnung.

**LTC:** Eine Zeitquelle mit zwei Eingängen. Die Framerate wird aus den eingehenden Frames abgeleitet (24 / 25 / 30). Bei LTC-Verlust wird der letzte Timecode gehalten (`LTC NOT LOCKED`). Die großen WARN-Meldungen (`waiting for LTC lock`, `Clock not LTC synchronized`, `LTC reader not connected`) sind **standardmäßig aus**, damit Scrubben/Videoschnitt WARN nicht flutet; **Show LTC unlock warning** einschalten, wenn sie gewünscht sind. Die Lock-LED zeigt immer `LTC LOCK` / `LTC NOT LOCKED`. NTP-Check vergleicht weiterhin die OS-Uhr mit dem NTP-Server, nicht den Timecode.

**LBE-1110 Serial:** USB-CDC-virtueller Seriellport eines [Leo-Bodnar-LBE-1110](https://www.leobodnar.com/shop/index.php?main_page=product_info&cPath=120&products_id=374); keine Treiber. Auto wählt ein Leo-Bodnar-Gerät (USB-VID `0x1DD2`) oder einen LBE-1110-/CDC-Port.

**Audio Input:** Dekodiert SMPTE-LTC (Biphase-Mark) von einem **lokalen** PortAudio-Capture-Gerät, unabhängig von den Audio Meters (kein Livewire/AES67). Kanal Links oder Rechts (Standard Links). Auf manchen Hosts kann dasselbe Gerät nicht zweimal geöffnet werden — wenn die Meters diesen Eingang schon nutzen, für LTC ein anderes Gerät wählen.

Die Lock-LED unten rechts ist grün, wenn die gewählte Quelle eingerastet ist, sonst rot. Daneben: `PTP LOCK` / `PTP NOT LOCKED`, `NTP LOCK` / `NTP NOT LOCKED`, `LTC LOCK` / `LTC NOT LOCKED` oder `LOCAL`.

> **Empfehlung:** Einen lokalen NTP-Server im Studio-Netzwerk verwenden, da `pool.ntp.org` zeitweise unzuverlässig sein kann.

---

### 5.4 Advanced


| Einstellung        | Schlüssel                      | Standard              | Beschreibung          |
| ------------------ | ------------------------------ | --------------------- | --------------------- |
| Date format        | `Formatting/dateFormat`        | `dddd, dd. MMMM yyyy` | Qt-Datumsformat       |
| Time format        | `Formatting/isAmPm`            | `false` (24h)         | 24-Stunden oder AM/PM |
| Textclock Language | `Formatting/textClockLanguage` | `English`             | Sprache der Textuhr   |


**Verfügbare Textuhr-Sprachen:** English, German, Dutch, French

**Datumsformat-Platzhalter** (Qt-Notation, Auszug):


| Platzhalter    | Bedeutung                |
| -------------- | ------------------------ |
| `d` / `dd`     | Tag (1–31 / 01–31)       |
| `ddd` / `dddd` | Wochentag (kurz / lang)  |
| `M` / `MM`     | Monat (1–12 / 01–12)     |
| `MMM` / `MMMM` | Monatsname (kurz / lang) |
| `yy` / `yyyy`  | Jahr (2 / 4 Stellen)     |




#### Weather Widget (OpenWeatherMap)


| Einstellung         | Schlüssel                        | Standard           | Beschreibung                    |
| ------------------- | -------------------------------- | ------------------ | ------------------------------- |
| show Weather Widget | `WeatherWidget/owmWidgetEnabled` | `false`            | Wetter-Widget aktivieren        |
| API Key             | `WeatherWidget/owmAPIKey`        | *(leer)*           | OpenWeatherMap API-Schlüssel    |
| City ID             | `WeatherWidget/owmCityID`        | `2643743` (London) | OpenWeatherMap City-ID          |
| Language            | `WeatherWidget/owmLanguage`      | `English`          | Sprache der Wetterbeschreibung  |
| Unit                | `WeatherWidget/owmUnit`          | `Celsius`          | Celsius, Fahrenheit oder Kelvin |


Städtenamen neben **City ID** eingeben, **Find** (oder Return) drücken und einen Treffer in der Liste wählen. Die City-ID wird automatisch eingetragen; die ID kann weiterhin manuell gesetzt werden. Der API-Key ist maskiert; mit dem durchgestrichenen Auge wird er sichtbar.

**Test API:** Schaltfläche zum Testen der API-Verbindung mit aktuellen Einstellungen.

**Verfügbare Wetter-Sprachen:** Arabic, Bulgarian, Catalan, Czech, German, Greek, English, Persian (Farsi), Finnish, French, Galician, Croatian, Hungarian, Italian, Japanese, Korean, Latvian, Lithuanian, Macedonian, Dutch, Polish, Portuguese, Romanian, Russian, Swedish, Slovak, Slovenian, Spanish, Turkish, Ukrainian, Vietnamese, Chinese Simplified, Chinese Traditional

Weitere Informationen: [WeatherWidget Guide](https://www.astrastudio.de/wiki/onairscreen#weather-widget)

---



### 5.5 Timers

Für jeden AIR-Timer (Gruppe `Timers`):


| Einstellung       | Schlüssel               | Standard      | Beschreibung                       |
| ----------------- | ----------------------- | ------------- | ---------------------------------- |
| Aktiviert         | `TimerAIR{n}Enabled`    | `true`        | Timer auf Hauptbildschirm anzeigen |
| Text              | `TimerAIR{n}Text`       | siehe unten   | Label des Timers                   |
| Active BG Color   | `AIR{n}activebgcolor`   | `#FF0000`     | Hintergrundfarbe (aktiv)           |
| Active Text Color | `AIR{n}activetextcolor` | `#FFFFFF`     | Textfarbe (aktiv)                  |
| Icon Path         | `air{n}iconpath`        | Standard-Icon | Pfad zum Timer-Icon                |


**Standard-AIR-Bezeichnungen und Icons:**


| Timer | Standard-Text | Standard-Icon | Funktion                                      |
| ----- | ------------- | ------------- | --------------------------------------------- |
| AIR1  | Mic           | Mikrofon-Icon | Mikrofon-Stoppuhr                             |
| AIR2  | Phone         | Telefon-Icon  | Telefon-Stoppuhr                              |
| AIR3  | Timer         | Timer-Icon    | Radio-Timer (Hoch-/Runterzählen, Top-of-Hour) |
| AIR4  | Stream        | Antennen-Icon | Stream-Timer                                  |



| Einstellung     | Schlüssel          | Standard      | Beschreibung                                                   |
| --------------- | ------------------ | ------------- | -------------------------------------------------------------- |
| TOTH Timer Text | `TimerTOTHText`    | `TOTH Timer`  | AIR3-Beschriftung, solange der Top-of-Hour-Countdown aktiv ist |
| AIR Min Width   | `TimerAIRMinWidth` | `200`         | Mindestbreite der AIR-Anzeigen (Pixel)                         |


---



### 5.6 Fonts

Für jedes UI-Element kann Schriftart, -größe und -stärke individuell gesetzt werden:


| Element      | Gruppe `Fonts`                    | Standard             |
| ------------ | --------------------------------- | -------------------- |
| LED1–4       | `LED{n}FontName/Size/Weight`      | Roboto, 32pt, Bold |
| AIR1–4       | `AIR{n}FontName/Size/Weight`      | Roboto, 24pt, Bold |
| Station Name | `StationNameFontName/Size/Weight` | Roboto, 24pt, Bold |
| Slogan       | `SloganFontName/Size/Weight`      | Roboto, 18pt, Bold |


Die Familien-Combo listet Application Fonts (inkl. mitgeliefertem Roboto und Noto Sans). Die Größe ist ein Punkt-SpinBox (8–96 pt), **Bold** schaltet die Stärke, **Reset** stellt Roboto mit Default-Größe und Bold für die Zeile wieder her. Die Vorschau zeigt Beispieltext in der gewählten Schrift.

Zusätzlich werden Schriftarten aus dem `fonts/`-Verzeichnis beim Start geladen.

---



### 5.7 About


| Element            | Beschreibung                                                           |
| ------------------ | ---------------------------------------------------------------------- |
| Version            | Aktuelle OnAirScreen-Version                                           |
| Distribution       | `OpenSource` oder kommerzielle Distribution                            |
| Settings Path      | Pfad zur Konfigurationsdatei auf diesem System                         |
| Log Folder         | Ordner mit `onairscreen.log` und Crash-Reports                         |
| Open log folder    | Öffnet diesen Ordner im Dateimanager                                   |
| Loglevel           | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, `NONE`                |
| Enable Reset       | Checkbox zum Freischalten des Reset-Buttons                            |
| Reset all settings | Setzt **alle** Einstellungen auf Standardwerte zurück (unwiderruflich) |


---



### 5.8 Audio Meters

Stereo-Pegelanzeige am linken Bildschirmrand: L/R (Sample-Peak, True Peak oder BBC PPM), ein einzelner Programme-LUFS-Balken (EBU R128) oder beides. L/R füllen mit RMS und legen den aktuellen Peak darüber. Programme-LUFS ist ein Balken (Momentary M, Short-term-S-Tick). Integrated I und LRA sind standardmäßig aus und starten mit `LUFSI:START` (Web-UI, MQTT-Home-Assistant-Schalter, Companion, OSC, UDP/HTTP). `LUFSI:RESET` startet eine laufende Session neu; ist sie gestoppt, verschwinden I und LRA im Meter. Rechtsklick auf den Main Screen → **Reset I+LRA**. Konfiguration unter **Settings → Audio Meters**.

Bestehende Configs mit `Audio/unit=lufs` (ohne `layout`) werden auf Layout `lufs` und L/R-Unit `dbtp` gemappt.


| Einstellung           | Schlüssel                    | Standard     | Beschreibung                                      |
| --------------------- | ---------------------------- | ------------ | ------------------------------------------------- |
| Enable Audio Meters   | `Audio/enabled`              | `true`       | Meter-Spalte anzeigen                             |
| Audio Source          | `Audio/source`               | `device`     | `device`, `livewire` oder `aes67`                 |
| Audio Input           | `Audio/input_device`         | *(leer)*     | PortAudio-Gerätename (bei Source = Local Input)   |
| Livewire Channel      | `Audio/livewire_channel`     | `1`          | Livewire-Kanal 1–32767 (auch über Livewire Source) |
| AoIP Interface        | `Audio/livewire_iface`       | *(leer)*     | IPv4 für Livewire/AES67-IGMP-Join; leer = Default |
| AES67 Stream ID       | `Audio/aes67_id`             | *(leer)*     | SDP-Origin-Hash des gewählten Streams             |
| AES67 Address         | `Audio/aes67_addr`           | *(leer)*     | Multicast-Adresse für RTP-Capture                 |
| AES67 Port            | `Audio/aes67_port`           | `5004`       | RTP-UDP-Port                                      |
| AES67 Name            | `Audio/aes67_name`           | *(leer)*     | Anzeigename aus SDP `s=`                          |
| AES67 Codec           | `Audio/aes67_codec`          | `L24`        | `L16` oder `L24`                                  |
| AES67 Sample Rate     | `Audio/aes67_rate`           | `48000`      | `44100`, `48000` oder `96000`                     |
| AES67 Channels        | `Audio/aes67_channels`       | `2`          | Kanalzahl im Stream (Meter nutzt die ersten zwei) |
| AES67 Pasted SDP      | `Audio/aes67_manual`         | `false`      | `true`, wenn der Stream per Paste SDP kam         |
| Meter Layout          | `Audio/layout`               | `both`       | `lr`, `lufs` oder `both`                           |
| Display Unit          | `Audio/unit`                 | `dbtp`       | L/R-Einheit: `dbfs`, `dbtp`, `bbc_ppm` (PPM nur bei `lr`) |
| Display Style         | `Audio/display_style`        | `bargraph`   | `solid` oder `bargraph`                           |
| Meter Width           | `Audio/meter_width`          | `115`        | Gesamtbreite in Pixel (53–150); extra Breite verdickt sichtbare Balken |
| LUFS Reference Preset | `Audio/lufs_reference_preset`| `ebu_r128`   | `ebu_r128`, `atsc_a85`, `aes_16`, `aes_18`, `custom` |
| LUFS Reference        | `Audio/lufs_reference`       | `-23.0`      | Zielpegel in LUFS (Peg auf der Skala)             |
| Peak Hold             | `Audio/peak_hold`            | `true`       | Peak-Marke halten                                 |
| Peak Hold Seconds     | `Audio/peak_hold_seconds`    | `1.5`        | Haltedauer der Peak-Marke                         |
| TooLoud               | `Audio/tooloud`              | `true`       | Aktion bei True-Peak-Überschreitung               |
| TooLoud Text          | `Audio/tooloudtext`          | `TOO LOUD`   | Warntext                                          |
| TooLoud Threshold     | `Audio/tooloud_threshold_dbtp` | `-1.0`     | Schwellwert in dBTP                               |
| TooLoud Action        | `Audio/tooloud_action`       | `warning`    | `warning` oder `led`                              |
| TooLoud LED           | `Audio/tooloud_led`          | `1`          | LED 1–4 bei Action = LED                          |
| Enable Silence Detection | `Audio/silence`          | `false`      | Aktuelle Audioquelle auf Stille überwachen      |
| Show WARN in OAS      | `Audio/silence_warn`         | `true`       | Silence-Alarm als WARN auf dem Bildschirm       |
| Trigger when Device/Stream is absent | `Audio/silence_on_absent` | `true` | Fehlendes Device/Stream als Stille zählen       |
| Silence Message       | `Audio/silence_text`         | `SILENCE`    | WARN-Text (nur wenn Show WARN an ist)           |
| Silence Threshold     | `Audio/silence_threshold_dbfs` | `-50.0`   | Sample-Peak-Schwellwert in dBFS (−90…0)        |
| Max. Silence duration | `Audio/silence_duration_s`  | `10.0`       | Sekunden unter dem Schwellwert bis zum Alarm    |
| Recovery time         | `Audio/silence_recovery_s`  | `2.0`        | Sekunden über dem Schwellwert bis zum Löschen   |
| HTTP GET URL          | `Audio/silence_http_url`    | *(leer)*     | Optionale URL, einmalig beim Trigger aufgerufen |

Silence Detection nutzt **dieselbe Audioquelle** wie die Meter (Local Input, Livewire oder AES67). Der Schwellwert ist immer **Sample-Peak dBFS**, unabhängig von der Meter-Anzeige. Capture läuft weiter, wenn Silence Detection an ist, auch wenn die Meter ausgeblendet sind.

Der Alarm rastet, wenn der Pegel die Duration lang unter dem Schwellwert bleibt, und löst nach der Recovery-Zeit über dem Schwellwert wieder. **Show WARN in OAS** ist unabhängig vom API/MQTT-Boolean: der Boolean wird aktualisiert, solange die Detection aktiv ist. Ein optionales HTTP GET wird nur bei der steigenden Flanke (`false` → `true`) ausgelöst.

**Device/Stream absent:** Wenn die Option an ist (Default), gilt eine Quelle, die nicht startet (kein Device, AES67 mit **None**, Startfehler), nach derselben Duration als Stille. Wenn die Option aus ist, zählen nur echte Pegel-Callbacks; Capture-Stop löscht einen hängenden Alarm. Paketverlust bei **laufendem** Stream (RTP-Timeout / Silence-Injection) zählt immer als Stille.

Das Bildschirm-WARN nutzt Priorität **2** (hoch) und liegt damit über TooLoud (Priorität 1). Das Flag `silence` in API/MQTT ist unabhängig von `texts.warn` und von `warning/active`.

**Livewire:** Der Rechner muss im AoIP-/Livewire-VLAN liegen (IGMP/Multicast). Solange die Settings offen sind, erscheinen announced Quellen in **Livewire Source** (`239.192.255.3` UDP **4001**, nur Standard-Stereo-Streams). Quelle wählen oder Kanalnummer eintippen. Kanal *N* entspricht Multicast `239.192.0.0 + N` auf UDP-Port **5004** (48 kHz / 24‑Bit Stereo RTP). Nach Apply läuft der Empfang mit gespeichertem Kanal weiter, auch wenn die Ads verstummen.

**AES67:** SAP-Discovery lauscht auf `239.255.255.255` und RFC 2974 `224.2.127.254` UDP **9875**, solange der Einstellungsdialog offen ist. Die Stream-Liste aktualisiert sich live **nur wenn Streams dazukommen oder verschwinden** (kein Flackern bei unveränderter Liste). Die Combo hat immer **None** (kein Stream). SAP-Einträge verschwinden, wenn sie nicht mehr announced werden (Deletion oder Timeout). **Paste SDP**, falls ein Gerät nicht per SAP announced — diese Einträge bleiben in der Liste und sind mit **pasted SDP** gekennzeichnet. Unterstützt: L16/L24 bei 44,1/48/96 kHz, 1–64 Kanäle (Meter zeigt Kanal 1–2). Dante-AES67-SAP-Streams erscheinen wie andere (`a=keywords:Dante` nur als Label). Kein PTP und kein Playout — nur Metering. Nach Apply läuft der Empfang mit gespeicherter Adresse/Port weiter, auch wenn SAP gerade schweigt. Apply mit **None** beendet den AES67-Empfang und setzt das Meter zurück.

**Lokaler Eingang:** unter macOS Mikrofon-Berechtigung für OnAirScreen.


---



## 6. Funktionen im Detail



### 6.1 Status-LEDs

Jede LED kann einzeln ein- und ausgeschaltet werden. Im aktiven Zustand werden konfigurierte Vorder- und Hintergrundfarben verwendet; im inaktiven Zustand die gemeinsamen Inaktiv-Farben.

**Blinkmodi:**

- **Autoflash:** Blinkt dauerhaft im 500-ms-Takt, solange die LED eingeschaltet ist
- **20sec flash:** Blinkt 20 Sekunden, schaltet sich dann automatisch aus



### 6.2 AIR-Timer

Alle AIR-Timer zählen die verstrichene Zeit im Format **M:SS** (z. B. `3:45`). AIR3 zeigt **▲** (Hochzählen) oder **▼** (Runterzählen) unter dem Timer-Icon.

#### AIR1 (Mikrofon) und AIR2 (Telefon)

- Einfache Stoppuhr: Start/Stopp, Sekunden werden bei Start auf 0 zurückgesetzt
- Steuerung: `M`/`/` (AIR1), `P`/`*` (AIR2)



#### AIR3 (Radio-Timer)

Der vielseitigste Timer mit drei Betriebsarten:

1. **Hochzählen (Count-Up):** Standardmodus, zählt von 0:00 aufwärts
2. **Runterzählen (Count-Down):** Wird per `AIR3TIME:seconds` oder Timer-Dialog gesetzt
3. **Top-of-Hour (TOH):** Countdown bis zur nächsten vollen Stunde (Format MM:SS, z. B. `22:38`)

**Top-of-Hour-Verhalten:**

- Erster Aufruf: Berechnet verbleibende Zeit bis `:00`, startet Countdown, Beschriftung ist der konfigurierte TOTH-Timer-Text (Standard `TOTH Timer`)
- Zweiter Aufruf (oder `OFF`/`TOGGLE` während aktiv): Stoppt und stellt die konfigurierte AIR3-Beschriftung wieder her
- Synchronisiert mit der Anzeigeuhr, stoppt automatisch bei Stundenwechsel und stellt die konfigurierte Beschriftung wieder her
- API-Status: `"topOfHour": true` und `"text"` mit dem konfigurierten TOTH-Timer-Text in `air[3]` wenn aktiv

**Timer-Eingabedialog** (`Enter`):


| Eingabe            | Bedeutung                          |
| ------------------ | ---------------------------------- |
| `2,10` oder `2.10` | 2 Minuten 10 Sekunden (Count-Down) |
| `30`               | 30 Sekunden (Count-Down)           |
| `0`                | Count-Up-Modus                     |




#### AIR4 (Stream-Timer)

- Wie AIR3, aber ohne Top-of-Hour-Funktion
- Steuerung: `S` (Start/Stopp), `Alt+S` (Reset)



### 6.3 Textzeilen NOW, NEXT, WARN


| Zeile | API-Befehl  | Beschreibung                                     |
| ----- | ----------- | ------------------------------------------------ |
| NOW   | `NOW:TEXT`  | Erste Fußzeile (aktueller Titel, IP-Adressen, …) |
| NEXT  | `NEXT:TEXT` | Zweite Fußzeile (nächster Titel, …)              |
| WARN  | `WARN:TEXT` | Warnmeldung mit rotem Warnmodus                  |


**Maximale Textlänge:** 500 Zeichen (Eingaben werden automatisch bereinigt und gekürzt).

#### Warnungssystem mit Prioritäten


| Priorität | Bedeutung                 | API-Format    |
| --------- | ------------------------- | ------------- |
| -1        | NTP-Warnung (automatisch) | *(intern)*    |
| 0         | Normal / Legacy           | `WARN:TEXT`   |
| 1         | Medium                    | `WARN:1:TEXT` |
| 2         | High (höchste)            | `WARN:2:TEXT` |


**Anzeigeregel:** Die Warnung mit der **höchsten Priorität** wird angezeigt. NTP-Warnungen (-1) erscheinen nur, wenn keine andere Warnung aktiv ist. Bei aktiver Warnung werden NOW und NEXT ausgeblendet.

**Warnung löschen:**


| Methode     | Befehl                                     |
| ----------- | ------------------------------------------ |
| Priorität 0 | `WARN:` *(leerer Text)*                    |
| Priorität 1 | `WARN:1:` *(leerer Text nach Doppelpunkt)* |
| Priorität 2 | `WARN:2:` *(leerer Text nach Doppelpunkt)* |
| Web-UI      | X-Button neben der Warnung                 |




### 6.4 IP-Adressen anzeigen

Taste `I` (oder automatisch beim Start) zeigt alle lokalen IPv4-Adressen in **NOW** und IPv6-Adressen in **NEXT** für 10 Sekunden an.

Wenn **Replace IPs after 10s** aktiviert ist, wird die NOW-Zeile danach durch den konfigurierten Ersatztext (`replacenowtext`) ersetzt.

### 6.5 Uhr

- **Digital:** LED-Style-Ziffernanzeige mit konfigurierbaren Farben
- **Analog:** Klassisches Zifferblatt
- **Textuhr:** Sprachliche Zeitanzeige (z. B. „it's a quarter past three")
- **Zeitquelle:** Local, NTP, PTPv2 oder LTC — siehe [5.3 Time Source](#53-time-source); die OS-Uhr wird nie gesetzt
- **Lock-LED** unten rechts: grün = eingerastet, rot = nicht eingerastet (`PTP LOCK` / `NTP LOCK` / `LTC LOCK` oder `LOCAL`)
- **Wetter-Widget:** Optional rechts neben der Uhr (OpenWeatherMap)



### 6.6 Systembefehle (nur API)


| Befehl         | Funktion                      |
| -------------- | ----------------------------- |
| `CMD:REBOOT`   | Betriebssystem neu starten    |
| `CMD:SHUTDOWN` | Betriebssystem herunterfahren |
| `CMD:QUIT`     | OnAirScreen beenden           |


> Diese Befehle sind **nicht** über die Einstellungs-UI erreichbar, sondern nur per API/MQTT.

---



## 7. Fernsteuerung und API

OnAirScreen unterstützt Fernsteuerung über UDP, HTTP, Web-UI, MQTT, OSC, REST-API und Bitfocus Companion.

### 7.1 UDP (Port 3310)

```bash
# LED1 einschalten
echo "LED1:ON" > /dev/udp/127.0.0.1/3310

# NOW-Text setzen
echo "NOW:Aktueller Songtitel" > /dev/udp/127.0.0.1/3310

# Konfiguration ändern
echo "CONF:LED1:text=STUDIO LIVE" > /dev/udp/127.0.0.1/3310
echo "CONF:CONF:APPLY=TRUE" > /dev/udp/127.0.0.1/3310
```



### 7.2 HTTP (Port 8010)

```bash
curl "http://127.0.0.1:8010/?cmd=LED1:ON"
curl "http://127.0.0.1:8010/?cmd=NOW:Aktueller%20Song"
```



### 7.3 Web-UI

Browser öffnen: `http://<IP-Adresse>:8010/`

**Funktionen der Web-UI:**

- Echtzeit-Status für LEDs, AIR-Timer, Textfelder, Silence-Alarm und Loudness I+LRA (I- und LRA-Werte plus Laufstatus)
- Instanzname in Titel und Status (aus `/api/status` `instance`)
- WebSocket-Updates (mit HTTP-Polling-Fallback; nach Polling wird wieder WebSocket versucht)
- Dark Mode mit persistenter Theme-Einstellung
- LED- und Timer-Steuerung mit Toggle-Buttons
- Start / Stop / Reset für Programme-I + LRA (`LUFSI`)
- Top-of-Hour-Button für AIR3
- AIR3-Zeit setzen (`m:ss`, `m,ss` oder Sekunden)
- AIR3 Count-up vs. Countdown in der Statuskachel
- Tasten `1`–`4` schalten LEDs (nicht während der Texteingabe)
- Texteingabe für NOW, NEXT, WARN (NOW/NEXT folgen dem Live-Status, solange nicht editiert wird)
- Warnungen mit Priorität und Lösch-Button
- Versions- und Distributionsinformationen
- Dauerhaftes Connection-Badge (Live / Polling / Offline) plus Fehler-Modal



### 7.4 REST-API

**Status abfragen:**

```bash
curl http://127.0.0.1:8010/api/status
```

Antwort (vereinfacht):

```json
{
  "leds": { "1": { "status": true, "text": "ON AIR", "autoflash": false } },
  "air": { "3": { "status": false, "seconds": 0, "text": "Timer", "topOfHour": false, "countDown": false } },
  "texts": { "now": "Song", "next": "Next Song", "warn": "" },
  "warnings": [],
  "silence": false,
  "lufsIntegrated": false,
  "lufsI": null,
  "lra": null,
  "instance": "Studio-1",
  "version": "1.0.0beta5",
  "distribution": "OpenSource"
}
```

Das Feld `silence` ist `true`, solange Silence Detection eingerastet ist, auch wenn das Bildschirm-WARN ausgeschaltet ist. `lufsIntegrated` ist `true`, solange eine I+LRA-Session läuft (`LUFSI:START`). `lufsI` ist die gated Integrated Loudness in LUFS (eine Nachkommastelle), `lra` die Loudness Range in LU; beide sind `null`, bis genug Audio gemessen wurde. `instance` ist der konfigurierte Instanzname. Bei AIR3 zeigt `topOfHour`, ob der Top-of-Hour-Countdown aktiv ist, und `countDown`, ob der Radio-Timer runterzählt.

**Befehl senden:**

```bash
curl "http://127.0.0.1:8010/api/command?cmd=LED1:ON"
```



### 7.5 MQTT

**Befehle senden** (Topic: `{base_topic}/...`):


| Topic            | Payload                 | Funktion              |
| ---------------- | ----------------------- | --------------------- |
| `led{1-4}/set`   | `ON` / `OFF` / `TOGGLE` | LED schalten          |
| `air{1-4}/set`   | `ON` / `OFF` / `TOGGLE` | Timer starten/stoppen |
| `air{3-4}/reset` | `PRESS`                 | Timer zurücksetzen    |
| `air3/toh`       | `ON` / `OFF` / `TOGGLE` | Top-of-Hour           |
| `lufs/integrated/set` | `ON` / `OFF` / `TOGGLE` / `RESET` | I+LRA starten/stoppen/reset |
| `lufs/integrated/reset` | `PRESS` | I+LRA zurücksetzen |
| `text/now/set`   | `TEXT`                  | NOW-Text setzen       |
| `text/next/set`  | `TEXT`                  | NEXT-Text setzen      |
| `text/warn/set`  | `TEXT`                  | WARN-Text setzen      |


**Status-Topics** (automatisch publiziert):


| Topic              | Payload            |
| ------------------ | ------------------ |
| `led{1-4}/state`   | `ON` / `OFF`       |
| `air{1-4}/state`   | `ON` / `OFF`       |
| `air{1-4}/time`    | Sekunden (Integer) |
| `air3/toh/state`   | `true` / `false`   |
| `text/{now,next,warn}/state` | Text     |
| `warning/active`  | `true` / `false`   |
| `silence/active`   | `true` / `false`   |
| `lufs/integrated/state` | `ON` / `OFF` |
| `lufs/i`           | I in LUFS (`""` wenn unbekannt) |
| `lufs/lra`         | LRA in LU (`""` wenn unbekannt) |
| `instance/state`   | Instanzname        |


**Home Assistant Autodiscovery** erstellt automatisch:

- LED-Schalter (LED1–4)
- AIR-Timer-Schalter (AIR1–4)
- AIR-Zeit-Sensoren (AIR1–4 Time)
- Reset-Buttons (AIR3/AIR4)
- Top-of-Hour-Button (AIR3)
- Text-Entitäten (NOW, NEXT, WARN)
- Binary Sensoren: Warning Active, Silence
- Sensor: Instance (Instanzname)
- Loudness-I+LRA-Schalter (Start setzt zurück; Stop friert die letzten Werte)
- Loudness-I+LRA-Reset-Taste (laufend neu starten; gestoppt I und LRA ausblenden)
- Sensoren: Loudness I (LUFS), Loudness LRA (LU)

Der Home-Assistant-Gerätename lautet `OnAirScreen (Studio-1)`, wenn der Instanzname noch nicht im MQTT Device Name steht.



### 7.6 Bitfocus Companion (empfohlen)

Das eigene Companion-Modul **astrastudio-OnAirScreen** ist der empfohlene Weg für Stream Decks und ähnliche Oberflächen. Befehle gehen über HTTP (Port **8010**): `GET /api/command?cmd=LED1:ON`. Der Live-Status nutzt bevorzugt den OnAirScreen-**WebSocket** auf HTTP-Port **+ 1** (also **8011**, wenn HTTP 8010 ist) und fällt auf Polling von `GET /api/status` zurück (Standard alle 500 ms). **OSC ist nicht nötig.** Die AIR-Zeiten auf den Buttons bleiben nah am Studiobildschirm (MIC = AIR1). Beide Ports in der Firewall freigeben.

**OnAirScreen:** HTTP muss erreichbar sein (Standard). OSC kann aus bleiben.

**Companion** (lokales Modul, bis es im Companion Store liegt):

1. Im Repo `OAS-Companion`: `yarn install && yarn build`
2. Ordner als `companion-module-astrastudio-onairscreen` nach Companion `module-local-dev` verlinken (oder unter Companion **Developer** den Pfad eintragen)
3. Companion neu starten und Connection **astrastudio / OnAirScreen** anlegen
4. Host = OnAirScreen-IP, HTTP-Port `8010` (wie unter **Settings → Network**). WebSocket anlassen, außer du musst nur pollen.

Presets: LED1–4 (Toggle + Farbe), AIR1–4 mit Live-Beschriftung und Zeit auf dem Button (MIC = AIR1), TOTH, Reset AIR3/4, NOW / NEXT / WARN, Silence, Loudness I+LRA, Reset I+LRA.

Variablen wie `$(oas:air1_time)`, `$(oas:lufs_i)` und `$(oas:lra)` und Feedbacks (LED an, AIR läuft, TOTH, Silence, WARN, Loudness I+LRA) kommen aus WebSocket oder Status-Poll. Connection-Label auf `oas` setzen, damit die Beispiele passen. Der Connection-Status zeigt Instanzname und Version, z. B. `Studio-1 · 1.0.0beta5`. Die `HELP.md` des Moduls listet alle Aktionen, Feedbacks und Variablen.

Wenn kein eigenes Modul geladen werden kann, bleibt **Generic OSC** als Alternative (nächster Abschnitt). OSC-Status-Push ist langsamer (alle 5 Sekunden) als HTTP-Poll / WebSocket.

### 7.7 OSC (Port 8000)

OSC unter **Settings → Network** einschalten. Prefix ist `/oas`. Integer `1`/`0` bedeutet AN/AUS; ohne Argument = TOGGLE. Texte als String.

**Setzen (Befehle):**


| Adresse               | Argument                         | Funktion              |
| -------------------- | -------------------------------- | --------------------- |
| `/oas/led{1-4}`      | `i` 0/1, oder leer für Toggle      | LED                   |
| `/oas/air{1-4}`      | `i` 0/1, oder leer für Toggle      | AIR-Timer             |
| `/oas/air{3-4}/reset` | keines                           | AIR3/AIR4 zurücksetzen |
| `/oas/air3/toh`      | `i` 0/1                          | Top-of-Hour           |
| `/oas/air3/time`     | `i` Sekunden (weglassen = Abfrage) | AIR3-Zeit setzen      |
| `/oas/text/now`      | `s` Text                         | NOW                   |
| `/oas/text/next`     | `s` Text                         | NEXT                  |
| `/oas/text/warn`     | `s` Text                         | WARN                  |
| `/oas/command`       | `s` `COMMAND:VALUE`              | Roh-API-Befehl        |
| `/oas/lufs/integrated` | `i` 0/1, oder leer für Toggle    | I + LRA starten/stoppen |
| `/oas/lufs/integrated/reset` | leer                        | I + LRA zurücksetzen    |


**Abfrage (Antwort an den UDP-Absender, kein Send Host nötig):** `/state`-Adresse senden (oder `/oas/status` für alles). Antworten sind Integer `0/1` für Booleans und Strings für Texte. `/oas/lufs/integrated/state` zeigt, ob I + LRA läuft. `/oas/lufs/i` und `/oas/lufs/lra` liefern I (LUFS) und LRA (LU) als String mit einer Nachkommastelle, oder leer wenn unbekannt.

**Push (Companion-Feedback):** OSC Send Host auf den Companion-Rechner, OSC Send Port auf den Generic-OSC-**Feedback**-Port. OnAirScreen sendet dann `/oas/led1/state` usw. nach Änderungen und alle 5 Sekunden.

```bash
# LED1 toggeln
python3 utils/oas_osc_send.py /oas/led1

# LED1 an
python3 utils/oas_osc_send.py /oas/led1 1
```

#### Alternative: Generic OSC

Wenn OSC bevorzugt wird oder das HTTP-Modul nicht geladen werden kann, eingebaute Connection **OSC Generic**.

**Nur steuern:**

1. OnAirScreen: OSC an, Listen-Port `8000`
2. Companion: **OSC Generic**, Target = OnAirScreen-IP, Port `8000`
3. Button-Action **Send integer**, Pfad `/oas/led1`, Wert `1` (an) oder `0` (aus). Ohne Argument = Toggle. **Send string** für `/oas/text/now`.

**Button-Feedback (Stream-Deck-Farbe):**

1. Companion: OSC-Generic-**Feedback-Listen-Port** setzen (z. B. `9000`)
2. OnAirScreen: OSC Send Host = Companion-IP, OSC Send Port = dieser Feedback-Port
3. Feedback **Listen for OSC messages (Integer)** auf `/oas/led1/state`, Vergleich `1`

Query-Reply an den Command-Socket nutzt Companion **nicht** (anderer UDP-Port).


### 7.8 Befehlsreferenz



#### Steuerungsbefehle


| Befehl                       | Funktion                            |
| ---------------------------- | ----------------------------------- |
| `LED{1-4}:[ON/OFF/TOGGLE]`   | LED schalten                        |
| `NOW:TEXT`                   | NOW-Text setzen                     |
| `NEXT:TEXT`                  | NEXT-Text setzen                    |
| `WARN:TEXT`                  | Warnung setzen (Priorität 0)        |
| `WARN:1:TEXT`                | Warnung setzen (Priorität Medium)   |
| `WARN:2:TEXT`                | Warnung setzen (Priorität High)     |
| `WARN:`                      | Warnung Priorität 0 löschen         |
| `WARN:1:`                    | Warnung Priorität 1 löschen         |
| `WARN:2:`                    | Warnung Priorität 2 löschen         |
| `AIR1:[ON/OFF/TOGGLE]`       | Mikrofon-Timer                      |
| `AIR2:[ON/OFF/TOGGLE]`       | Telefon-Timer                       |
| `AIR3:[ON/OFF/RESET/TOGGLE]` | Radio-Timer                         |
| `AIR3TIME:seconds`           | Radio-Timer auf Sekundenwert setzen |
| `AIR3TOH:[ON/OFF/TOGGLE]`    | Top-of-Hour-Countdown               |
| `AIR4:[ON/OFF/RESET/TOGGLE]` | Stream-Timer                        |
| `LUFSI:[START/STOP/TOGGLE/RESET]` | Programme-I + LRA-Session (Reset: laufend neu, gestoppt ausblenden) |
| `CMD:REBOOT`                 | OS-Neustart                         |
| `CMD:SHUTDOWN`               | OS-Herunterfahren                   |
| `CMD:QUIT`                   | OnAirScreen beenden                 |




#### Remote-Konfiguration (CONF)

Format: `CONF:GRUPPE:PARAMETER=WERT`

Änderungen werden erst nach `CONF:CONF:APPLY=TRUE` aktiv und gespeichert.


| Befehl                                          | Beschreibung            |
| ----------------------------------------------- | ----------------------- |
| `CONF:General:stationname=TEXT`                 | Stationsname            |
| `CONF:General:instancename=TEXT`              | Instanzname (DNS-Label) |
| `CONF:General:slogan=TEXT`                      | Slogan                  |
| `CONF:General:stationcolor=COLOR`               | Stationsfarbe           |
| `CONF:General:slogancolor=COLOR`                | Sloganfarbe             |
| `CONF:General:replacenow=[True/False]`          | IP-Ersatz aktivieren    |
| `CONF:General:replacenowtext=TEXT`              | Ersatztext              |
| `CONF:LED[1-4]:used=[True/False]`               | LED aktivieren          |
| `CONF:LED[1-4]:text=TEXT`                       | LED-Text                |
| `CONF:LED[1-4]:activebgcolor=COLOR`             | LED-Hintergrund aktiv   |
| `CONF:LED[1-4]:activetextcolor=COLOR`           | LED-Text aktiv          |
| `CONF:LED[1-4]:autoflash=[True/False]`          | Autoflash               |
| `CONF:LED[1-4]:timedflash=[True/False]`         | 20-Sekunden-Flash       |
| `CONF:Clock:digital=[True/False]`               | Digital/Analog          |
| `CONF:Clock:showseconds=[True/False]`           | Sekunden anzeigen       |
| `CONF:Clock:secondsinoneline=[True/False]`      | Sekunden in einer Zeile |
| `CONF:Clock:staticcolon=[True/False]`           | Statischer Doppelpunkt  |
| `CONF:Clock:digitalhourcolor=COLOR`             | Stundenfarbe            |
| `CONF:Clock:digitalsecondcolor=COLOR`           | Sekundenfarbe           |
| `CONF:Clock:digitaldigitcolor=COLOR`            | Ziffernfarbe            |
| `CONF:Clock:logopath=PFAD`                      | Logo-Pfad               |
| `CONF:Clock:logoupper=[True/False]`             | Logo oben               |
| `CONF:Network:udpport=PORT`                     | UDP-Port                |
| `CONF:Network:tcpport=PORT`                     | HTTP-Port               |
| `CONF:Audio:enabled=[True/False]`               | Audio-Meter ein/aus     |
| `CONF:Audio:source=[device/livewire/aes67]`     | Audioquelle             |
| `CONF:Audio:input_device=DEVICE_NAME`           | Lokales Eingabegerät    |
| `CONF:Audio:livewire_channel=N`                 | Livewire-Kanal          |
| `CONF:Audio:livewire_iface=IP_OR_EMPTY`         | AoIP-Interface-IP       |
| `CONF:Audio:aes67_id=ORIGIN_HASH`               | AES67-Stream-ID         |
| `CONF:Audio:aes67_addr=MULTICAST`               | AES67-Multicast         |
| `CONF:Audio:aes67_port=PORT`                    | AES67-RTP-Port          |
| `CONF:Audio:aes67_name=NAME`                    | AES67-Anzeigename       |
| `CONF:Audio:aes67_codec=[L16/L24]`              | AES67-Codec             |
| `CONF:Audio:aes67_rate=48000`                   | AES67-Samplerate        |
| `CONF:Audio:aes67_channels=2`                   | AES67-Kanalzahl         |
| `CONF:Audio:aes67_manual=[True/False]`          | AES67 Paste-SDP         |
| `CONF:Audio:unit=[dbfs/dbtp/bbc_ppm]`         | L/R-Anzeigeeinheit       |
| `CONF:Audio:layout=[lr/lufs/both]`            | Meter-Layout             |
| `CONF:Audio:display_style=[solid/bargraph]`     | Meter-Stil              |
| `CONF:Audio:meter_width=79`                     | Meter-Breite (Pixel)    |
| `CONF:Audio:lufs_reference_preset=PRESET`       | LUFS-Preset             |
| `CONF:Audio:lufs_reference=-23.0`               | LUFS-Zielpegel          |
| `CONF:Audio:peak_hold=[True/False]`             | Peak-Hold ein/aus       |
| `CONF:Audio:peak_hold_seconds=1.5`              | Peak-Hold-Dauer         |
| `CONF:Audio:tooloud=[True/False]`               | TooLoud ein/aus         |
| `CONF:Audio:tooloudtext=TEXT`                   | TooLoud-Text            |
| `CONF:Audio:tooloud_threshold_dbtp=-1.0`        | TooLoud-Schwellwert     |
| `CONF:Audio:tooloud_action=[warning/led]`       | TooLoud-Aktion          |
| `CONF:Audio:tooloud_led=[1/2/3/4]`              | TooLoud-LED             |
| `CONF:Audio:silence=[True/False]`                | Silence Detection      |
| `CONF:Audio:silence_warn=[True/False]`          | Silence-WARN ein/aus |
| `CONF:Audio:silence_on_absent=[True/False]`      | Absent als Stille     |
| `CONF:Audio:silence_text=TEXT`                  | Silence-WARN-Text     |
| `CONF:Audio:silence_threshold_dbfs=-50.0`      | Silence-Schwellwert   |
| `CONF:Audio:silence_duration_s=10.0`            | Silence-Dauer (s)    |
| `CONF:Audio:silence_recovery_s=2.0`             | Silence-Recovery (s) |
| `CONF:Audio:silence_http_url=URL`                | Silence-HTTP-GET-URL |
| `CONF:Timers:TimerAIR[1-4]Enabled=[True/False]` | AIR aktivieren          |
| `CONF:Timers:TimerAIR[1-4]Text=TEXT`            | AIR-Label               |
| `CONF:Timers:TimerTOTHText=TEXT`                | TOTH-Timer-Label        |
| `CONF:Timers:AIR[1-4]activebgcolor=COLOR`       | AIR-Hintergrund aktiv   |
| `CONF:Timers:AIR[1-4]activetextcolor=COLOR`     | AIR-Text aktiv          |
| `CONF:Timers:AIR[1-4]iconpath=PFAD`             | AIR-Icon-Pfad           |
| `CONF:Timers:TimerAIRMinWidth=PIXEL`            | AIR-Mindestbreite       |
| `CONF:CONF:APPLY=TRUE`                          | Konfiguration anwenden  |

`CONF:Audio:unit=lufs` wird weiterhin akzeptiert und setzt das Layout auf `lufs` (L/R-Einheit bleibt `dbtp`).

**Farben:** Hex-Format (`#FF0000`) oder Farbnamen.

---



## 8. Presets (Profile)

Presets ermöglichen das Speichern und Laden kompletter Konfigurationen.


| Aktion    | Schaltfläche         | Beschreibung                                    |
| --------- | -------------------- | ----------------------------------------------- |
| Speichern | **Save Preset...**   | Aktuelle Konfiguration als JSON-Datei speichern |
| Laden     | **Load Preset...**   | Gespeichertes Preset laden und anwenden         |
| Löschen   | **Delete Preset...** | Preset-Datei entfernen                          |


**Speicherort:** `<Konfigurationsverzeichnis>/presets/<name>.json`

Presets enthalten Metadaten (Name, Version) und die vollständige Konfiguration als JSON. Nach dem Laden muss **Apply** geklickt werden, damit die Einstellungen aktiv werden.

> **Hinweis:** MQTT-Einstellungen werden in der Konfigurationsdatei gespeichert, sind aber **bewusst nicht** im Preset-Export enthalten. MQTT-Zugangsdaten sind installations- und umgebungsspezifisch und sollen nicht mit visuellen Profilen mitexportiert werden.

---



## 9. Kommandozeilenoptionen

```bash
python start.py --loglevel DEBUG
python start.py -l WARNING
```


| Option             | Werte                                           | Beschreibung                                         |
| ------------------ | ----------------------------------------------- | ---------------------------------------------------- |
| `-l`, `--loglevel` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Log-Level überschreiben (wird **nicht** gespeichert) |


Das Log-Level aus den Einstellungen (`About/Loglevel`) kann zusätzlich die Werte `NONE` (kein Logging) enthalten.

---



## 10. Konfigurationsspeicherort

Einstellungen werden über Qt `QSettings` gespeichert:

- **Organisation:** `astrastudio`
- **Anwendung:** `OnAirScreen`

Der genaue Pfad wird im Register **About** unter **Settings Path** angezeigt. Typische Speicherorte:


| Plattform | Pfad                                                           |
| --------- | -------------------------------------------------------------- |
| Linux     | `~/.config/astrastudio/OnAirScreen.conf`                       |
| macOS     | `~/Library/Preferences/com.astrastudio.OnAirScreen.plist`      |
| Windows   | Registry: `HKEY_CURRENT_USER\Software\astrastudio\OnAirScreen` |


Logs und Crash-Reports liegen separat. Der genaue Pfad steht im Register **About** unter **Log Folder**:


| Plattform | Log-Ordner                                      |
| --------- | ----------------------------------------------- |
| Linux     | `~/.local/share/astrastudio/OnAirScreen/logs/` |
| macOS     | `~/Library/Logs/OnAirScreen/`                   |
| Windows   | `%LOCALAPPDATA%\astrastudio\OnAirScreen\logs\`   |


Dateien in diesem Ordner:

- `onairscreen.log` — rotierendes Anwendungs-Log (gleicher Inhalt wie stderr, folgt dem Log-Level)
- `crash-YYYYMMDD-HHMMSS.txt` — ungefangene Python-Exceptions (Traceback, Version, OS; keine Settings oder Passwörter). Nach einem Main-Thread- oder Qt-Fatal-Crash beendet sich die Anwendung; Fehler in Hintergrund-Threads werden nur geloggt.
- `fault.log` — native Abstürze (Segfaults in Qt oder C-Erweiterungen)

Crash-Dateien werden immer geschrieben, auch wenn das Log-Level `NONE` ist. Den Log-Ordner nur an den Support schicken, nicht öffentlich posten (DEBUG-Logs können Hostnamen oder Befehle enthalten). Nach einem Prozess-Absturz zeigt der nächste Start einen Dialog mit **Open log folder**; er schließt sich nach 30 Sekunden automatisch.


---



## 11. Fehlerbehebung



### OnAirScreen startet nicht / Port belegt

- Prüfen, ob UDP-Port 3310 oder HTTP-Port 8010 bereits belegt ist
- Ports in **Network** ändern



### Fernsteuerung funktioniert nicht

- Firewall-Regeln für UDP/HTTP/OSC-Ports prüfen
- Korrekte IP-Adresse und Ports verwenden
- Mit `curl http://127.0.0.1:8010/api/status` lokal testen



### Companion-Modul zeigt Disconnected

- HTTP muss auf dem konfigurierten Port erreichbar sein (Standard 8010); OSC nutzt dieses Modul nicht
- Mit `curl http://<OnAirScreen-IP>:8010/api/status` JSON prüfen
- Nach `yarn build` Companion neu starten, damit das lokale Modul neu geladen wird



### Silence Detection löst nicht aus

- Ist **Enable Silence Detection** aktiviert und mit **Apply** gespeichert?
- Audioquelle prüfen (Device gewählt, Livewire-Kanal, AES67-Stream nicht **None**)
- dBFS-Schwellwert senken oder Duration verkürzen, wenn Restgeräusch über −50 dBFS liegt
- Fehlt Device oder Stream, **Trigger silence warning when Device/Stream is absent** einschalten



### MQTT-Verbindung schlägt fehl

- MQTT-Broker erreichbar? (`mqttserver`, `mqttport`)
- Zugangsdaten korrekt?
- `enable MQTT support` aktiviert und mit **Apply** gespeichert?



### NTP-Warnung erscheint dauerhaft

- Lokalen NTP-Server konfigurieren (`NTP/ntpcheckserver`)
- Bei Quelle Local die Systemzeit synchronisieren oder die Zeitquelle auf NTP/PTP umstellen
- NTP-Prüfung deaktivieren, falls nicht benötigt



### Wetter-Widget zeigt nichts

- Gültigen OpenWeatherMap API-Key eingeben
- Städtenamen mit **Find** neben City ID suchen oder die ID manuell eingeben
- **Test API** in den Einstellungen ausführen



### Livewire-Meter zeigt keine Pegel

- Source auf **Livewire** gesetzt und Channel-Nummer korrekt (oder announced Quelle gewählt)?
- Rechner im AoIP-/Livewire-VLAN? IGMP/Multicast nicht gefiltert?
- Passendes Netzwerk-Interface gewählt (nicht „Default“, falls mehrere NICs)?
- UDP-Port 5004 freigegeben?
- **Keine Namen unter Livewire Source:** Ads laufen auf `239.192.255.3:4001` nur bei offenen Settings. Die Kanalnummer kann trotzdem manuell eingegeben werden.



### AES67-Meter: keine Streams oder keine Pegel

- **Keine Streams in der Liste:** AoIP-Interface, VLAN und IGMP prüfen; SAP ist `239.255.255.255:9875` und `224.2.127.254:9875` und läuft nur bei offenem Settings-Dialog. Wenn das Gerät nicht announced, **Paste SDP** verwenden.
- **Stream da, Meter bleibt stumm:** RTP-Adresse/Port und Codec (L16 vs. L24). Dante muss im AES67-/SAP-Modus sein. PTP ist fürs Metering nicht nötig.



### Einstellungen zurücksetzen

1. Einstellungsdialog öffnen (`Ctrl+S`)
2. Register **About** → **Enable Reset all settings button** aktivieren
3. **Reset all OnAirScreen settings to default** klicken
4. **Apply** klicken



### Logs an den Support schicken

Wenn OnAirScreen abstürzt oder sich unerwartet verhält:

1. **Settings → About** öffnen
2. **Open log folder** klicken (oder den Pfad unter **Log Folder** kopieren)
3. `onairscreen.log` und vorhandene `crash-*.txt`-Dateien schicken (plus `fault.log`, falls nicht leer)

Die Reports enthalten keine Settings, MQTT-Passwörter oder API-Keys. `--loglevel DEBUG` nur kurz zum Reproduzieren nutzen, bevor die Logs verschickt werden. Nach einem Absturz erscheint dieser Dialog auch beim nächsten Start (schließt sich nach 30 Sekunden).


---



## Anhang: Ereignisprotokollierung

OnAirScreen protokolliert intern folgende Ereignistypen:

- LED-Änderungen (Quelle: manual, autoflash, timedflash, API)
- AIR-Timer Start/Stopp/Reset
- Empfangene Befehle (UDP/HTTP/OSC)
- Warnungen hinzugefügt/entfernt
- Einstellungsänderungen
- Systemereignisse (Start, Beenden, Neustart)

Das Log-Level steuert die Ausgabemenge. Bei Problemen empfiehlt sich temporär `--loglevel DEBUG`. Logs werden zusätzlich nach `onairscreen.log` im Log-Ordner geschrieben (siehe **About**).

---

*© 2012–2026 Sascha Ludwig · [astrastudio.de](http://www.astrastudio.de)*