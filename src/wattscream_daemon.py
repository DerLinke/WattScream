#!/usr/bin/env python3
"""
wattScream – Power Monitor Daemon
Author: Dan & Gemini CLI
Version: 0.1.0
License: MIT
"""
import os
import sys
import time
import json
import subprocess
from datetime import datetime

# Define Glitch Header constants
SCRIPTNAME = "wattScream Daemon"
VERSION = "0.1.0"

class RaplReader:
    """Reads CPU Package Power via Intel/AMD RAPL (requires root)."""
    def __init__(self):
        self.packages = []
        base_dir = "/sys/class/powercap/intel-rapl"
        if os.path.exists(base_dir):
            for entry in os.listdir(base_dir):
                if entry.startswith("intel-rapl:"):
                    name_path = os.path.join(base_dir, entry, "name")
                    energy_path = os.path.join(base_dir, entry, "energy_uj")
                    if os.path.exists(name_path) and os.path.exists(energy_path):
                        try:
                            with open(name_path, "r") as f:
                                name = f.read().strip()
                            # package-0 or similar
                            if "package" in name.lower() or "core" in name.lower():
                                self.packages.append({
                                    "path": energy_path,
                                    "last_val": None,
                                    "last_time": None
                                })
                        except Exception:
                            pass

    def read_power_w(self):
        total_w = 0.0
        now = time.time()
        for pkg in self.packages:
            try:
                with open(pkg["path"], "r") as f:
                    val = int(f.read().strip())
                if pkg["last_val"] is not None and pkg["last_time"] is not None:
                    dt = now - pkg["last_time"]
                    if dt > 0:
                        d_uj = val - pkg["last_val"]
                        if d_uj >= 0:
                            w = (d_uj / dt) / 1000000.0
                            if w < 1000.0:  # Avoid spikes/overflow anomalies
                                total_w += w
                pkg["last_val"] = val
                pkg["last_time"] = now
            except Exception:
                pass
        return total_w

class HwmonPowerReader:
    """Reads GPU/System Power via sysfs hwmon files."""
    def __init__(self):
        self.files = []
        hwmon_dir = "/sys/class/hwmon"
        if os.path.exists(hwmon_dir):
            for entry in os.listdir(hwmon_dir):
                path = os.path.join(hwmon_dir, entry)
                name_path = os.path.join(path, "name")
                if not os.path.exists(name_path):
                    continue
                try:
                    with open(name_path, "r") as f:
                        name = f.read().strip()
                    
                    # Group files by prefix to avoid double-counting average/input
                    sensors = {}
                    for filename in os.listdir(path):
                        if filename.startswith("power") and ("_input" in filename or "_average" in filename):
                            parts = filename.split("_")
                            if len(parts) == 2:
                                prefix, suffix = parts[0], parts[1]
                                if prefix not in sensors:
                                    sensors[prefix] = {}
                                sensors[prefix][suffix] = os.path.join(path, filename)
                                
                    # Select average over input if both exist
                    for prefix, suffixes in sensors.items():
                        chosen_path = suffixes.get("average", suffixes.get("input"))
                        if chosen_path:
                            self.files.append({
                                "name": f"{name}_{prefix}",
                                "path": chosen_path
                            })
                except Exception:
                    pass

    def read_power_w(self):
        total_w = 0.0
        for f_info in self.files:
            try:
                with open(f_info["path"], "r") as f:
                    val = int(f.read().strip())
                # sysfs reports microwatts
                total_w += val / 1000000.0
            except Exception:
                pass
        return total_w

class BatteryPowerReader:
    """Reads system discharge rate from ACPI Battery."""
    def __init__(self):
        self.paths = []
        base = "/sys/class/power_supply"
        if os.path.exists(base):
            for entry in os.listdir(base):
                path = os.path.join(base, entry)
                type_path = os.path.join(path, "type")
                if os.path.exists(type_path):
                    try:
                        with open(type_path, "r") as f:
                            t = f.read().strip()
                        if t.lower() == "battery":
                            self.paths.append(path)
                    except Exception:
                        pass

    def read_power_w(self):
        total_w = 0.0
        for path in self.paths:
            try:
                status_path = os.path.join(path, "status")
                # Only count discharge rate
                if os.path.exists(status_path):
                    with open(status_path, "r") as f:
                        status = f.read().strip().lower()
                    if status != "discharging":
                        continue
                
                power_now_path = os.path.join(path, "power_now")
                if os.path.exists(power_now_path):
                    with open(power_now_path, "r") as f:
                        w = int(f.read().strip()) / 1000000.0
                        total_w += w
                else:
                    current_path = os.path.join(path, "current_now")
                    voltage_path = os.path.join(path, "voltage_now")
                    if os.path.exists(current_path) and os.path.exists(voltage_path):
                        with open(current_path, "r") as f:
                            c = int(f.read().strip())
                        with open(voltage_path, "r") as f:
                            v = int(f.read().strip())
                        total_w += (c * v) / 1000000000000.0
            except Exception:
                pass
        return total_w

