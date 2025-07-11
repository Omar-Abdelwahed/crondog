from datetime import timedelta, datetime
from typing import List, Protocol
from time import sleep

#Logging
import os
import logging

#Other classes
from cronjob import CronJob, CJ_next_run #To change

#Requirements
from dataclasses import dataclass
import subprocess



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

class ProcState(Protocol):
    def switch(self) -> None:  
        ...

class ProcContext(Protocol):
    cronjobs: List[CronJob]

    def set_state(self, state: ProcState) -> None:
        ...
    def switch(self) -> None:  
        ...


@dataclass
class Running:
    process: "Process"

    def switch(self):
        should_run = self.process.should_run()
        is_running = self.process.is_cron_running()
        is_starting = self.process.is_starting()
        
        if is_running and should_run:
            logging.info("Running: Process is running as expected.")
        elif not is_running and should_run and is_starting:
            logging.debug("Running -> Starting")
            self.process.set_state(Starting(self.process))
        elif not is_running and should_run:
            logging.warning("Running -> Down")
            self.process.set_state(Down(self.process))
        elif not is_running and not should_run:
            logging.debug("Running -> Stopped")
            self.process.set_state(Stopped(self.process))
        elif is_running and not should_run:
            logging.warning("Running -> Undefined")
            self.process.set_state(Undefined(self.process))
        else:
            logging.warning("Running: Unhandled condition.")


@dataclass
class Stopped:
    process: "Process"

    def switch(self):
        logging.debug(f"Stopped state: is_running={is_running}, should_run={should_run}, is_starting={is_starting}")
        should_run = self.process.should_run()
        is_running = self.process.is_cron_running()
        is_starting = self.process.is_starting()

        if not is_running and not should_run and not is_starting:
            logging.debug("Stopped: Process has already stopped.")
        elif not is_running and should_run and is_starting:
            logging.debug("Stopped -> Starting")
            self.process.set_state(Starting(self.process))
        elif not is_running and should_run:
            logging.warning("Stopped -> Down")
            self.process.set_state(Down(self.process))
        elif is_running and should_run:
            logging.debug("Stopped -> Running")
            self.process.set_state(Running(self.process))
        elif is_running and not should_run:
            logging.warning("Stopped -> Undefined")
            self.process.set_state(Undefined(self.process))
        else:
            logging.warning("Stopped: Unhandled condition.")


@dataclass
class Down:
    process: "Process"

    def switch(self):
        should_run = self.process.should_run()
        is_running = self.process.is_cron_running()
        is_starting = self.process.is_starting()

        if is_starting and not is_running and should_run:
            logging.debug("Down -> Starting")
            self.process.set_state(Starting(self.process))
        elif is_running and should_run:
            logging.debug("Down -> Running")
            self.process.set_state(Running(self.process))
        elif not is_running and not should_run:
            logging.debug("Down -> Stopped")
            self.process.set_state(Stopped(self.process))
        elif is_running and not should_run:
            logging.warning("Down -> Undefined")
            self.process.set_state(Undefined(self.process))
        else:
            logging.warning("Down: Process is still down.")

@dataclass
class Starting:
    process: "Process"

    def switch(self):
        should_run = self.process.should_run()
        is_running = self.process.is_cron_running()

        if is_running and should_run:
            logging.debug("Starting -> Running")
            self.process.set_state(Running(self.process))
        elif not is_running and not should_run:
            logging.debug("Starting -> Stopped")
            self.process.set_state(Stopped(self.process))
        elif not is_running and should_run:
            logging.debug("Starting: Still starting up.")
        elif is_running and not should_run:
            logging.warning("Starting -> Undefined")
            self.process.set_state(Undefined(self.process))
        else:
            logging.warning("Starting: Unhandled condition.")


@dataclass
class Undefined:
    process: "Process"

    def switch(self):
        should_run = self.process.should_run()
        is_running = self.process.is_cron_running()
        is_starting = self.process.is_starting()
        logging.info(f"[Troubleshoot]: is_running={is_running}, should_run={should_run}, is_starting={is_starting}")

        if is_running and should_run:
            logging.debug("Undefined -> Running")
            self.process.set_state(Running(self.process))
        elif not is_running and not should_run: 
            logging.debug("Undefined -> Stopped")
            self.process.set_state(Stopped(self.process))
        elif not is_running and should_run and is_starting:
            logging.debug("Undefined -> Starting")
            self.process.set_state(Starting(self.process))
        elif not is_running and should_run:
            logging.warning("Undefined -> Down")
            self.process.set_state(Down(self.process))

