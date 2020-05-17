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


exit
echo -e "LED1:ON\nLED2:ON\nLED3:ON\nLED4:ON"
conf="LED1TEXT=ON AIR\n
LED2TEXT=ATTENTION\n
LED3TEXT=DOORBELL\n
LED4TEXT=PHONE\n
"
echo -e "CONF:$conf"
