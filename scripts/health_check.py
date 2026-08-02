#!/usr/bin/env python3
import os
import subprocess
import shutil
import psutil
import time
import json
from pathlib import Path
from collections import deque
import getpass


username = getpass.getuser()
REBOOT_COMMAND = "sudo reboot"
SERVICE_RESTARTS = ["gunicorn", "nginx", "redis-server"]
LOG_FILE = f"/home/{username}/Sonet/.data/logs/node_health.log"
COUNTER_FILE = f"/home/{username}/Sonet/.data/logs/node_health_counters.json"

MAX_CPU_PERCENT = 90
MAX_MEM_PERCENT = 90
MAX_SWAP_PERCENT = 90
MAX_DISK_PERCENT = 90
PING_TIMEOUT = 1  # seconds
CHECK_WINDOW = 6  # consecutive failures before reboot - max reboot once per hour (600 * 6)
SLEEP_INTERVAL = 600  # seconds (10 minutes)


def log(msg):
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception as e:
        print('log error',str(e))

def restart_service(service):
    try:
        subprocess.run(["sudo", "systemctl", "restart", service], check=True)
        log(f"Restarted service: {service}")
    except Exception as e:
        log(f"Failed to restart service {service}: {e}")

def reboot_device():
    log("Rebooting device now...")
    os.system(REBOOT_COMMAND)

def ping_localhost():
    try:
        subprocess.run(["ping", "-c", "1", "-W", str(PING_TIMEOUT), "127.0.0.1"], check=True, stdout=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def load_counters():
    if Path(COUNTER_FILE).exists():
        try:
            data = json.loads(Path(COUNTER_FILE).read_text())
            return {k: deque(v, maxlen=CHECK_WINDOW) for k, v in data.items()}
        except Exception:
            pass
    # default empty
    return {
        "cpu": deque(maxlen=CHECK_WINDOW),
        "mem": deque(maxlen=CHECK_WINDOW),
        "swap": deque(maxlen=CHECK_WINDOW),
        "disk": deque(maxlen=CHECK_WINDOW),
        "ping": deque(maxlen=CHECK_WINDOW)
    }

def save_counters(counters):
    data = {k: list(v) for k, v in counters.items()}
    Path(COUNTER_FILE).write_text(json.dumps(data))


def check_cpu(counters):
    usage = psutil.cpu_percent(interval=1)
    fail = usage > MAX_CPU_PERCENT
    counters["cpu"].append(fail)
    return fail

def check_memory(counters):
    mem = psutil.virtual_memory()
    fail = mem.percent > MAX_MEM_PERCENT
    counters["mem"].append(fail)
    return fail

def check_swap(counters):
    swap = psutil.swap_memory()
    fail = swap.percent > MAX_SWAP_PERCENT
    counters["swap"].append(fail)
    return fail

def check_disk(counters):
    disk = psutil.disk_usage("/")
    fail = disk.percent > MAX_DISK_PERCENT
    counters["disk"].append(fail)
    return fail

def check_services():
    failed_services = []
    for svc in SERVICE_RESTARTS:
        if shutil.which(svc) is None:
            continue
        result = subprocess.run(["systemctl", "is-active", "--quiet", svc])
        if result.returncode != 0:
            restart_service(svc)
            failed_services.append(svc)
    return failed_services

def check_ping(counters):
    fail = not ping_localhost()
    counters["ping"].append(fail)
    return fail

def failures_over_window(counters):
    return any(sum(v) >= CHECK_WINDOW for v in counters.values())


def main():
    counters = load_counters()

    while True:
        try:
            log("Running health check...")
            cpu_fail = check_cpu(counters)
            mem_fail = check_memory(counters)
            swap_fail = check_swap(counters)
            disk_fail = check_disk(counters)
            ping_fail = check_ping(counters)
            svc_failures = check_services()

            if failures_over_window(counters):
                log("Persistent failures detected, rebooting device...")
                save_counters(counters)
                reboot_device()
            elif any([cpu_fail, mem_fail, swap_fail, disk_fail, ping_fail]):
                log("Minor failures detected, services restarted if needed.")
                save_counters(counters)
            else:
                log("All systems healthy.")
                save_counters(counters)
        except Exception as e:
            print('main error',str(e))

        time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    main()