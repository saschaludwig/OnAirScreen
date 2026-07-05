# OnAirScreen – User Manual

**Version:** 0.9.8  
**Author:** Sascha Ludwig, [astrastudio.de](http://www.astrastudio.de)  
**Project:** [OnAirScreen on GitHub](http://saschaludwig.github.io/OnAirScreen/)  
**German version:** [BEDIENUNGSANLEITUNG.md](BEDIENUNGSANLEITUNG.md)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Installation and Startup](#2-installation-and-startup)
3. [Main Screen](#3-main-screen)
4. [Keyboard Shortcuts (Hotkeys)](#4-keyboard-shortcuts-hotkeys)
5. [Settings Dialog](#5-settings-dialog)
6. [Features in Detail](#6-features-in-detail)
7. [Remote Control and API](#7-remote-control-and-api)
8. [Presets (Profiles)](#8-presets-profiles)
9. [Command-Line Options](#9-command-line-options)
10. [Configuration Storage Location](#10-configuration-storage-location)
11. [Troubleshooting](#11-troubleshooting)

---



## 1. Overview

OnAirScreen is a versatile **on-air lamp** solution for professional broadcast environments. The application combines:

- **4 status LEDs** (switchable, blinking, timed flash)
- **4 AIR timers** (microphone, phone, radio timer, stream timer)
- **Digital or analog clock** with optional text clock mode
- **Text lines** NOW, NEXT, and WARN (with priority system)
- **Weather widget** (OpenWeatherMap)
- **Remote control** via keyboard, UDP, HTTP, Web UI, MQTT, and REST API
- **Home Assistant integration** via MQTT Autodiscovery

The application starts in **fullscreen mode** by default with the mouse cursor hidden, making it suitable for dedicated studio monitors, Raspberry Pi setups, and touch-free operation.

OnAirScreen automatically adapts to different monitor aspect ratios and works on both **4:3** and **16:9/16:10** displays.

---



## 2. Installation and Startup



### Requirements

- **Python 3** with PyQt6 (when installing from source)
- Dependencies: see `requirements.txt`
- Network access for UDP/HTTP/MQTT remote control (optional)



### Starting from Source

```bash
python start.py
```



### Precompiled Versions

Ready-to-run binaries for Windows, Linux, macOS, and Raspberry Pi are available at [astrastudio.de/shop](https://www.astrastudio.de/shop/).

### First Startup

On first launch, default settings are loaded. Open the settings dialog with `Ctrl+S` (macOS: `Cmd+S`). Changes are only applied and saved after clicking **Apply**.

---



## 3. Main Screen

The main screen is divided into the following areas:

```
┌─────────────────────────────────────────────────────────┐
│  Station Name                                           │
│  Slogan                                                 │
├─────────────────────────────────────────────────────────┤
│  [LED1]  [LED2]  [LED3]  [LED4]     (Status LEDs)      │
├─────────────────────────────────────────────────────────┤
│  Text left           │  Clock / Logo │  Text right      │
│                      │  (ClockWidget)│                   │
├─────────────────────────────────────────────────────────┤
│  [AIR1 Mic]  [AIR3 Timer]  [AIR2 Phone]  [AIR4 Stream]  │
├─────────────────────────────────────────────────────────┤
│  NOW:  current title / IP addresses                       │
│  NEXT: next title / IPv6 addresses                      │
│  WARN: warning message (replaces NOW/NEXT when active)  │
└─────────────────────────────────────────────────────────┘
```



### Areas in Detail


| Area                | Widget                    | Function                                                 |
| ------------------- | ------------------------- | -------------------------------------------------------- |
| **Station Name**    | `labelStation`            | Station name, color configurable                         |
| **Slogan**          | `labelSlogan`             | Station tagline / claim                                  |
| **Status LEDs 1–4** | `buttonLED1`–`buttonLED4` | Large colored status indicators (ON AIR, PHONE, …)       |
| **Clock**           | `clockWidget`             | Digital or analog, with logo and optional weather widget |
| **AIR Timers 1–4**  | `AirLED_1`–`AirLED_4`     | Stopwatch timers with icon, label, and MM:SS display     |
| **NOW**             | `labelCurrentSong`        | First footer line (e.g. current song title)              |
| **NEXT**            | `labelNews`               | Second footer line (e.g. next title)                     |
| **WARN**            | `labelWarning`            | Warning message; hides NOW/NEXT when active              |


> **Note:** Status LEDs and AIR timers are primarily controlled via **keyboard** or **remote control**.



### Fullscreen Mode

- Default: fullscreen with hidden mouse cursor
- Toggle: `F` or `Ctrl+F` (macOS: `Cmd+F`)
- Fullscreen state is saved in settings (`General/fullscreen`)

---



## 4. Keyboard Shortcuts (Hotkeys)

> On **macOS**, `Ctrl` is replaced by `Cmd (⌘)`.



### Application


| Key(s)                            | Function                                        |
| --------------------------------- | ----------------------------------------------- |
| `F` / `Ctrl+F`                    | Toggle fullscreen                               |
| `Ctrl+S` / `Ctrl+,`               | Open settings dialog                            |
| `Q` / `Ctrl+Q` / `Ctrl+C` / `ESC` | Quit OnAirScreen                                |
| `I`                               | Display IP addresses in NOW/NEXT for 10 seconds |




### Status LEDs


| Key | Function     |
| --- | ------------ |
| `1` | LED 1 on/off |
| `2` | LED 2 on/off |
| `3` | LED 3 on/off |
| `4` | LED 4 on/off |




### AIR Timers


| Key(s)              | Function                     | Timer               |
| ------------------- | ---------------------------- | ------------------- |
| `M` / `/`           | Start/stop                   | AIR1 (Microphone)   |
| `P` / `*`           | Start/stop                   | AIR2 (Phone)        |
| `Space` / `,` / `.` | Start/stop                   | AIR3 (Radio Timer)  |
| `S`                 | Start/stop                   | AIR4 (Stream Timer) |
| `0` / `R`           | Reset to 0:00                | AIR3 (Radio Timer)  |
| `Alt+S`             | Reset to 0:00                | AIR4 (Stream Timer) |
| `T`                 | Top-of-Hour countdown on/off | AIR3                |
| `Enter` / `Return`  | Open timer input dialog      | AIR3                |




### OAS USB Keyboard (Special Mapping)


| Key            | Function                         |
| -------------- | -------------------------------- |
| Display key    | Toggle fullscreen                |
| Calculator key | Shut down host (`shutdown_host`) |


---



## 5. Settings Dialog

The settings dialog opens with `Ctrl+S` or `Ctrl+,`. It contains **7 tabs** (arranged vertically on the left):


| Tab                   | Content                                  |
| --------------------- | ---------------------------------------- |
| **General Settings**  | Station, LEDs, clock, NTP, logo, updates |
| **Advanced Settings** | Network, MQTT, formatting, weather       |
| **Timers**            | AIR timers 1–4                           |
| **Fonts**             | Fonts for all elements                   |
| **About**             | Version, license info, log level, reset  |
| **License**           | BSD license text                         |




### Buttons (bottom bar)


| Button               | Function                                          |
| -------------------- | ------------------------------------------------- |
| **Quit**             | Quit OnAirScreen                                  |
| **Delete Preset...** | Delete a saved preset                             |
| **Load Preset...**   | Load a preset                                     |
| **Save Preset...**   | Save current configuration as a preset            |
| **Close**            | Close dialog **without** saving (discard changes) |
| **Apply**            | Apply all settings, save, and close dialog        |


---



### 5.1 General Settings



#### Station Name and Slogan


| Setting       | Key                    | Default                           | Description             |
| ------------- | ---------------------- | --------------------------------- | ----------------------- |
| Station Name  | `General/stationname`  | `Radio Eriwan`                    | Station name            |
| Station Color | `General/stationcolor` | `#FFAA00`                         | Station name text color |
| Slogan        | `General/slogan`       | `Your question is our motivation` | Station slogan / claim  |
| Slogan Color  | `General/slogancolor`  | `#FFAA00`                         | Slogan text color       |


A live preview (`StationNameDemo`, `SloganDemo`) shows your input immediately.

#### Status LEDs 1–4

For each LED (groups `LED1`–`LED4`):


| Setting           | Key               | Default   | Description                         |
| ----------------- | ----------------- | --------- | ----------------------------------- |
| Enabled           | `used`            | `true`    | Show LED on main screen             |
| Text              | `text`            | see below | LED label                           |
| Active BG Color   | `activebgcolor`   | `#FF0000` | Background color (active)           |
| Active Text Color | `activetextcolor` | `#FFFFFF` | Text color (active)                 |
| Autoflash         | `autoflash`       | `false`   | Continuous blinking every 500 ms    |
| 20sec flash       | `timedflash`      | `false`   | Blink for 20 seconds, then turn off |


**Default LED texts:**


| LED  | Text       |
| ---- | ---------- |
| LED1 | ON AIR     |
| LED2 | PHONE      |
| LED3 | DOORBELL   |
| LED4 | EAS ACTIVE |


**Shared inactive colors** (group `LEDS`):


| Setting             | Key                 | Default   |
| ------------------- | ------------------- | --------- |
| Inactive BG Color   | `inactivebgcolor`   | `#222222` |
| Inactive Text Color | `inactivetextcolor` | `#555555` |




#### NTP Check


| Setting          | Key                  | Default        | Description                       |
| ---------------- | -------------------- | -------------- | --------------------------------- |
| Enable NTP-Check | `NTP/ntpcheck`       | `true`         | Enable time synchronization check |
| NTP-Check Server | `NTP/ntpcheckserver` | `pool.ntp.org` | NTP server address                |


When enabled, the system clock is regularly compared against the NTP server. Deviations > 0.3 seconds or connection errors trigger an **NTP warning** (priority -1, lowest priority).

> **Recommendation:** Use a local NTP server on your studio network, as `pool.ntp.org` can be unreliable at times.



#### Logo


| Setting       | Key               | Default                  | Description                   |
| ------------- | ----------------- | ------------------------ | ----------------------------- |
| Logo Path     | `Clock/logopath`  | `:/astrastudio_logo/...` | Path to logo image            |
| Logo Position | `Clock/logoUpper` | `false` (lower)          | Logo above or below the clock |


Buttons: `...` (file picker), `reset` (restore default logo).

#### OnAir Clock Mode / Colors


| Setting               | Key                          | Default          | Description                        |
| --------------------- | ---------------------------- | ---------------- | ---------------------------------- |
| Digital / Analog      | `Clock/digital`              | `true` (Digital) | Clock mode                         |
| Hours LEDs            | `Clock/digitalhourcolor`     | `#3232FF`        | Hour digit color                   |
| Seconds LEDs          | `Clock/digitalsecondcolor`   | `#FF9900`        | Seconds color                      |
| Digits LEDs           | `Clock/digitaldigitcolor`    | `#3232FF`        | All digit color                    |
| Show seconds          | `Clock/showSeconds`          | `false`          | Show seconds                       |
| Seconds Layout        | `Clock/showSecondsInOneLine` | `false`          | `separate` or `in one line`        |
| Static colon          | `Clock/staticColon`          | `false`          | Static colon (non-blinking)        |
| Use textclock         | `Clock/useTextClock`         | `true`           | Text clock (e.g. "it's 3 o'clock") |
| Replace IPs after 10s | `General/replacenow`         | `false`          | Replace text after IP display      |
| Replace with text     | `General/replacenowtext`     | *(empty)*        | Replacement text for NOW line      |




#### Update Check (compiled versions)


| Setting               | Key                         | Default   | Description                                   |
| --------------------- | --------------------------- | --------- | --------------------------------------------- |
| Check for updates     | `General/updatecheck`       | `false`   | Automatic update check on startup             |
| Update Key            | `General/updatekey`         | *(empty)* | Update key for paid versions (see note below) |
| Include Beta Versions | `General/updateincludebeta` | `false`   | Include beta versions                         |


> The update feature is intended for **precompiled (paid) versions**.
>
> To use update checking in the paid version, an **Update Key** must be entered. You can find it in the customer portal at [customer.astrastudio.de](https://customer.astrastudio.de) after placing your order.

---



### 5.2 Advanced Settings



#### Network


| Setting           | Key                         | Default       | Description               |
| ----------------- | --------------------------- | ------------- | ------------------------- |
| UDP Port          | `Network/udpport`           | `3310`        | Port for UDP commands     |
| HTTP Port         | `Network/httpport`          | `8010`        | Port for HTTP/Web UI      |
| Multicast Address | `Network/multicast_address` | `239.194.0.1` | Multicast address for UDP |




#### MQTT


| Setting             | Key                   | Default       | Description                   |
| ------------------- | --------------------- | ------------- | ----------------------------- |
| enable MQTT support | `MQTT/enablemqtt`     | `false`       | Enable MQTT integration       |
| MQTT Server         | `MQTT/mqttserver`     | `localhost`   | Broker hostname/IP            |
| MQTT Server Port    | `MQTT/mqttport`       | `1883`        | Broker port                   |
| MQTT User           | `MQTT/mqttuser`       | *(empty)*     | Username (optional)           |
| MQTT Password       | `MQTT/mqttpassword`   | *(empty)*     | Password (optional)           |
| MQTT Device Name    | `MQTT/mqttdevicename` | `OnAirScreen` | Device name in Home Assistant |


**MQTT Base Topic:** `onairscreen` + last 6 hex characters of the MAC address, e.g. `onairscreen_a1b2c3`.

#### Date and Time Format


| Setting            | Key                            | Default               | Description         |
| ------------------ | ------------------------------ | --------------------- | ------------------- |
| Date format        | `Formatting/dateFormat`        | `dddd, dd. MMMM yyyy` | Qt date format      |
| Time format        | `Formatting/isAmPm`            | `false` (24h)         | 24-hour or AM/PM    |
| Textclock Language | `Formatting/textClockLanguage` | `English`             | Text clock language |


**Available text clock languages:** English, German, Dutch, French

**Date format placeholders** (Qt notation, excerpt):


| Placeholder    | Meaning                   |
| -------------- | ------------------------- |
| `d` / `dd`     | Day (1–31 / 01–31)        |
| `ddd` / `dddd` | Weekday (short / long)    |
| `M` / `MM`     | Month (1–12 / 01–12)      |
| `MMM` / `MMMM` | Month name (short / long) |
| `yy` / `yyyy`  | Year (2 / 4 digits)       |




#### Weather Widget (OpenWeatherMap)


| Setting             | Key                              | Default            | Description                    |
| ------------------- | -------------------------------- | ------------------ | ------------------------------ |
| show Weather Widget | `WeatherWidget/owmWidgetEnabled` | `false`            | Enable weather widget          |
| API Key             | `WeatherWidget/owmAPIKey`        | *(empty)*          | OpenWeatherMap API key         |
| City ID             | `WeatherWidget/owmCityID`        | `2643743` (London) | OpenWeatherMap city ID         |
| Language            | `WeatherWidget/owmLanguage`      | `English`          | Weather description language   |
| Unit                | `WeatherWidget/owmUnit`          | `Celsius`          | Celsius, Fahrenheit, or Kelvin |


**Test API:** Button to test the API connection with current settings.

**Available weather languages:** Arabic, Bulgarian, Catalan, Czech, German, Greek, English, Persian (Farsi), Finnish, French, Galician, Croatian, Hungarian, Italian, Japanese, Korean, Latvian, Lithuanian, Macedonian, Dutch, Polish, Portuguese, Romanian, Russian, Swedish, Slovak, Slovenian, Spanish, Turkish, Ukrainian, Vietnamese, Chinese Simplified, Chinese Traditional

More information: [WeatherWidget Guide](https://www.astrastudio.de/wiki/onairscreen#weather-widget)

---



### 5.3 Timers

For each AIR timer (group `Timers`):


| Setting           | Key                     | Default      | Description               |
| ----------------- | ----------------------- | ------------ | ------------------------- |
| Enabled           | `TimerAIR{n}Enabled`    | `true`       | Show timer on main screen |
| Text              | `TimerAIR{n}Text`       | see below    | Timer label               |
| Active BG Color   | `AIR{n}activebgcolor`   | `#FF0000`    | Background color (active) |
| Active Text Color | `AIR{n}activetextcolor` | `#FFFFFF`    | Text color (active)       |
| Icon Path         | `air{n}iconpath`        | default icon | Path to timer icon        |


**Default AIR labels and icons:**


| Timer | Default Text | Default Icon    | Function                                 |
| ----- | ------------ | --------------- | ---------------------------------------- |
| AIR1  | Mic          | Microphone icon | Microphone stopwatch                     |
| AIR2  | Phone        | Phone icon      | Phone stopwatch                          |
| AIR3  | Timer        | Timer icon      | Radio timer (count up/down, Top-of-Hour) |
| AIR4  | Stream       | Antenna icon    | Stream timer                             |



| Setting       | Key                | Default | Description                            |
| ------------- | ------------------ | ------- | -------------------------------------- |
| AIR Min Width | `TimerAIRMinWidth` | `200`   | Minimum width of AIR displays (pixels) |


---



### 5.4 Fonts

Font family, size, and weight can be set individually for each UI element:


| Element      | Group `Fonts`                     | Default              |
| ------------ | --------------------------------- | -------------------- |
| LED1–4       | `LED{n}FontName/Size/Weight`      | FreeSans, 24pt, Bold |
| AIR1–4       | `AIR{n}FontName/Size/Weight`      | FreeSans, 24pt, Bold |
| Station Name | `StationNameFontName/Size/Weight` | FreeSans, 24pt, Bold |
| Slogan       | `SloganFontName/Size/Weight`      | FreeSans, 18pt, Bold |


The **Set Font...** button opens a font dialog. The preview shows the current font.

Fonts from the `fonts/` directory are also loaded at startup.

---



### 5.5 About


| Element            | Description                                             |
| ------------------ | ------------------------------------------------------- |
| Version            | Current OnAirScreen version                             |
| Distribution       | `OpenSource` or commercial distribution                 |
| Settings Path      | Path to the configuration file on this system           |
| Loglevel           | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, `NONE` |
| Enable Reset       | Checkbox to enable the reset button                     |
| Reset all settings | Resets **all** settings to defaults (cannot be undone)  |


---



## 6. Features in Detail



### 6.1 Status LEDs

Each LED can be switched on and off individually. In the active state, configured foreground and background colors are used; in the inactive state, the shared inactive colors apply.

**Blink modes:**

- **Autoflash:** Blinks continuously at 500 ms intervals while the LED is on
- **20sec flash:** Blinks for 20 seconds, then turns off automatically



### 6.2 AIR Timers

All AIR timers display elapsed time in **MM:SS** format (e.g. `3:45`).

#### AIR1 (Microphone) and AIR2 (Phone)

- Simple stopwatch: start/stop, seconds reset to 0 on start
- Control: `M`/`/` (AIR1), `P`/`*` (AIR2)



#### AIR3 (Radio Timer)

The most versatile timer with three operating modes:

1. **Count-Up:** Default mode, counts from 0:00 upward
2. **Count-Down:** Set via `AIR3TIME:seconds` or timer dialog
3. **Top-of-Hour (TOH):** Countdown to the next full hour (format MM:SS, e.g. `22:38`)

**Top-of-Hour behavior:**

- First call: Calculates remaining time until `:00`, starts countdown
- Second call (or `OFF`/`TOGGLE` while active): Stops and resets to `0:00`
- Synchronized with system clock, stops automatically at hour change
- API status: `"topOfHour": true` in `air[3]` when active

**Timer input dialog** (`Enter`):


| Input            | Meaning                           |
| ---------------- | --------------------------------- |
| `2,10` or `2.10` | 2 minutes 10 seconds (count-down) |
| `30`             | 30 seconds (count-down)           |
| `0`              | Count-up mode                     |




#### AIR4 (Stream Timer)

- Like AIR3, but without Top-of-Hour function
- Control: `S` (start/stop), `Alt+S` (reset)



### 6.3 Text Lines NOW, NEXT, WARN


| Line | API Command | Description                                        |
| ---- | ----------- | -------------------------------------------------- |
| NOW  | `NOW:TEXT`  | First footer line (current title, IP addresses, …) |
| NEXT | `NEXT:TEXT` | Second footer line (next title, …)                 |
| WARN | `WARN:TEXT` | Warning message with red warning mode              |


**Maximum text length:** 500 characters (input is automatically sanitized and truncated).

#### Warning System with Priorities


| Priority | Meaning                 | API Format    |
| -------- | ----------------------- | ------------- |
| -1       | NTP warning (automatic) | *(internal)*  |
| 0        | Normal / Legacy         | `WARN:TEXT`   |
| 1        | Medium                  | `WARN:1:TEXT` |
| 2        | High (highest)          | `WARN:2:TEXT` |


**Display rule:** The warning with the **highest priority** is shown. NTP warnings (-1) only appear when no other warning is active. When a warning is active, NOW and NEXT are hidden.

**Clearing warnings:**


| Method     | Command                              |
| ---------- | ------------------------------------ |
| Priority 0 | `WARN:` *(empty text)*               |
| Priority 1 | `WARN:1:` *(empty text after colon)* |
| Priority 2 | `WARN:2:` *(empty text after colon)* |
| Web UI     | X button next to the warning         |




### 6.4 Displaying IP Addresses

Press `I` (or automatically at startup) to show all local IPv4 addresses in **NOW** and IPv6 addresses in **NEXT** for 10 seconds.

If **Replace IPs after 10s** is enabled, the NOW line is replaced with the configured replacement text (`replacenowtext`) afterwards.

### 6.5 Clock

- **Digital:** LED-style digit display with configurable colors
- **Analog:** Classic clock face
- **Text clock:** Spoken time display (e.g. "it's a quarter past three")
- **Weather widget:** Optionally displayed next to the clock (OpenWeatherMap)



### 6.6 System Commands (API only)


| Command        | Function                   |
| -------------- | -------------------------- |
| `CMD:REBOOT`   | Restart operating system   |
| `CMD:SHUTDOWN` | Shut down operating system |
| `CMD:QUIT`     | Quit OnAirScreen           |


> These commands are **not** available through the settings UI, only via API/MQTT.

---



## 7. Remote Control and API

OnAirScreen supports four remote control channels:

### 7.1 UDP (Port 3310)

```bash
# Turn on LED1
echo "LED1:ON" > /dev/udp/127.0.0.1/3310

# Set NOW text
echo "NOW:Current Song Title" > /dev/udp/127.0.0.1/3310

# Change configuration
echo "CONF:LED1:text=STUDIO LIVE" > /dev/udp/127.0.0.1/3310
echo "CONF:CONF:APPLY=TRUE" > /dev/udp/127.0.0.1/3310
```



### 7.2 HTTP (Port 8010)

```bash
curl "http://127.0.0.1:8010/?cmd=LED1:ON"
curl "http://127.0.0.1:8010/?cmd=NOW:Current%20Song"
```



### 7.3 Web UI

Open in browser: `http://<IP-address>:8010/`

**Web UI features:**

- Real-time status for LEDs, AIR timers, and text fields
- WebSocket updates (with HTTP polling fallback)
- Dark mode with persistent theme setting
- LED and timer controls with toggle buttons
- Top-of-Hour button for AIR3
- Text input for NOW, NEXT, WARN
- Warnings with priority and delete button
- Version and distribution information



### 7.4 REST API

**Query status:**

```bash
curl http://127.0.0.1:8010/api/status
```

Response (simplified):

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

**Send command:**

```bash
curl "http://127.0.0.1:8010/api/command?cmd=LED1:ON"
```



### 7.5 MQTT

**Send commands** (topic: `{base_topic}/...`):


| Topic            | Payload                 | Function         |
| ---------------- | ----------------------- | ---------------- |
| `led{1-4}/set`   | `ON` / `OFF`            | Switch LED       |
| `air{1-4}/set`   | `ON` / `OFF`            | Start/stop timer |
| `air{3-4}/reset` | `PRESS`                 | Reset timer      |
| `air3/toh`       | `ON` / `OFF` / `TOGGLE` | Top-of-Hour      |
| `text/now/set`   | `TEXT`                  | Set NOW text     |
| `text/next/set`  | `TEXT`                  | Set NEXT text    |
| `text/warn/set`  | `TEXT`                  | Set WARN text    |


**Status topics** (published automatically):


| Topic            | Payload           |
| ---------------- | ----------------- |
| `led{1-4}/state` | `ON` / `OFF`      |
| `air{1-4}/state` | `ON` / `OFF`      |
| `air{1-4}/time`  | Seconds (integer) |
| `air3/toh/state` | `true` / `false`  |
| `text/{now       | next              |


**Home Assistant Autodiscovery** automatically creates:

- LED switches (LED1–4)
- AIR timer switches (AIR1–4)
- AIR time sensors (AIR1–4 Time)
- Reset buttons (AIR3/AIR4)
- Top-of-Hour button (AIR3)
- Text entities (NOW, NEXT, WARN)



### 7.6 Command Reference



#### Control Commands


| Command                      | Function                         |
| ---------------------------- | -------------------------------- |
| `LED{1-4}:[ON/OFF/TOGGLE]`   | Switch LED                       |
| `NOW:TEXT`                   | Set NOW text                     |
| `NEXT:TEXT`                  | Set NEXT text                    |
| `WARN:TEXT`                  | Set warning (priority 0)         |
| `WARN:1:TEXT`                | Set warning (priority Medium)    |
| `WARN:2:TEXT`                | Set warning (priority High)      |
| `WARN:`                      | Clear warning priority 0         |
| `WARN:1:`                    | Clear warning priority 1         |
| `WARN:2:`                    | Clear warning priority 2         |
| `AIR1:[ON/OFF/TOGGLE]`       | Microphone timer                 |
| `AIR2:[ON/OFF/TOGGLE]`       | Phone timer                      |
| `AIR3:[ON/OFF/RESET/TOGGLE]` | Radio timer                      |
| `AIR3TIME:seconds`           | Set radio timer to seconds value |
| `AIR3TOH:[ON/OFF/TOGGLE]`    | Top-of-Hour countdown            |
| `AIR4:[ON/OFF/RESET/TOGGLE]` | Stream timer                     |
| `CMD:REBOOT`                 | OS reboot                        |
| `CMD:SHUTDOWN`               | OS shutdown                      |
| `CMD:QUIT`                   | Quit OnAirScreen                 |




#### Remote Configuration (CONF)

Format: `CONF:GROUP:PARAMETER=VALUE`

Changes are only applied and saved after `CONF:CONF:APPLY=TRUE`.


| Command                                         | Description           |
| ----------------------------------------------- | --------------------- |
| `CONF:General:stationname=TEXT`                 | Station name          |
| `CONF:General:slogan=TEXT`                      | Slogan                |
| `CONF:General:stationcolor=COLOR`               | Station color         |
| `CONF:General:slogancolor=COLOR`                | Slogan color          |
| `CONF:General:replacenow=[True/False]`          | Enable IP replacement |
| `CONF:General:replacenowtext=TEXT`              | Replacement text      |
| `CONF:LED[1-4]:used=[True/False]`               | Enable LED            |
| `CONF:LED[1-4]:text=TEXT`                       | LED text              |
| `CONF:LED[1-4]:activebgcolor=COLOR`             | LED active background |
| `CONF:LED[1-4]:activetextcolor=COLOR`           | LED active text       |
| `CONF:LED[1-4]:autoflash=[True/False]`          | Autoflash             |
| `CONF:LED[1-4]:timedflash=[True/False]`         | 20-second flash       |
| `CONF:Clock:digital=[True/False]`               | Digital/Analog        |
| `CONF:Clock:showseconds=[True/False]`           | Show seconds          |
| `CONF:Clock:secondsinoneline=[True/False]`      | Seconds on one line   |
| `CONF:Clock:staticcolon=[True/False]`           | Static colon          |
| `CONF:Clock:digitalhourcolor=COLOR`             | Hour color            |
| `CONF:Clock:digitalsecondcolor=COLOR`           | Seconds color         |
| `CONF:Clock:digitaldigitcolor=COLOR`            | Digit color           |
| `CONF:Clock:logopath=PATH`                      | Logo path             |
| `CONF:Clock:logoupper=[True/False]`             | Logo on top           |
| `CONF:Network:udpport=PORT`                     | UDP port              |
| `CONF:Network:tcpport=PORT`                     | HTTP port             |
| `CONF:Timers:TimerAIR[1-4]Enabled=[True/False]` | Enable AIR            |
| `CONF:Timers:TimerAIR[1-4]Text=TEXT`            | AIR label             |
| `CONF:Timers:AIR[1-4]activebgcolor=COLOR`       | AIR active background |
| `CONF:Timers:AIR[1-4]activetextcolor=COLOR`     | AIR active text       |
| `CONF:Timers:AIR[1-4]iconpath=PATH`             | AIR icon path         |
| `CONF:Timers:TimerAIRMinWidth=PIXELS`           | AIR minimum width     |
| `CONF:CONF:APPLY=TRUE`                          | Apply configuration   |


**Colors:** Hex format (`#FF0000`) or color names.

---



## 8. Presets (Profiles)

Presets allow saving and loading complete configurations.


| Action | Button               | Description                             |
| ------ | -------------------- | --------------------------------------- |
| Save   | **Save Preset...**   | Save current configuration as JSON file |
| Load   | **Load Preset...**   | Load and apply a saved preset           |
| Delete | **Delete Preset...** | Remove preset file                      |


**Storage location:** `<configuration directory>/presets/<name>.json`

Presets contain metadata (name, version) and the full configuration as JSON. After loading, **Apply** must be clicked for settings to take effect.

> **Note:** MQTT settings are saved in the configuration file but are **intentionally not** included in preset exports. MQTT credentials are installation- and environment-specific and should not be exported together with visual profiles.

---



## 9. Command-Line Options

```bash
python start.py --loglevel DEBUG
python start.py -l WARNING
```


| Option             | Values                                          | Description                    |
| ------------------ | ----------------------------------------------- | ------------------------------ |
| `-l`, `--loglevel` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Override log level (not saved) |


The log level from settings (`About/Loglevel`) additionally supports `NONE` (no logging).

---



## 10. Configuration Storage Location

Settings are stored via Qt `QSettings`:

- **Organization:** `astrastudio`
- **Application:** `OnAirScreen`

The exact path is shown in the **About** tab under **Settings Path**. Typical locations:


| Platform | Path                                                           |
| -------- | -------------------------------------------------------------- |
| Linux    | `~/.config/astrastudio/OnAirScreen.conf`                       |
| macOS    | `~/Library/Preferences/com.astrastudio.OnAirScreen.plist`      |
| Windows  | Registry: `HKEY_CURRENT_USER\Software\astrastudio\OnAirScreen` |


---



## 11. Troubleshooting



### OnAirScreen won't start / port in use

- Check if UDP port 3310 or HTTP port 8010 is already in use
- Change ports in **Advanced Settings → Network**



### Remote control not working

- Check firewall rules for UDP/HTTP ports
- Use correct IP address and ports
- Test locally with `curl http://127.0.0.1:8010/api/status`



### MQTT connection fails

- Is the MQTT broker reachable? (`mqttserver`, `mqttport`)
- Are credentials correct?
- Is `enable MQTT support` enabled and saved with **Apply**?



### NTP warning appears permanently

- Configure a local NTP server (`NTP/ntpcheckserver`)
- Synchronize system time manually
- Disable NTP check if not needed



### Weather widget shows nothing

- Enter a valid OpenWeatherMap API key
- Use correct city ID
- Run **Test API** in settings



### Reset settings

1. Open settings dialog (`Ctrl+S`)
2. Tab **About** → enable **Enable Reset all settings button**
3. Click **Reset all OnAirScreen settings to default**
4. Click **Apply**

---



## Appendix: Event Logging

OnAirScreen internally logs the following event types:

- LED changes (source: manual, autoflash, timedflash, API)
- AIR timer start/stop/reset
- Received commands (UDP/HTTP)
- Warnings added/removed
- Settings changes
- System events (start, quit, reboot)

The log level controls output verbosity. For troubleshooting, temporarily use `--loglevel DEBUG`.

---

*© 2012–2026 Sascha Ludwig · BSD License · [astrastudio.de](http://www.astrastudio.de)*