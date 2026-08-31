# Changelog

All notable changes to this project will be documented in this file.

## [TBA]

### Added

- Persistent log folder with rotating `onairscreen.log`, crash reports for uncaught Python exceptions, and `fault.log` for native faults; About tab shows the path and can open the folder

### Fixed

- Fresh installs without `Audio/layout` now use L/R + LUFS (`both`) instead of falling back to L/R only

## [1.0.0beta4]

### Changed

- OnAirScreen Source-Available License (OASL 1.0): source may be used, modified, and redistributed; compiled/binary redistribution requires written permission
- Application file headers point to OASL; Settings License tab shows OASL plus third-party notices

## [1.0.0beta3]

### Added

- TOTH Timer label text is configurable (`Timers/TimerTOTHText`, default `TOTH Timer`)
- Bundled Noto Sans (Regular, Bold, Italic, Bold Italic) as an additional font family alongside Roboto
- Web-UI Loudness I+LRA tile shows live I (LUFS) and LRA (LU); `lufsI` / `lra` in `/api/status` and WebSocket; MQTT sensors `{base}/lufs/i` and `/lra`; OSC `/oas/lufs/i` and `/oas/lufs/lra`

### Fixed

- Weather widget text shadows work again under PySide6 (drop-shadow effects are parented so they are not garbage-collected)
- AoIP source change without RTP now drops the meters to the floor instead of freezing on the previous level

### Changed

- Settings **Network** and **Time Source** tabs align labels and fields in a shared two-column form layout
- License dialog and `THIRD_PARTY_LICENSES.md` now document PySide6/Qt (LGPLv3), the analog clock BSD example, and Roboto (SIL OFL) instead of PyQt GPL
- Application BSD text removed from `LICENSE` and the Settings license tab pending the forthcoming source license
- Default audio meter layout is L/R plus programme LUFS (`both`); default width is 115px and the maximum is 150px

## [1.0.0beta2]

### Fixed

- Digital clock no longer aborts when a time sample has no SMPTE frame count
- Startup no longer crashes when listing host addresses under PySide6

### Changed

- Qt binding switched from PyQt6 to PySide6
- Settings window opens at 700×800 and is capped at 800px height so it fits smaller screens, audio meters tab uses two columns
- Station and slogan color pickers in Settings no longer show a live preview
- dBTP meter hides the orange ceiling peg when the Too Loud indicator is off

## [1.0.0beta1]

### Added

- Meter layouts: L/R only, programme LUFS only, or both (`Audio/layout`: `lr` / `lufs` / `both`; BBC PPM stays L/R-only)
- Programme LUFS bar (EBU R128): momentary M with a short-term S tick (I and LRA stay off until started)
- Optional gated Integrated I + LRA (off until started): `LUFSI:START` / `STOP` / `TOGGLE` / `RESET` via UDP, HTTP, OSC, MQTT, Web-UI, and Companion
- MQTT Home Assistant: Loudness I+LRA switch and reset button (`{base}/lufs/integrated/set` and `/state`); `lufsIntegrated` in `/api/status` and WebSocket
- Right-click **Reset I+LRA** on the main screen (when meters are enabled); `LUFSI:RESET` restarts a running session or hides frozen I/LRA when stopped
- Existing configs with `Audio/unit=lufs` (no `layout` key) migrate to layout `lufs` and L/R unit `dbtp`
- AIR3 shows ▲ (count-up) or ▼ (count-down) under the timer icon
- AIR3 shows `TOTH Timer` while top-of-hour countdown is active, then restores the configured label
- Web-UI: AIR3 time input (`m:ss`, `m,ss`, or seconds) and count-up vs. countdown in the status tile
- Web-UI: silence alarm and loudness I+LRA in live status; keys `1`–`4` toggle LEDs (ignored while typing)
- Web-UI: persistent connection badge (Live / Polling / Offline)
- `countDown` in `/api/status` for AIR timers (`true` while AIR3/AIR4 is counting down)
- Bitfocus Companion HTTP module (`astrastudio-OnAirScreen`) as the recommended Stream Deck path; Generic OSC remains as an alternative
- OSC remote control on UDP port 8000 (`/oas/...`): set commands, query-reply to the sender, optional status push for Companion Generic OSC
- Settings **Network** tab (after General) for UDP, HTTP, multicast, MQTT, and OSC; **General** / **Advanced** tab titles no longer include “Settings”
- Silence Detection on the current audio source (Local / Livewire / AES67): dBFS threshold, duration (default 10 s), recovery time, optional OAS WARN, optional HTTP GET on trigger
- Silence alarm as API boolean (`silence` in `/api/status` and WebSocket) and MQTT `{base}/silence/active` (Home Assistant binary sensor)
- Option to treat a missing device/stream as silence (on by default)
- DNS-safe instance name (Settings **General**, default `Studio-1`, max 32 characters, LDH hostname label) so each OnAirScreen can be identified by location; shown in the Web-UI, `/api/status` (`instance`), MQTT `{base}/instance/state`, and as a Home Assistant sensor; HA device name becomes `OnAirScreen (Studio-1)`
- `CONF:General:instancename=TEXT` to set the instance name remotely
- Double-click on the main screen toggles fullscreen
- Right-click context menu on the main screen: Toggle Fullscreen, Settings

