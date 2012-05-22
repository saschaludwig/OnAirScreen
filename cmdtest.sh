#!/bin/bash

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

