#!/bin/bash

curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Clock:showseconds=True"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:CONF:APPLY=TRUE"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Clock:showseconds=False"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:CONF:APPLY=TRUE"
sleep 1

curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=NOW:The Testers - Test around the clock"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=NEXT:coming up next: the foo the bar and the generic"
sleep 1

curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=WARN:The system is testing..."
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=WARN:"
sleep 1

curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=LED1:ON"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=LED1:OFF"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=LED2:ON"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=LED2:OFF"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=LED3:ON"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=LED3:OFF"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=LED4:ON"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=LED4:OFF"
sleep 1

# Test AIR Timer Commands
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR1:ON"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR1:OFF"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR2:ON"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR2:OFF"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR3:ON"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR3:OFF"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR3:RESET"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR3:TOGGLE"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR3TIME:120"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR4:ON"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR4:OFF"
sleep 1
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=AIR4:RESET"
sleep 1

# Test General Configuration
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:General:stationname=Test Radio Station"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:General:slogan=Your Music, Your Way"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:General:stationcolor=#FF0000"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:General:slogancolor=#00FF00"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:CONF:APPLY=TRUE"
sleep 1

# Test LED Configuration
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:LED1:text=ON AIR"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:LED2:text=ATTENTION"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:LED3:text=DOORBELL"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:LED4:text=PHONE"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:LED1:used=True"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:LED1:activebgcolor=#FF0000"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:LED1:activetextcolor=#FFFFFF"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:LED1:autoflash=True"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:LED1:timedflash=False"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:CONF:APPLY=TRUE"
sleep 1

# Test Clock Configuration
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Clock:digital=True"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Clock:digitalhourcolor=#FFFFFF"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Clock:digitalsecondcolor=#FFFF00"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Clock:digitaldigitcolor=#00FFFF"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:CONF:APPLY=TRUE"
sleep 1

# Test Timer Configuration
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Timers:TimerAIR1Enabled=True"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Timers:TimerAIR1Text=Mic"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Timers:TimerAIR2Text=Phone"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Timers:TimerAIR3Text=Radio"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Timers:TimerAIR4Text=Stream"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:CONF:APPLY=TRUE"
sleep 1

# Test Network Configuration
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:Network:udpport=3310"
curl "http://127.0.0.1:8010/" --get --data-urlencode "cmd=CONF:CONF:APPLY=TRUE"
sleep 1

exit