### Changed

- Default meter width is 79 px (extra width still thickens the L/R bars)
- `CONF:Audio:unit=lufs` now switches the layout to programme LUFS instead of using LUFS as an L/R unit
- Default audio meter unit is dBTP; TooLoud is enabled by default

### Fixed

- Clock no longer freezes after an NTP timeout: NTP results are delivered on the GUI thread, and a watchdog restarts a dead clock timer
- Clock watchdog no longer aborts when a time sample is missing
- Opening Settings no longer paints a running AIR timer (including TOTH) as inactive or resets its displayed time to 0:00
- Web-UI restores the WebSocket after falling back to HTTP polling
- Opening Settings again brings the existing window to the front instead of reloading it

## [0.9.9beta1]

### Added

- Stereo audio meters on the left (on by default, Local Input): L/R bars with RMS fill and peak overlay
- Display units: **dBFS**, **dBTP** (true peak), **LUFS** (momentary), **BBC PPM** (Type IIa, marks 1–7)
- Peak hold marker (default 1.5 s, can be disabled) and display style **Solid** or **Bargraph**
- LUFS reference peg via presets (EBU R128 −23, ATSC A/85 −24, AES −16/−18, Custom)
- Adjustable meter width (extra width goes into thicker L/R bars)
- Optional **TOO LOUD** action: on-screen warning (priority 1) or trigger LED 1–4 when true peak exceeds the threshold; dBTP ceiling peg uses that threshold
- Audio sources: **Local Input** (PortAudio), **Livewire** AoIP multicast, **AES67** multicast RTP (SAP or pasted SDP)
- Shared **AoIP Interface** for Livewire/AES67 IGMP join (empty = system route)
- Livewire: advertised sources listed while Settings are open (`239.192.255.3` UDP 4001); pick a name or enter channel 1–32767 (channel *N* → `239.192.0.0+N` UDP 5004, L24/48 kHz stereo)
- AES67: SAP discovery on `239.255.255.255` and RFC 2974 `224.2.127.254` UDP 9875 while Settings are open; live stream list (None / SAP / pasted SDP); L16/L24 at 44.1/48/96 kHz, meters use the first two channels
- Settings **Audio Meters** tab and `CONF:Audio:*` keys (source, unit, TooLoud, meter width, LUFS reference, peak hold, display style)

### Fixed

- Date display follows the configured `Formatting/dateFormat` setting
- Digital AM/PM clock: midnight displays as 12 (12-hour mapping)
- NTP lock LED no longer stays green when the server is unreachable
- Autoflash / timedflash LED regression and Web-UI blink
- MQTT reconnect and AES67 capture restart stop during application quit

## [0.9.8]

### Added

