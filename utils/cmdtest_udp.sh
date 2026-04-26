#!/bin/bash

echo "========================================="
echo "OnAirScreen UDP Command Test Script"
echo "========================================="
echo ""

echo "[TEST] Clock Configuration - showseconds"
echo  "CONF:Clock:showseconds=True" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:Clock:showseconds=False" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] Clock Configuration - secondsinoneline"
echo  "CONF:Clock:secondsinoneline=True" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:Clock:secondsinoneline=False" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] Clock Configuration - logoupper"
echo  "CONF:Clock:logoupper=True" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:Clock:logoupper=False" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] NOW/NEXT Text Commands"
echo  "NOW:The Testers - Test around the clock" | nc -w 1 -u 127.0.0.1 3310
echo  "NEXT:coming up next: the foo the bar and the generic" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] WARN Command"
echo  "WARN:The system is testing..." | nc -w 1 -u 127.0.0.1 3310
echo  "WARN:" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] LED Commands - Individual LEDs"
echo "LED1:ON" | nc -w 1 -u 127.0.0.1 3310
echo "LED1:OFF" | nc -w 1 -u 127.0.0.1 3310
echo "LED2:ON" | nc -w 1 -u 127.0.0.1 3310
echo "LED2:OFF" | nc -w 1 -u 127.0.0.1 3310
echo "LED3:ON" | nc -w 1 -u 127.0.0.1 3310
echo "LED3:OFF" | nc -w 1 -u 127.0.0.1 3310
echo "LED4:ON" | nc -w 1 -u 127.0.0.1 3310
echo "LED4:OFF" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] LED Commands - Multiple LEDs in one packet"
echo -e "LED1:ON\nLED2:ON\nLED3:ON\nLED4:ON" | nc -w 1 -u 127.0.0.1 3310
echo -e "LED1:OFF\nLED2:OFF\nLED3:OFF\nLED4:OFF" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] AIR Timer Commands"
echo "  -> AIR1:ON/OFF"
echo "AIR1:ON" | nc -w 1 -u 127.0.0.1 3310
echo "AIR1:OFF" | nc -w 1 -u 127.0.0.1 3310
echo "  -> AIR2:ON/OFF"
echo "AIR2:ON" | nc -w 1 -u 127.0.0.1 3310
echo "AIR2:OFF" | nc -w 1 -u 127.0.0.1 3310
echo "  -> AIR3:ON/OFF/RESET/TOGGLE"
echo "AIR3:ON" | nc -w 1 -u 127.0.0.1 3310
echo "AIR3:OFF" | nc -w 1 -u 127.0.0.1 3310
echo "AIR3:RESET" | nc -w 1 -u 127.0.0.1 3310
echo "AIR3:TOGGLE" | nc -w 1 -u 127.0.0.1 3310
echo "  -> AIR3TIME:120"
echo "AIR3TIME:120" | nc -w 1 -u 127.0.0.1 3310
echo "  -> AIR4:ON/OFF/RESET"
echo "AIR4:ON" | nc -w 1 -u 127.0.0.1 3310
echo "AIR4:OFF" | nc -w 1 -u 127.0.0.1 3310
echo "AIR4:RESET" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] General Configuration"
echo "  -> Station Name, Slogan, Colors"
echo "CONF:General:stationname=Test Radio Station" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:General:slogan=Your Music, Your Way" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:General:stationcolor=#FF0000" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:General:slogancolor=#00FF00" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] LED Configuration"
echo "  -> LED Text, Colors, Flash Settings"
echo "CONF:LED1:text=ON AIR" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:LED2:text=ATTENTION" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:LED3:text=DOORBELL" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:LED4:text=PHONE" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:LED1:used=True" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:LED1:activebgcolor=#FF0000" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:LED1:activetextcolor=#FFFFFF" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:LED1:autoflash=True" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:LED1:timedflash=False" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] Clock Configuration"
echo "  -> Digital Mode, Colors"
echo "CONF:Clock:digital=True" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:Clock:digitalhourcolor=#FFFFFF" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:Clock:digitalsecondcolor=#FFFF00" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:Clock:digitaldigitcolor=#00FFFF" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] Timer Configuration"
echo "  -> Timer Enabled, Timer Text"
echo "CONF:Timers:TimerAIR1Enabled=True" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:Timers:TimerAIR1Text=Mic" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:Timers:TimerAIR2Text=Phone" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:Timers:TimerAIR3Text=Radio" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:Timers:TimerAIR4Text=Stream" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] Network Configuration"
echo "  -> UDP Port"
echo "CONF:Network:udpport=3310" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] Multiple Commands in One Packet"
echo "  -> NOW, NEXT, LED1, LED2"
echo -e "NOW:Current Song Title\nNEXT:Next Song Title\nLED1:ON\nLED2:ON" | nc -w 1 -u 127.0.0.1 3310

echo "[TEST] LED Text Configuration - Multi-line Format"
conf="LED1TEXT=ON AIR\n
LED2TEXT=ATTENTION\n
LED3TEXT=DOORBELL\n
LED4TEXT=PHONE\n
"
echo -e "CONF:$conf" | nc -w 1 -u 127.0.0.1 3310
echo "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo ""
echo "[CLEANUP] Resetting test configuration changes to defaults"
echo "  -> Resetting General Configuration (changed in test)"
echo -e "CONF:General:stationname=Radio Eriwan\nCONF:General:slogan=Your question is our motivation\nCONF:General:stationcolor=#FFAA00\nCONF:General:slogancolor=#FFAA00" | nc -w 1 -u 127.0.0.1 3310

echo "  -> Resetting LED Configuration (changed in test)"
echo -e "CONF:LED1:text=ON AIR\nCONF:LED2:text=PHONE\nCONF:LED3:text=DOORBELL\nCONF:LED4:text=EAS ACTIVE\nCONF:LED1:autoflash=False" | nc -w 1 -u 127.0.0.1 3310

echo "  -> Resetting Clock Configuration (changed in test)"
echo -e "CONF:Clock:digitalhourcolor=#3232FF\nCONF:Clock:digitalsecondcolor=#FF9900\nCONF:Clock:digitaldigitcolor=#3232FF" | nc -w 1 -u 127.0.0.1 3310

echo "  -> Resetting Timer Configuration (changed in test)"
echo -e "CONF:Timers:TimerAIR1Text=Mic\nCONF:Timers:TimerAIR2Text=Phone\nCONF:Timers:TimerAIR3Text=Timer\nCONF:Timers:TimerAIR4Text=Stream" | nc -w 1 -u 127.0.0.1 3310

echo "  -> Clearing text fields (changed in test)"
echo -e "NOW:\nNEXT:\nWARN:" | nc -w 1 -u 127.0.0.1 3310

echo "  -> Turning off all LEDs and AIR timers (changed in test)"
echo -e "LED1:OFF\nLED2:OFF\nLED3:OFF\nLED4:OFF\nAIR1:OFF\nAIR2:OFF\nAIR3:OFF\nAIR4:OFF\nAIR3:RESET\nAIR4:RESET" | nc -w 1 -u 127.0.0.1 3310

echo "  -> Applying all configuration changes"
echo "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo ""
echo "========================================="
echo "Test completed! Test configuration changes reset to defaults."
echo "========================================="
exit
