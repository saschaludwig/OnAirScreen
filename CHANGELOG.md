# Changelog
All notable changes to this project will be documented in this file.

## [TBA]
### Added
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
- fixed calling API error when WeatherWidget is disabled (Thanks to https://github.com/ywiskerke)
- added dutch language support (Thanks to https://github.com/ywiskerke)
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
