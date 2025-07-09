#!/usr/bin/env python3
import time
from datetime import datetime


while True:
    with open("/home/omar/cronDog/scripts/cron_test.log", "a") as f: 
        f.write(f"{datetime.now().isoformat()}\n")
    time.sleep(15)