#!/bin/bash

echo  "CONF:Clock:showseconds=True" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:Clock:showseconds=False" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:Clock:secondsinoneline=True" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:Clock:secondsinoneline=False" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo  "CONF:Clock:logoupper=True" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:Clock:logoupper=False" | nc -w 1 -u 127.0.0.1 3310
echo  "CONF:CONF:APPLY=TRUE" | nc -w 1 -u 127.0.0.1 3310

echo  "NOW:The Testers - Test around the clock" | nc -w 1 -u 127.0.0.1 3310
echo  "NEXT:coming up next: the foo the bar and the generic" | nc -w 1 -u 127.0.0.1 3310

echo  "WARN:The system is testing..." | nc -w 1 -u 127.0.0.1 3310
echo  "WARN:" | nc -w 1 -u 127.0.0.1 3310

echo "LED1:ON" | nc -w 1 -u 127.0.0.1 3310
echo "LED1:OFF" | nc -w 1 -u 127.0.0.1 3310
echo "LED2:ON" | nc -w 1 -u 127.0.0.1 3310
echo "LED2:OFF" | nc -w 1 -u 127.0.0.1 3310
echo "LED3:ON" | nc -w 1 -u 127.0.0.1 3310
echo "LED3:OFF" | nc -w 1 -u 127.0.0.1 3310
echo "LED4:ON" | nc -w 1 -u 127.0.0.1 3310
echo "LED4:OFF" | nc -w 1 -u 127.0.0.1 3310


echo -e "LED1:ON\nLED2:ON\nLED3:ON\nLED4:ON" | nc -w 1 -u 127.0.0.1 3310
echo -e "LED1:OFF\nLED2:OFF\nLED3:OFF\nLED4:OFF" | nc -w 1 -u 127.0.0.1 3310



exit


conf="LED1TEXT=ON AIR\n
LED2TEXT=ATTENTION\n
LED3TEXT=DOORBELL\n
LED4TEXT=PHONE\n
"
echo -e "CONF:$conf" | nc -w 1 -u 127.0.0.1 3310
