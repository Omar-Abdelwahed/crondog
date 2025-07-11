#!/usr/bin/env python3
import threading
import os
import signal
import logging
from subprocess import Popen
from time import time, sleep


"""
Crondog logger application
Handles start/stop signals and writes logs to a directory
"""




class CronDog:
    def __init__(self):
        self.setup_logging()
        self.setup_sig_h()
        self.sig_handler()
        self.running = False
        self.logger = None
        self.start()
        self.stop()
        

    def setup_logging(self):
        os.makedirs(os.path.expanduser("~/.cronlog"), exist_ok=True) # Ensure the directory exists
        log_file_path = os.path.expanduser("~/.cronlog/cron.log") 


    def running(self) -> bool:
        #logic of checking if pid file exists and pgrep
        #unsure of it necessity so far.

        ...

    def setup_sig_h(self):
        signal.signal()
        ...

    def sig_handler(self):
    #If sigkill bla bla
    # if sigterm ...
        ...
    
    def logger(self):
        ...
    
    def start(self):
        pid_file = "/home/omar/.cronlog/crondog.pid"
        log_file = "/home/omar/.cronlog/cronlog.log"
    
        if os.path.exists(pid_file):
            print("Process exists and is already running.")
            return

        print("Crondog starting...")
        
        n = os.popen("crontab -l | wc -l").read().strip()
        print(f"Detected processes: {n}")

        process = Popen( #asynchronously opening process.py
            ["python3", "~/crondog/src/process.py"],
            stdout=open(log_file, 'wb'),
            stderr=open(log_file, 'wb'),
            preexec_fn=os.setpgrp  # affects pid to pgid therefore detaches the process
        )
        
        with open(pid_file, "w") as f:
            f.write(str(process.pid))
        
        time.sleep(3)
        print("...started.")

    def stop(self):
        pid_file = "/home/omar/.cronlog/crondog.pid"
    
        if not os.path.exists(pid_file):
            print("No PID file found, nothing to stop.")
            return
        
        with open(pid_file) as f:
            pid = int(f.read().strip())
        
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to process {pid}.")
        except ProcessLookupError:
            print("Process not found.")
        
        os.remove(pid_file)


    def main():
        ...