class Process:
    GRACE_PERIOD = timedelta(minutes=5)

    def __init__(self, cronjobs: List[CronJob], name:str):
        self.cronjobs = cronjobs
        self.state = Undefined(self)
        self.name = name
        self.start_jobs, self.stop_jobs = _split_start_stop(self.cronjobs,name)
        

    def is_cron_running(self) -> bool:
        """
        Checks if a process matching the expected command and name is running.
        """
        search_pattern = f"--name {self.name}"
        try:
            output = subprocess.check_output(
                f"ps aux | grep '{search_pattern}' | grep -v grep",  # -v
                shell=True,
                stderr=subprocess.DEVNULL,
                universal_newlines=True
            )
            
            if output:
                logging.debug(f"Found matching process for {self.name}: {output}")
                return True
            return False
        except subprocess.CalledProcessError:
            logging.debug(f"No process found matching --name {self.name}")
            return False # when using --name Lux whilst running the porcess it still matches with in the ps aux.
        
    def should_run(self) -> bool:
        """
        Checks wether the process is supposed to be running in the meantime (Reference: The crontab)
        """
        now= datetime.now()
        start_time = min(job.next_run_date(now) for job in self.start_jobs)
        stop_time = min(job.next_run_date(now) for job in self.stop_jobs)
        logging.debug(f"[should_run] {self.name}: start_time={start_time}, stop_time={stop_time}")
        return stop_time < start_time
    
    
    def is_starting(self) -> bool: 
            """
            Checks wether a process is within the grace period or not
            """
            now = datetime.now()
            for job in self.start_jobs:
                rewinded_time = now - timedelta(days=7)
                last_valid_run = None
                
                while rewinded_time <= now:
                    run_time = job.next_run_date(rewinded_time)
                    if run_time > now:
                        break  #itd save the last run_time value before reachin limit
                    last_valid_run = run_time
                    rewinded_time = run_time + timedelta(minutes=1) 

                if last_valid_run and last_valid_run < now <= last_valid_run + self.GRACE_PERIOD:
                    return True
                
            logging.debug("No jobs within grace period")
            return False


    def last_run_time(self, now: datetime):
        """checks last rundate within the last seven days:
        Out of scope atm but handy for:
            skipping re-runs, compute uptime or downtime, trigger downstream action, storing logs, etc..
        """
        for job in self.start_jobs:
            period = now - timedelta(days=7)
            last_scheduled_run = job.next_run_date(period)
            
            if (job.name not in self.last_run_log or last_scheduled_run > self.last_run_log[job.name]):
                self.last_run_log[job.name] = last_scheduled_run
        return self.last_run_log
            

    def set_state(self, state: ProcState) -> None:
        logging.debug(f"[STATE] -> {state.__class__.__name__}")
        self.state = state


    def switch(self):
        self.state.switch()

    def monitor(self):
        self.monitor

def _split_start_stop(jobs: List[CronJob], target_name: str):
    start_jobs = []
    stop_jobs = []
    
    for job in jobs:
        name = job._extract_name()
        if not name or name != target_name:
            continue
        if "start" in job.command:
            start_jobs.append(job)
        elif "stop" in job.command:
            stop_jobs.append(job)

    return start_jobs, stop_jobs

if __name__ == "__main__":
    """
    runs with process.py --name Lux or process.py 
    """
    import sys

    target_name = None                                          
    if len(sys.argv) >= 3 and sys.argv[1] == "-n":
        target_name = sys.argv[2]

    cronjobs = CJ_next_run()
    group = {}
    for job in cronjobs:
        if job.name:
            group.setdefault(job.name, []).append(job)  # group["A"] = [job1, job2, ...]

    while True:
        now = datetime.now()
        for name, jobs in group.items():
            if target_name and name != target_name:
                continue  # Skipi

            print(f"\nChecking process: {name}")
            process = Process(jobs, name)
            process.switch()
            print(f"Process state: {process.state.__class__.__name__}")

        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        sleep(5)