- Persist windowed position and size across restarts (`Window/geometry`); restored when not in fullscreen
- OpenWeatherMap city search in Settings: type a city name next to City ID, Find, pick a match
- Mask Update Key, MQTT password, and OpenWeatherMap API key; slashed-eye toggle reveals them
- Time Source settings tab: Local System Clock, NTP Server, PTPv2 IEEE 1588-2008, or LTC
- NTP and PTP steer an independent display clock (monotonic timebase); the OS clock is never set
- PTP: software slave on 224.0.1.129 UDP 319/320, configurable interface (independent of AoIP) and domain 0–255
- LTC: Leo Bodnar LBE-1110 USB-serial SMPTE reader, or SMPTE LTC decoded from a local PortAudio input (Left/Right); display shows `HH:MM:SS:FF`, holds last timecode on signal loss
- LTC audio uses its own capture device (not Audio Meters / Livewire / AES67); opening the same device for meters and LTC can fail on some hosts
- LTC unlock WARN (`Clock not LTC synchronized` etc.) is optional and off by default; the `LTC NOT LOCKED` LED always remains
- AES67: SAP discovery on `239.255.255.255` and RFC 2974 `224.2.127.254` (UDP 9875)
- PTP: apply TAI−UTC only when the master announces the PTP timescale (fixes ~37s offset vs software ptp4l)
- NTP Check settings moved from General to the Time Source tab
- Clock lock LED (bottom right, seconds-LED size): green when the selected time source is locked, red when not; caption `PTP LOCK` / `NTP LOCK` / `LTC LOCK` (or `NOT LOCKED`)
- NTP Server field stays enabled when Time Source is NTP, even if NTP-Check is off
- Top-of-Hour countdown for Radio Timer (AIR3): wall-clock synchronized countdown to the next full hour (display format M:SS)
- Top-of-Hour: Hotkey `T` to toggle countdown (stop resets display to 0:00)
- Top-of-Hour: API command `AIR3TOH:[ON/OFF/TOGGLE]` via UDP and HTTP
- Top-of-Hour: MQTT topic `{base_topic}/air3/toh` and status topic `air3/toh/state` (Home Assistant button via Autodiscovery)
- Top-of-Hour: Web-UI "Top of Hour" button for AIR3
- Top-of-Hour: `topOfHour` field in `/api/status` for `air[3]`
- API: `TOGGLE` for LED1–4, AIR1, AIR2, and AIR4 (same ON/OFF/TOGGLE pattern as AIR3)
- German and English user manuals (`BEDIENUNGSANLEITUNG.md`, `USER_MANUAL.md`) with README links
- Refactoring: Extracted NTP management to ntp_manager.py module
- Refactoring: Extracted font loading to font_loader.py module
- Refactoring: Extracted signal handlers to signal_handlers.py module
- Refactoring: Extracted system operations to system_operations.py module
- Refactoring: Extracted status export to status_exporter.py module
- Refactoring: Extracted UI updates to ui_updater.py module
- Refactoring: Extracted hotkey management to hotkey_manager.py module
- Refactoring: Extracted logging configuration to logging_config.py module
- Error Handling: Unified error handling system with custom exception hierarchy
- Error Handling: Custom exceptions for all error types (Network, Command, Configuration, Validation, API, Encoding, Widget)
- Error Handling: Consistent logging strategy with log_exception() helper function
- Error Handling: HTTP error response mapping based on exception types
- Error Handling: Comprehensive exception handling in network.py, command_handler.py, start.py, weatherwidget.py, mqtt_client.py, settings_functions.py
- Tests: Unit tests for exceptions module (26 tests covering all exception types and logging helper)
- MQTT integration with Home Assistant Autodiscovery support
- MQTT: LED switches (LED1-4) for controlling LEDs via MQTT
- MQTT: AIR timer switches (AIR1-4) for starting/stopping timers
- MQTT: AIR timer sensors (AIR1-4 Time) for displaying elapsed time in seconds
- MQTT: Reset buttons (AIR3/AIR4 Reset) for resetting timers
- MQTT: Text entities (NOW, NEXT, WARN) for setting text fields
- MQTT: Automatic status updates after state changes
- MQTT: Automatic reconnection and autodiscovery re-publishing on reconnect
- Settings: MQTT configuration (Server, Port, Username, Password, Device Name)
- MQTT: Base topic automatically generated from "onairscreen" + unique device ID (last 6 hex characters of MAC address)
- Web-UI: Dark Mode support with theme toggle button and automatic persistence
- Web-UI: Warning priority system with support for NTP warnings (priority -1), normal warnings (priority 0), medium priority (1), and high priority (2)
- Web-UI: Display NTP warnings in Current Status section with blue color coding
- Web-UI: X button to delete warnings directly from status display (for priority 0-2)
- Web-UI: Improved Current Status layout - organized in rows (LED1-4, AIR1-4, NOW/NEXT)
- Web-UI: Compact design for NOW/NEXT status items and input fields
- Web-UI: AIR Timer Controls now show timer labels (Mic, Phone, etc.) directly on buttons
- Web-UI: NOW/NEXT input fields placed side by side (50% width each)
- Settings: Preset/Profile management - save, load, list, and delete configuration presets as JSON files
- Settings: UI buttons for preset management (Save, Load, Delete)
- Settings: Log level configuration (DEBUG, INFO, WARNING, ERROR, CRITICAL, NONE) with ComboBox in General settings
- Command-line: --loglevel option to override log level settings (temporary, not saved)
- Tests: Comprehensive unit test coverage for defaults.py (17 tests for get_default() function)
- Tests: Comprehensive unit test coverage for weatherwidget.py (23 tests for WeatherWidget class)
- Tests: Comprehensive unit test coverage for clockwidget.py (25 tests for ClockWidget class)
- Tests: Extended test coverage for start.py with 11 tests for set_log_level() function
- Security: Comprehensive input validation for all network commands (UDP/HTTP)
- Security: Text input sanitization for NOW, NEXT, WARN commands (removes control characters, dangerous patterns)
- Security: Command value validation for LED, AIR, CMD commands (validates allowed values)
- Security: Length limits for text inputs (500 chars for NOW/NEXT/WARN, 1000 for CONF)
- Security: Input validation for CONF commands (stationname, slogan, LED text, AIR text)
- Refactoring: Extracted NTP management to ntp_manager.py module
- Refactoring: Extracted font loading to font_loader.py module
- Refactoring: Extracted signal handlers to signal_handlers.py module
- Refactoring: Extracted system operations to system_operations.py module
- Refactoring: Extracted status export to status_exporter.py module
- Refactoring: Extracted UI updates to ui_updater.py module
- Refactoring: Extracted hotkey management to hotkey_manager.py module
- Refactoring: Extracted logging configuration to logging_config.py module

