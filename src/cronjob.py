from subprocess import check_output
from typing import List, Tuple
from datetime import timedelta, datetime
import re

class CronJob:
    def __init__(self, line: str):
        self.expression, self.command = CronJob._line_parse(line)
        self.name = self._extract_name() 

    @staticmethod
    def _line_parse(line: str) -> tuple[str, str]:
        buf = line.split(" ", 5)
        command = buf.pop()
        expr = " ".join(buf)
        return (expr, command)

    def is_start_job(self):
        ...
    
    def __repr__(self):
        return f"[CronJob expression='{self.expression}' command='{self.command}']"
    
    def _extract_name(self) -> str | None:
        """
        @Extracts:
        '--name VALUE' from the command part.
        """
        match = re.search(r'--name\s+(\w+)', self.command) #r makes it a raw string
        return match.group(1) if match else None
    
    def _field_parse(self, field: str, min_value: int, max_value: int) -> List[int]:
        """
        Parses a single cron field like '*', '*/5', '1,2,3', '1-5', etc.
        Returns a sorted list of valid values in range [min_value, max_value].
        """
        values = set()
        for part in field.split(','):
            part = part.strip()

            if part == "*":
                values.update(range(min_value, max_value + 1))
            elif '/' in part:
                base, step = part.split('/')
                step = int(step)
                if base == '*':
                    values.update(range(min_value, max_value + 1, step))
                elif '-' in base:
                    start, end = map(int, base.split('-'))
                    values.update(range(start, end + 1, step))
                else:
                    values.add(int(base))
            elif '-' in part:
                start, end = map(int, part.split('-'))
                values.update(range(start, end + 1))
            else:
                values.add(int(part))

        return sorted(v for v in values if min_value <= v <= max_value)
    
    def next_run_date(self, now=None) -> datetime:
        """
        Computes the next datetime that matches this cron expression.
        """
        if now is None:
            now = datetime.now().replace(second=0, microsecond=0)
        search_time = now + timedelta(minutes=1)

        parts = self.expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: '{self.expression}'")

        minute_list = self._field_parse(parts[0], 0, 59)
        hour_list = self._field_parse(parts[1], 0, 23)
        day_list = self._field_parse(parts[2], 1, 31)
        month_list = self._field_parse(parts[3], 1, 12)
        dow_list = self._field_parse(parts[4], 0, 6)

        # 1y limit
        for _ in range(0, 525600):  # 60 minutes * 24 hours * 365 days 
            if (search_time.minute in minute_list and
                search_time.hour in hour_list and
                search_time.day in day_list and
                search_time.month in month_list and
                search_time.isoweekday() in dow_list): 
                return search_time
            search_time += timedelta(minutes=1)

        raise Exception("Couldn't find next run time within 1 year.")
    


def CJ_next_run()-> List[CronJob]:
    crontab = check_output(["crontab","-l"], universal_newlines=True)
    lines = crontab.strip().split("\n")
    jobs= []
    for line in lines:
        if not line.startswith("#") and line.strip():
            jobs.append(CronJob(line))
    for job in jobs:
        print(job, "Next run at:", job.next_run_date())
    return jobs






if __name__ == "__main__":
    CJ_next_run()