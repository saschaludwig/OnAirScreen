# OnAirScreen – Bedienungsanleitung

**Version:** 0.9.8  
**Autor:** Sascha Ludwig, [astrastudio.de](http://www.astrastudio.de)  
**Projekt:** [OnAirScreen auf GitHub](http://saschaludwig.github.io/OnAirScreen/)  
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
- **4 AIR-Timer** (Mikrofon, Telefon, Radio-Timer, Stream-Timer)
- **Digitale oder analoge Uhr** mit optionalem Textuhr-Modus
- **Textzeilen** NOW, NEXT und WARN (mit Prioritätssystem)
- **Wetter-Widget** (OpenWeatherMap)
- **Fernsteuerung** per Tastatur, UDP, HTTP, Web-UI, MQTT und REST-API
- **Home-Assistant-Integration** via MQTT Autodiscovery

Die Anwendung startet standardmäßig im **Vollbildmodus** mit ausgeblendetem Mauszeiger und eignet sich für dedizierte Studio-Monitore, Raspberry-Pi-Setups und Touch-freie Bedienung.

OnAirScreen passt sich automatisch an verschiedene Monitor-Seitenverhältnisse an und funktioniert sowohl auf **4:3**- als auch auf **16:9/16:10**-Displays.

---



## 2. Installation und Start



### Voraussetzungen

- **Python 3** mit PyQt6 (bei Installation aus dem Quellcode)
- Abhängigkeiten: siehe `requirements.txt`
- Netzwerkzugriff für UDP/HTTP/MQTT-Fernsteuerung (optional)



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

```
┌─────────────────────────────────────────────────────────┐
│  Stationsname                                           │
│  Slogan                                                 │
├─────────────────────────────────────────────────────────┤
│  [LED1]  [LED2]  [LED3]  [LED4]     (Status-LEDs)     │
├─────────────────────────────────────────────────────────┤
│  Text links          │  Uhr / Logo  │  Text rechts      │
│                      │  (ClockWidget)│                   │
├─────────────────────────────────────────────────────────┤
│  [AIR1 Mic]  [AIR3 Timer]  [AIR2 Phone]  [AIR4 Stream]  │
├─────────────────────────────────────────────────────────┤
│  NOW:  aktueller Titel / IP-Adressen                    │
│  NEXT: nächster Titel / IPv6-Adressen                   │
│  WARN: Warnmeldung (ersetzt NOW/NEXT bei aktiver Warnung) │
└─────────────────────────────────────────────────────────┘
```



### Bereiche im Detail


| Bereich             | Widget                    | Funktion                                                   |
| ------------------- | ------------------------- | ---------------------------------------------------------- |
| **Stationsname**    | `labelStation`            | Name des Senders, Farbe konfigurierbar                     |
| **Slogan**          | `labelSlogan`             | Untertitel / Claim des Senders                             |
| **Status-LEDs 1–4** | `buttonLED1`–`buttonLED4` | Große farbige Statusanzeigen (ON AIR, PHONE, …)            |
| **Uhr**             | `clockWidget`             | Digital oder analog, mit Logo und optionalem Wetter-Widget |
| **AIR-Timer 1–4**   | `AirLED_1`–`AirLED_4`     | Stoppuhr-Timer mit Icon, Label und MM:SS-Anzeige           |
| **NOW**             | `labelCurrentSong`        | Erste Fußzeile (z. B. aktueller Songtitel)                 |
| **NEXT**            | `labelNews`               | Zweite Fußzeile (z. B. nächster Titel)                     |
| **WARN**            | `labelWarning`            | Warnmeldung; blendet NOW/NEXT aus, wenn aktiv              |


> **Hinweis:** Die Status-LEDs und AIR-Timer werden primär per **Tastatur** oder **Fernsteuerung** bedient.



### Vollbildmodus

- Standard: Vollbild mit verstecktem Mauszeiger
- Umschalten: `F` oder `Ctrl+F` (macOS: `Cmd+F`)
- Der Vollbild-Zustand wird in den Einstellungen (`General/fullscreen`) gespeichert

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

Der Einstellungsdialog öffnet sich mit `Ctrl+S` oder `Ctrl+,`. Er enthält **7 Registerkarten** (vertikal links angeordnet):


| Register              | Inhalt                                 |
| --------------------- | -------------------------------------- |
| **General Settings**  | Station, LEDs, Uhr, NTP, Logo, Updates |
| **Advanced Settings** | Netzwerk, MQTT, Formatierung, Wetter   |
| **Timers**            | AIR-Timer 1–4                          |
| **Fonts**             | Schriftarten für alle Elemente         |
| **About**             | Version, Lizenzinfo, Log-Level, Reset  |
| **License**           | BSD-Lizenztext                         |




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



### 5.1 General Settings



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




#### NTP-Prüfung


| Einstellung      | Schlüssel            | Standard       | Beschreibung                            |
| ---------------- | -------------------- | -------------- | --------------------------------------- |
| Enable NTP-Check | `NTP/ntpcheck`       | `true`         | Zeitsynchronisations-Prüfung aktivieren |
| NTP-Check Server | `NTP/ntpcheckserver` | `pool.ntp.org` | NTP-Server-Adresse                      |


Bei aktivierter NTP-Prüfung wird die Systemuhr regelmäßig mit dem NTP-Server verglichen. Abweichungen > 0,3 Sekunden oder Verbindungsfehler erzeugen eine **NTP-Warnung** (Priorität -1, niedrigste Priorität).

> **Empfehlung:** Einen lokalen NTP-Server im Studio-Netzwerk verwenden, da `pool.ntp.org` zeitweise unzuverlässig sein kann.



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
> Für die Update-Prüfung in der kostenpflichtigen Version muss ein **Update Key** eingegeben werden. Diesen erhältst du nach der Bestellung im Kundenportal unter [customer.astrastudio.de](https://customer.astrastudio.de).

---



### 5.2 Advanced Settings



#### Netzwerk


| Einstellung       | Schlüssel                   | Standard      | Beschreibung              |
| ----------------- | --------------------------- | ------------- | ------------------------- |
| UDP Port          | `Network/udpport`           | `3310`        | Port für UDP-Befehle      |
| HTTP Port         | `Network/httpport`          | `8010`        | Port für HTTP/Web-UI      |
| Multicast Address | `Network/multicast_address` | `239.194.0.1` | Multicast-Adresse für UDP |




#### MQTT


| Einstellung         | Schlüssel             | Standard      | Beschreibung                 |
| ------------------- | --------------------- | ------------- | ---------------------------- |
| enable MQTT support | `MQTT/enablemqtt`     | `false`       | MQTT-Integration aktivieren  |
| MQTT Server         | `MQTT/mqttserver`     | `localhost`   | Broker-Hostname/IP           |
| MQTT Server Port    | `MQTT/mqttport`       | `1883`        | Broker-Port                  |
| MQTT User           | `MQTT/mqttuser`       | *(leer)*      | Benutzername (optional)      |
| MQTT Password       | `MQTT/mqttpassword`   | *(leer)*      | Passwort (optional)          |
| MQTT Device Name    | `MQTT/mqttdevicename` | `OnAirScreen` | Gerätename in Home Assistant |


**MQTT Base Topic:** `onairscreen` + letzte 6 Hex-Zeichen der MAC-Adresse, z. B. `onairscreen_a1b2c3`.

#### Datums- und Zeitformat


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


**Test API:** Schaltfläche zum Testen der API-Verbindung mit aktuellen Einstellungen.

**Verfügbare Wetter-Sprachen:** Arabic, Bulgarian, Catalan, Czech, German, Greek, English, Persian (Farsi), Finnish, French, Galician, Croatian, Hungarian, Italian, Japanese, Korean, Latvian, Lithuanian, Macedonian, Dutch, Polish, Portuguese, Romanian, Russian, Swedish, Slovak, Slovenian, Spanish, Turkish, Ukrainian, Vietnamese, Chinese Simplified, Chinese Traditional

Weitere Informationen: [WeatherWidget Guide](https://www.astrastudio.de/wiki/onairscreen#weather-widget)

---



### 5.3 Timers

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



| Einstellung   | Schlüssel          | Standard | Beschreibung                           |
| ------------- | ------------------ | -------- | -------------------------------------- |
| AIR Min Width | `TimerAIRMinWidth` | `200`    | Mindestbreite der AIR-Anzeigen (Pixel) |


---



### 5.4 Fonts

Für jedes UI-Element kann Schriftart, -größe und -stärke individuell gesetzt werden:


| Element      | Gruppe `Fonts`                    | Standard             |
| ------------ | --------------------------------- | -------------------- |
| LED1–4       | `LED{n}FontName/Size/Weight`      | FreeSans, 24pt, Bold |
| AIR1–4       | `AIR{n}FontName/Size/Weight`      | FreeSans, 24pt, Bold |
| Station Name | `StationNameFontName/Size/Weight` | FreeSans, 24pt, Bold |
| Slogan       | `SloganFontName/Size/Weight`      | FreeSans, 18pt, Bold |


Schaltfläche **Set Font...** öffnet einen Schriftart-Dialog. Die Vorschau zeigt den aktuellen Font an.

Zusätzlich werden Schriftarten aus dem `fonts/`-Verzeichnis beim Start geladen.

---



### 5.5 About


| Element            | Beschreibung                                                           |
| ------------------ | ---------------------------------------------------------------------- |
| Version            | Aktuelle OnAirScreen-Version                                           |
| Distribution       | `OpenSource` oder kommerzielle Distribution                            |
| Settings Path      | Pfad zur Konfigurationsdatei auf diesem System                         |
| Loglevel           | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, `NONE`                |
| Enable Reset       | Checkbox zum Freischalten des Reset-Buttons                            |
| Reset all settings | Setzt **alle** Einstellungen auf Standardwerte zurück (unwiderruflich) |


---



## 6. Funktionen im Detail



### 6.1 Status-LEDs

Jede LED kann einzeln ein- und ausgeschaltet werden. Im aktiven Zustand werden konfigurierte Vorder- und Hintergrundfarben verwendet; im inaktiven Zustand die gemeinsamen Inaktiv-Farben.

**Blinkmodi:**

- **Autoflash:** Blinkt dauerhaft im 500-ms-Takt, solange die LED eingeschaltet ist
- **20sec flash:** Blinkt 20 Sekunden, schaltet sich dann automatisch aus



### 6.2 AIR-Timer

Alle AIR-Timer zählen die verstrichene Zeit im Format **MM:SS** (z. B. `3:45`).

#### AIR1 (Mikrofon) und AIR2 (Telefon)

- Einfache Stoppuhr: Start/Stopp, Sekunden werden bei Start auf 0 zurückgesetzt
- Steuerung: `M`/`/` (AIR1), `P`/`*` (AIR2)



#### AIR3 (Radio-Timer)

Der vielseitigste Timer mit drei Betriebsarten:

1. **Hochzählen (Count-Up):** Standardmodus, zählt von 0:00 aufwärts
2. **Runterzählen (Count-Down):** Wird per `AIR3TIME:seconds` oder Timer-Dialog gesetzt
3. **Top-of-Hour (TOH):** Countdown bis zur nächsten vollen Stunde (Format MM:SS, z. B. `22:38`)

**Top-of-Hour-Verhalten:**

- Erster Aufruf: Berechnet verbleibende Zeit bis `:00`, startet Countdown
- Zweiter Aufruf (oder `OFF`/`TOGGLE` während aktiv): Stoppt und setzt auf `0:00`
- Synchronisiert mit der Systemuhr, stoppt automatisch bei Stundenwechsel
- API-Status: `"topOfHour": true` in `air[3]` wenn aktiv

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

OnAirScreen unterstützt vier Fernsteuerungskanäle:

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

- Echtzeit-Status für LEDs, AIR-Timer und Textfelder
- WebSocket-Updates (mit HTTP-Polling-Fallback)
- Dark Mode mit persistenter Theme-Einstellung
- LED- und Timer-Steuerung mit Toggle-Buttons
- Top-of-Hour-Button für AIR3
- Texteingabe für NOW, NEXT, WARN
- Warnungen mit Priorität und Lösch-Button
- Versions- und Distributionsinformationen



### 7.4 REST-API

**Status abfragen:**

```bash
curl http://127.0.0.1:8010/api/status
```

Antwort (vereinfacht):

```json
{
  "leds": { "1": { "status": true, "text": "ON AIR", "autoflash": false } },
  "air": { "3": { "status": false, "seconds": 0, "text": "Timer", "topOfHour": false } },
  "texts": { "now": "Song", "next": "Next Song", "warn": "" },
  "warnings": [],
  "version": "0.9.8",
  "distribution": "OpenSource"
}
```

**Befehl senden:**

```bash
curl "http://127.0.0.1:8010/api/command?cmd=LED1:ON"
```



### 7.5 MQTT

**Befehle senden** (Topic: `{base_topic}/...`):


| Topic            | Payload                 | Funktion              |
| ---------------- | ----------------------- | --------------------- |
| `led{1-4}/set`   | `ON` / `OFF`            | LED schalten          |
| `air{1-4}/set`   | `ON` / `OFF`            | Timer starten/stoppen |
| `air{3-4}/reset` | `PRESS`                 | Timer zurücksetzen    |
| `air3/toh`       | `ON` / `OFF` / `TOGGLE` | Top-of-Hour           |
| `text/now/set`   | `TEXT`                  | NOW-Text setzen       |
| `text/next/set`  | `TEXT`                  | NEXT-Text setzen      |
| `text/warn/set`  | `TEXT`                  | WARN-Text setzen      |


**Status-Topics** (automatisch publiziert):


| Topic            | Payload            |
| ---------------- | ------------------ |
| `led{1-4}/state` | `ON` / `OFF`       |
| `air{1-4}/state` | `ON` / `OFF`       |
| `air{1-4}/time`  | Sekunden (Integer) |
| `air3/toh/state` | `true` / `false`   |
| `text/{now       | next               |


**Home Assistant Autodiscovery** erstellt automatisch:

- LED-Schalter (LED1–4)
- AIR-Timer-Schalter (AIR1–4)
- AIR-Zeit-Sensoren (AIR1–4 Time)
- Reset-Buttons (AIR3/AIR4)
- Top-of-Hour-Button (AIR3)
- Text-Entitäten (NOW, NEXT, WARN)



### 7.6 Befehlsreferenz



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
| `CMD:REBOOT`                 | OS-Neustart                         |
| `CMD:SHUTDOWN`               | OS-Herunterfahren                   |
| `CMD:QUIT`                   | OnAirScreen beenden                 |




#### Remote-Konfiguration (CONF)

Format: `CONF:GRUPPE:PARAMETER=WERT`

Änderungen werden erst nach `CONF:CONF:APPLY=TRUE` aktiv und gespeichert.


| Befehl                                          | Beschreibung            |
| ----------------------------------------------- | ----------------------- |
| `CONF:General:stationname=TEXT`                 | Stationsname            |
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
| `CONF:Timers:TimerAIR[1-4]Enabled=[True/False]` | AIR aktivieren          |
| `CONF:Timers:TimerAIR[1-4]Text=TEXT`            | AIR-Label               |
| `CONF:Timers:AIR[1-4]activebgcolor=COLOR`       | AIR-Hintergrund aktiv   |
| `CONF:Timers:AIR[1-4]activetextcolor=COLOR`     | AIR-Text aktiv          |
| `CONF:Timers:AIR[1-4]iconpath=PFAD`             | AIR-Icon-Pfad           |
| `CONF:Timers:TimerAIRMinWidth=PIXEL`            | AIR-Mindestbreite       |
| `CONF:CONF:APPLY=TRUE`                          | Konfiguration anwenden  |


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


---



## 11. Fehlerbehebung



### OnAirScreen startet nicht / Port belegt

- Prüfen, ob UDP-Port 3310 oder HTTP-Port 8010 bereits belegt ist
- Ports in **Advanced Settings → Network** ändern



### Fernsteuerung funktioniert nicht

- Firewall-Regeln für UDP/HTTP-Ports prüfen
- Korrekte IP-Adresse und Ports verwenden
- Mit `curl http://127.0.0.1:8010/api/status` lokal testen



### MQTT-Verbindung schlägt fehl

- MQTT-Broker erreichbar? (`mqttserver`, `mqttport`)
- Zugangsdaten korrekt?
- `enable MQTT support` aktiviert und mit **Apply** gespeichert?



### NTP-Warnung erscheint dauerhaft

- Lokalen NTP-Server konfigurieren (`NTP/ntpcheckserver`)
- Systemzeit manuell synchronisieren
- NTP-Prüfung deaktivieren, falls nicht benötigt



### Wetter-Widget zeigt nichts

- Gültigen OpenWeatherMap API-Key eingeben
- Korrekte City-ID verwenden
- **Test API** in den Einstellungen ausführen



### Einstellungen zurücksetzen

1. Einstellungsdialog öffnen (`Ctrl+S`)
2. Register **About** → **Enable Reset all settings button** aktivieren
3. **Reset all OnAirScreen settings to default** klicken
4. **Apply** klicken

---



## Anhang: Ereignisprotokollierung

OnAirScreen protokolliert intern folgende Ereignistypen:

- LED-Änderungen (Quelle: manual, autoflash, timedflash, API)
- AIR-Timer Start/Stopp/Reset
- Empfangene Befehle (UDP/HTTP)
- Warnungen hinzugefügt/entfernt
- Einstellungsänderungen
- Systemereignisse (Start, Beenden, Neustart)

Das Log-Level steuert die Ausgabemenge. Bei Problemen empfiehlt sich temporär `--loglevel DEBUG`.

---

*© 2012–2026 Sascha Ludwig · BSD-Lizenz · [astrastudio.de](http://www.astrastudio.de)*