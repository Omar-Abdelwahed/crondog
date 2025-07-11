#!/usr/bin/env python3
import os
import sys
import signal
import time
import logging

def daemonize(pid_file=None, *, stdout='/dev/null', stderr=None, stdin='/dev/null'):
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"First fork failed: {e}\n")
        sys.exit(1)

    os.chdir('/')
    os.setsid()
    os.umask(0)
