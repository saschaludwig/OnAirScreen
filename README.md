# OnAirScreen
Multi purpose "OnAir Lamp" solution targeted for use in professional broadcast environments
http://saschaludwig.github.io/OnAirScreen/

<a href="https://www.buymeacoffee.com/saschaludwig" target="_blank"><img src="https://img.buymeacoffee.com/button-api/?text=Thanks%20for%20OnAirScreen&emoji=%E2%98%95&slug=saschaludwig&button_colour=FFDD00&font_colour=000000&font_family=Arial&outline_colour=000000&coffee_colour=ffffff" alt="Buy Me A Coffee" height="45px"></a>

<a href='https://ko-fi.com/L3L8BKHYT' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi1.png?v=3' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

#### Precompiled Linux/Win/Mac versions
If you need ready-to-run Linux/Win/Mac executables, please visit https://www.astrastudio.de/shop/. \
I also have a RaspberryPi version and a ready-to-run RaspberryPi SD-Card image in my shop. \
And if you need extended support, please contact me.

#### Screenshots
<img src="https://cdn.rawgit.com/saschaludwig/OnAirScreen/gh-pages/images/oas_v2.png" width="600px">
<img src="https://cdn.rawgit.com/saschaludwig/OnAirScreen/gh-pages/images/oas_settings_1.png" width="400px"><img src="https://cdn.rawgit.com/saschaludwig/OnAirScreen/gh-pages/images/oas_settings_2.png" width="400px"><img src="https://cdn.rawgit.com/saschaludwig/OnAirScreen/gh-pages/images/oas_settings_2.png" width="400px">

#### Pictures of OnAirScreen in use
<img src="https://cdn.rawgit.com/saschaludwig/OnAirScreen/gh-pages/images/OAS1.jpg" width="220px"><img src="https://cdn.rawgit.com/saschaludwig/OnAirScreen/gh-pages/images/OAS2.jpg" width="220px"><img src="https://cdn.rawgit.com/saschaludwig/OnAirScreen/gh-pages/images/OAS3.jpg" width="220px"><img src="https://cdn.rawgit.com/saschaludwig/OnAirScreen/gh-pages/images/OAS4.jpg" width="220px">

#### Features
 * flexible integration into existing studio setups
 * customizable logo, colors and labels
 * 4:3 and 16:9/16:10 monitor aspect ratio support
 * easy installation (Win/Linux/Mac binaries available)
 * runs on RaspberryPi
 * runs on Windows, Mac, Linux
 * controlled via keyboard and network
 * Weather Widget
 * static or blinking colon in digital clock mode
 * OnAir Timer, Stopwatch, Countdown and more

#### OnAirScreen Function Keys
| Hotkeys                           | Function                |
|-----------------------------------|-------------------------|
| Ctrl+F or F                       | Toggle fullscreen       |
| Ctrl+Q or Q or Ctrl+C or ESC      | Quit OnAirScreen        |
| Ctrl+S or Ctrl+,                  | Open settings dialog    |
| Space or 0                        | Timer start/stop        |
| . or , or R                       | Timer reset to 0:00     |
| 1                                 | LED1 on/off             |
| 2                                 | LED2 on/off             |
| 3                                 | LED3 on/off             |
| 4                                 | LED4 on/off             |
| M or /                            | Mic Timer start/stop    |
| P or *                            | Phone Timer start/stop  |
| Enter                             | opens set timer dialog  |

On OSX use the `command ⌘` key instead of `Ctrl`

#### OnAirScreen API Commands

##### API via UDP

OnAirScreen can receive API commands via UDP port 3310<br>
Here is an easy example on how to control a local OnAirScreen instance on a linux system.

Set LED1 Text to "FOO" and switch LED1 on:

```Shell
echo "CONF:LED1:text=FOO" > /dev/udp/127.0.0.1/3310
echo "LED1:ON" > /dev/udp/127.0.0.1/3310
```

##### API via HTTP

OnAirScreen can receive API commands via HTTP (port 8010 by default).<br>
Here is an easy example of how to control a local OnAirScreen instance on a linux system.

Set LED1 Text to "FOO" and switch LED1 on:

```Shell
curl http://127.0.0.1:8010/?cmd=CONF:LED1:text=FOO
curl http://127.0.0.1:8010/?cmd=LED1:ON
```  

##### API Commands

| UDP Command         | Function |
----------------------|----------|
| `LED1:[ON/OFF]`     | switch LED1 on/off |
| `LED2:[ON/OFF]`     | switch LED2 on/off |
| `LED3:[ON/OFF]`     | switch LED3 on/off |
| `LED4:[ON/OFF]`     | switch LED4 on/off |
| `NOW:TEXT`               | set TEXT in first footer line |
| `NEXT:TEXT`              | set TEXT in second footer line |
| `WARN:TEXT`              | set TEXT and switch on red warning mode |
| `AIR1:[ON/OFF]`          | start/stop Mic Timer |
| `AIR2:[ON/OFF]`          | start/stop Phone Timer |
| `AIR3:[ON/OFF/RESET/TOGGLE]` | start/stop/reset/toggle Radio Timer |
| `AIR3TIME:seconds`            | set Radio Timer to given value in seconds |
| `AIR4:[ON/OFF/RESET]`        | start/stop/reset Stream Timer |
| `CMD:REBOOT`                  | OS restart |
| `CMD:SHUTDOWN`                | OS shutdown |
| `CMD:QUIT`                    | quit OnAirScreen instance |

##### Remote Configuration Commands
`CONF:General:stationname=TEXT`<br>
`CONF:General:slogan=TEXT`<br>
`CONF:General:stationcolor=COLOR`<br>
`CONF:General:slogancolor=COLOR`<br>
`CONF:LED[1-4]:used=[False|True]`<br>
`CONF:LED[1-4]:text=TEXT`<br>
`CONF:LED[1-4]:activebgcolor=COLOR`<br>
`CONF:LED[1-4]:activetextcolor=COLOR`<br>
`CONF:LED[1-4]:autoflash=[False|True]`<br>
`CONF:LED[1-4]:timedflash=[False|True]`<br>
`CONF:Clock:digital=[True|False]`<br>
`CONF:Clock:showseconds=[True|False]`<br>
`CONF:Clock:digitalhourcolor=COLOR`<br>
`CONF:Clock:digitalsecondcolor=COLOR`<br>
`CONF:Clock:digitaldigitcolor=COLOR`<br>
`CONF:Clock:logopath=PathToLogo`<br>
`CONF:Network:udpport=PORT`<br>
`CONF:Network:tcpport=PORT`<br>
`CONF:CONF:APPLY=TRUE`<br>

#### Donation
Do you like OnAirScreen?
Feel free to donate.

<span class="badge-paypal"><a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=YCQKC82DLCHMG" title="Donate to this project using Paypal"><img src="https://img.shields.io/badge/paypal-donate-yellow.svg" alt="PayPal donate button" /></a></span>

<a href="https://www.buymeacoffee.com/saschaludwig" target="_blank"><img src="https://img.buymeacoffee.com/button-api/?text=Thanks%20for%20OnAirScreen&emoji=%E2%98%95&slug=saschaludwig&button_colour=FFDD00&font_colour=000000&font_family=Arial&outline_colour=000000&coffee_colour=ffffff" alt="Buy Me A Coffee" height="45px"></a>

<a href='https://ko-fi.com/L3L8BKHYT' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi1.png?v=3' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>