### Changed

- Fonts settings: family combo (includes bundled Roboto), separate size, bold, and per-row reset instead of the native font dialog
- LED1–4 default font size is 32pt
- Default UI font is now bundled Roboto (FreeSans removed); existing FreeSans settings are mapped to Roboto
- Audio meters are enabled by default with Local Input (`device`) as the source
- Require Python 3.11 or newer; bump websockets to >=17.1
- Clock: Digital clock second LEDs and colon now repaint aligned to wall-clock second boundaries (removes visible lag at second rollover)
- Refactoring: Reduced start.py from 1711 lines to ~1415 lines by extracting logical components into separate modules
- Refactoring: Improved code modularity and maintainability by separating concerns into dedicated modules
- Refactoring: All tests updated to use new modular structure (583 tests passing)
- Code Quality: Removed unnecessary backward compatibility code after refactoring
- Code Quality: Simplified initialization code using for loops for LED and AIR timer setup
- Error Handling: Replaced generic Exception handling with specific custom exceptions throughout codebase
- Error Handling: Standardized error logging with consistent format and context information
- Error Handling: Improved HTTP error responses with appropriate status codes based on error types
- Web-UI: Fixed dark mode flash on page reload by setting theme immediately in HTML head
- Web-UI: Restructured status display for better organization and space efficiency
- Command Handler: Enhanced WARN command to support priority format (WARN:Prio:Text)
- MainScreen: Implemented priority-based warning system with array index mapping
- MainScreen: Updated process_warnings() to display highest priority warning (excluding NTP if others exist)
- MainScreen: Simplified update_ntp_status() to use priority -1 directly
- API: get_status_json() now returns warnings array with priorities in addition to legacy warn field

## [0.9.7beta4]

### Added

- WebSocket support for Web-UI: Real-time status updates via WebSocket connections (replaces HTTP polling)
- Integration tests for network communication (UDP, HTTP, WebSocket)
- Extended unit tests for timer_manager, event_logger, and command_handler modules
- Test tools: cmdtest_multicast.py and diagnose_multicast.py for multicast testing and diagnostics
- Central configuration file (defaults.py) for all default values
- Type hints and docstrings throughout codebase
- Context manager (settings_group) for QSettings group operations

### Changed

- Network: Improved multicast support for macOS - UDP server now explicitly joins on loopback interface too
- Network: Improved socket configuration for reliable multicast sending on macOS
- Network: HTTP server now uses ReusableHTTPServer with SO_REUSEADDR to prevent TIME_WAIT issues
- Security: Replaced os.system() with subprocess.run() for secure system command execution
- Error handling: Enhanced error handling for network operations, timer input parsing, and color validation
- Error handling: Graceful degradation when resources (fonts, templates) are missing
- Makefile: Follow symlinks when searching for rcc tool in Homebrew installations
- Fixed: IP addresses now correctly displayed at startup

## [0.9.7beta3]

### Added

