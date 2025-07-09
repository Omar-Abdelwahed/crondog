#!/usr/bin/env bash

PID_FILE="/home/omar/cronDog//scripts/log_time.pid" #can use a similar road as subprocess.check_output(["pgrep", "-fl", self.name]) to get the PID incase
LOG_FILE="/home/omar/cronDog/scripts/cron_test.log" 

if [[ "$1" == "start" && "$2" == "--name" && ! -f "$PID_FILE" ]]; then
    nohup python3 -u /home/omar/cronDog/scripts/log_time.py --name "$3" >> "$LOG_FILE" 2>&1 & #UNDERSTAND DIS PART
    echo $! > "$PID_FILE" #holds the PID of last background command
elif [[ "$1" == "stop" && "$2" == "--name" ]]; then
      kill "$(cat "$PID_FILE")"
      rm "$PID_FILE"
      rm "$LOG_FILE"
fi