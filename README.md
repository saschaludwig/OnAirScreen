# OnAirScreen
Multi purpose "OnAir Lamp" solution targeted for use in professional broadcast environments

--
Screenshot:

<img src="https://www.astrastudio.de/wiki/lib/exe/fetch.php?media=%20:oas.png" width="500px">

### OnAirScreen Function Keys
| Hotkeys                         | Function                |
|---------------------------------|-------------------------|
| Ctrl+F or F                     | Toggle fullscreen       |
| Ctrl+Q or Q or Ctrl+C or ESC    | Quit OnAirScreen        |
| Ctrl+S or Ctrl+,                | Open settings dialog    |
| Space or 0                      | Timer start/stop        |
| . or , or R                     | Timer reset to 0:00     |
| 1                               | LED1 on/off             |
| 2                               | LED2 on/off             |
| 3                               | LED3 on/off             |
| 4                               | LED4 on/off             |
| M or /                          | Mic Timer start/stop    |
| P or *                          | Phone Timer start/stop  |
| Enter                           | opens set timer dialog  |

### OnAirScreen API / UDP Commands
OnAirScreen can receive API commands via UDP port 3310<br>
Here is an easy example on how to control a local OnAirScreen instance on a linux system.

Set LED1 Text to "FOO" and switch LED1 on:
```
echo "CONF:LED1:text=FOO" > /dev/udp/127.0.0.1/3310
echo "LED1:ON" > /dev/udp/127.0.0.1/3310
```

#### API Commands
| UDP Command         | Function |
----------------------|----------|
| `LED1:[ON|OFF]`     | switch LED1 on/off |
| `LED2:[ON|OFF]`     | switch LED2 on/off |
| `LED3:[ON|OFF]`     | switch LED3 on/off |
| `LED4:[ON|OFF]`     | switch LED4 on/off |
| `NOW:TEXT`          | set TEXT in first footer line |
| `NEXT:TEXT`         | set TEXT in second footer line |
| `WARN:TEXT`         | set TEXT and switch on red warning mode |
| `AIR1:[ON|OFF]`     | start/stop Mic Timer |
| `AIR2:[ON|OFF]`     | start/stop Phone Timer |
| `AIR3:[ON|OFF|RESET|TOGGLE]` | start/stop/reset/toggelt Radio Timer |
| `AIR3TIME:seconds`           | set Radio Timer to given value in seconds |
| `AIR4:[ON|OFF|RESET]`        | start/stop/reset Stream Timer |
| `CMD:REBOOT`                 | OS restart |
| `CMD:SHUTDOWN`               | OS shutdown |
| `CMD:QUIT`                   | quit OnAirScreen instance |

#### Remote Configuration Commands
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
`CONF:Clock:digitalhourcolor=COLOR`<br>
`CONF:Clock:digitalsecondcolor=COLOR`<br>
`CONF:Clock:digitaldigitcolor=COLOR`<br>
`CONF:Clock:logopath=PathToLogo`<br>
`CONF:Network:udpport=PORT`<br>
`CONF:Network:tcpport=PORT`<br>
`CONF:CONF:APPLY=TRUE`<br>

### Donation
Do you like OnAirScreen?
Feel free to donate.

<span class="badge-flattr"><a href="https://flattr.com/profile/saschaludwig" title="Donate to this project using Flattr"><img src="https://img.shields.io/badge/flattr-donate-yellow.svg" alt="Flattr donate button" /></a></span>
<span class="badge-paypal"><a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=YCQKC82DLCHMG" title="Donate to this project using Paypal"><img src="https://img.shields.io/badge/paypal-donate-yellow.svg" alt="PayPal donate button" /></a></span>


more infos: https://www.astrastudio.de/wiki/onairscreen