- Web-UI: Complete web-based remote control interface accessible via HTTP
- Web-UI: Real-time status display for LEDs, AIR timers, and text fields (NOW/NEXT/WARN)
- Web-UI: LED control buttons with toggle functionality
- Web-UI: AIR timer controls with start/stop and reset (for AIR3/AIR4) buttons
- Web-UI: Text input controls for NOW, NEXT, and WARN messages
- Web-UI: REST-style API endpoints (/api/status, /api/command)
- Web-UI: Version and distribution information displayed in top-right corner
- Web-UI: Modal dialog with overlay for connection errors (always visible, dims background)
- Web-UI: Clear buttons for NOW/NEXT text inputs
- Web-UI: Current NOW/NEXT/WARN texts displayed in status panel
- API: Status endpoint now includes version and distribution information

### Changed

- Web-UI: HTML template moved from network.py to separate templates/web_ui.html file for better maintainability
- Web-UI: Connection error modal now disables all controls when connection is lost
- Network: HTTP server now supports Web-UI in addition to command API
- Network: Improved thread-safety for GUI operations from HTTP thread using pyqtSignal

## [0.9.7beta2]

### Added

- Event logging system for tracking LED changes, AIR timer events, commands, warnings, and system events
- Tooltips for all settings widgets to improve user experience

### Changed

- Fixed weather widget API calls when widget is disabled or no API key is configured
- Removed unused font button

## [0.9.7beta1]

### Added

- Command test scripts for HTTP and UDP testing (utils/cmdtest_http.sh, utils/cmdtest_udp.sh)
- Show version, distribution and settings path in about dialog
- Fonts/COPYING file

### Changed

- Major code refactoring: extracted command handler, network module, and timer manager to separate modules
- Use context manager for QSettings groups
- Consolidated text setters and timer reset methods
- Consolidated AIR reset and start_stop methods
- Consolidated LED toggle methods
- Consolidated set_station_color() and set_slogan_color() methods
- Consolidated set_led1-4() methods into generic method
- Split restore_settings_from_config() into smaller methods
- Optimized led_logic() method
- Optimized font setup in restore_settings_from_config()
- Modernized string formatting to f-strings
- Refactored parse_cmd() using command pattern
- Added logging, type hints, and docstrings throughout codebase
- Fixed crash when UDP/HTTP ports are empty
- Updated copyright strings
- Updated settings.ui

## [0.9.6 beta2]

### Added

- options to change icons on all 4 timers

## [0.9.6 beta1]

### Added

- option for preferred logo position

## [0.9.5]

### Changed

- fixed textclock when hour == 12
- fixed wrong default font size for slogan
- refactored text clock code
- fixed crash when using API to configure boolean fields
- API: you can now use colors in web notation (#00FF00) and hex notation (0x00FF00)
- fixed slogan font in settings
- fixed analog clock style

### Added

- french localization for textclock
- left LEDs are now customizable (text/color)
- settings for left LEDs minimum width
- IPs can be automatically replaced with custom text after 10s
- API commands for added functions
- New Hotkey "I" to display IPs for 10 seconds
- added option to select between no/separate/combined seconds display
- added logo to analog clock

## [0.9.4]

### Changed

- fixed crash when OWM API responds with strange JSON
- OWM API uses https now
- fixed calling API error when WeatherWidget is disabled (Thanks to [ywiskerke](https://github.com/ywiskerke))
- added dutch language support (Thanks to [ywiskerke](https://github.com/ywiskerke))
- fixed wrong hour in xx:45 textclock display

## [0.9.3]

### Added

- Alt-S now resets stream timer
- added enable/disable option for timers 1-4
- fixed unit display in weather widget
- fixed crash introduced through a lazy print
- fixed logo size calculation for portrait format logos
- customizable font and size for various elements

## [0.9.2]

### Changed

- Fix crash when timer value is not numeric
- Fix show/hide of weather widget
- Fix HTTP API full UTF-8 support
- Fix crash when restoring config on .ini style platforms, boolean type mismatch
- Localized "WEATHER" string in Weather Widget

### Added

- HTTP API
- Update check support
- Show/hide LED1-4
- Show/hide TextClock

## [0.9.1 beta4]

### Changed

- Fix window resize when displaying long text in NOW/NEXT/WARN

## [0.9.1 beta3]

### Added

- this changelog
- selectable blinking/static colon for HH:MM in digital clock mode

### Changed

- Fix update of weatherwidget when location is changed
