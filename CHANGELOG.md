# Changelog
All notable changes to this project will be documented in this file.

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