class CommandPowerReader:
    """Runs a shell command to fetch wattage (e.g. querying a Shelly plug)."""
    def __init__(self, cmd):
        self.cmd = cmd

    def read_power_w(self):
        if not self.cmd:
            return 0.0
        try:
            res = subprocess.run(self.cmd, shell=True, capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                return float(res.stdout.strip())
        except Exception:
            pass
        return 0.0

class FilePowerReader:
    """Reads wattage from a specified file."""
    def __init__(self, path):
        self.path = path

    def read_power_w(self):
        if not self.path or not os.path.exists(self.path):
            return 0.0
        try:
            with open(self.path, "r") as f:
                return float(f.read().strip())
        except Exception:
            pass
        return 0.0

def get_system_boot_time():
    """Gets system boot time as a Unix timestamp."""
    try:
        with open("/proc/stat", "r") as f:
            for line in f:
                if line.startswith("btime "):
                    return int(line.split()[1])
    except Exception:
        pass
    return 0

def load_config(is_root):
    config_file = "/etc/wattscream/config.json" if is_root else os.path.expanduser("~/.config/wattscream/config.json")
    default_config = {
        "source": "auto",  # auto, battery, sensors, command, file
        "command": "",     # e.g. "curl -s http://192.168.0.50/status | jq .power"
        "file_path": "",
        "poll_interval_sec": 2
    }
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                for k, v in default_config.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            pass
    return default_config

def main():
    is_root = (os.getuid() == 0)
    config = load_config(is_root)
    
    # State paths
    if is_root:
        state_dir = "/var/lib/wattscream"
        telemetry_file = "/run/wattscream.json"
    else:
        state_dir = os.path.expanduser("~/.cache/wattscream")
        telemetry_file = f"/run/user/{os.getuid()}/wattscream.json"
        
    state_file = os.path.join(state_dir, "state.json")
    
    # Ensure state dir exists
    os.makedirs(state_dir, exist_ok=True)
    
    # Load past state
    state = {
        "today_wh": 0.0,
        "boot_wh": 0.0,
        "day": datetime.now().strftime("%Y-%m-%d"),
        "boot_time": get_system_boot_time()
    }
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                saved = json.load(f)
                for k in ["today_wh", "boot_wh", "day", "boot_time"]:
                    if k in saved:
                        state[k] = saved[k]
        except Exception:
            pass
            
    # Check if system has rebooted or day has changed
    current_boot_time = get_system_boot_time()
    if abs(state["boot_time"] - current_boot_time) > 10:
        state["boot_wh"] = 0.0
        state["boot_time"] = current_boot_time
        
    current_day = datetime.now().strftime("%Y-%m-%d")
    if state["day"] != current_day:
        state["today_wh"] = 0.0
        state["day"] = current_day

    # Initialize readers
    rapl = RaplReader()
    hwmon = HwmonPowerReader()
    battery = BatteryPowerReader()
    cmd_reader = CommandPowerReader(config.get("command"))
    file_reader = FilePowerReader(config.get("file_path"))
    
    poll_interval = config.get("poll_interval_sec", 2)
    last_loop_time = time.time()
    
    while True:
        now = time.time()
        
        # 1. Day change detection
        loop_day = datetime.now().strftime("%Y-%m-%d")
        if state["day"] != loop_day:
            state["today_wh"] = 0.0
            state["day"] = loop_day
            
        # 2. Reboot detection
        loop_boot_time = get_system_boot_time()
        if abs(state["boot_time"] - loop_boot_time) > 10:
            state["boot_wh"] = 0.0
            state["boot_time"] = loop_boot_time

        # 3. Read power (W)
        source = config.get("source", "auto")
        current_w = 0.0
        
        if source == "command":
            current_w = cmd_reader.read_power_w()
        elif source == "file":
            current_w = file_reader.read_power_w()
        elif source == "battery":
            current_w = battery.read_power_w()
        elif source == "sensors":
            current_w = rapl.read_power_w() + hwmon.read_power_w()
        else: # auto
            # Try battery first
            bat_w = battery.read_power_w()
            if bat_w > 0.1:
                current_w = bat_w
            else:
                # Try RAPL + HWMON
                current_w = rapl.read_power_w() + hwmon.read_power_w()
                
        # 4. Update energy integrals (Wh)
        dt = now - last_loop_time
        # Prevent huge calculations on resume from suspend (max 2 * interval)
        if 0 < dt < (poll_interval * 2.5):
            dt_hours = dt / 3600.0
            energy_tick = current_w * dt_hours
            state["today_wh"] += energy_tick
            state["boot_wh"] += energy_tick
            
        last_loop_time = now
        
        # Save state to persistent JSON
        try:
            with open(state_file, "w") as f:
                json.dump(state, f)
        except Exception:
            pass
            
        # Export telemetry to /run
        telemetry = {
            "current_w": current_w,
            "today_wh": state["today_wh"],
            "boot_wh": state["boot_wh"],
            "last_updated": now
        }
        
        try:
            with open(telemetry_file, "w") as f:
                json.dump(telemetry, f)
            # Make readable by everyone
            os.chmod(telemetry_file, 0o644)
        except Exception:
            pass
            
        time.sleep(poll_interval)

if __name__ == "__main__":
    main()
