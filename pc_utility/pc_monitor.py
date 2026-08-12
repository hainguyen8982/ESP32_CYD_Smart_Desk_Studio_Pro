import sys
import time
import json
import subprocess
import os
import psutil
import serial
import serial.tools.list_ports
import urllib.request
import urllib.parse
import socket

import ctypes

BAUD_RATE = 115200

# Windows Virtual Key Definitions for Media Controls
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP       = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE      = 0xAD
VK_VOLUME_DOWN      = 0xAE
VK_VOLUME_UP        = 0xAF

def background_skip_youtube_ad():
    """Background YouTube Ad Skipper — Browser Targeting Ad Clicker!"""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        
        # 1. Find Chrome / Edge / Firefox / YouTube window
        browser_hwnd = None
        def _enum_cb(hwnd, extra):
            nonlocal browser_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if any(b in title for b in ["youtube", "chrome", "edge", "firefox", "brave", "opera"]):
                        browser_hwnd = hwnd
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)

        if browser_hwnd:
            user32.SetForegroundWindow(browser_hwnd)
            time.sleep(0.05)

        # 2. Perform Targeted Click at YouTube Skip Ad Button Location (84% X, 76% Y)
        if browser_hwnd:
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                            ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
            rect = RECT()
            user32.GetWindowRect(browser_hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            click_x = rect.left + int(w * 0.84)
            click_y = rect.top + int(h * 0.76)
            user32.SetCursorPos(click_x, click_y)
            time.sleep(0.02)
            user32.mouse_event(0x0002, 0, 0, 0, 0) # Left Down
            user32.mouse_event(0x0004, 0, 0, 0, 0) # Left Up
        else:
            user32.keybd_event(0x09, 0, 0, 0); user32.keybd_event(0x09, 0, 2, 0)
            time.sleep(0.02)
            user32.keybd_event(0x0D, 0, 0, 0); user32.keybd_event(0x0D, 0, 2, 0)
            
        print("[Media Remote]: Executed YouTube Skip Ad Targeted Click!")
    except Exception as e:
        print(f"[Skip Ad Error]: {e}")

last_media_time = 0.0

def handle_media_action(action):
    global last_media_time
    if not action:
        return
    now = time.time()
    if now - last_media_time < 0.45:
        return
    
    act = str(action).lower().strip()
    vk = None
    if act in ["play_pause", "play", "pause"]:
        vk = VK_MEDIA_PLAY_PAUSE
    elif act in ["next", "next_track"]:
        vk = VK_MEDIA_NEXT_TRACK
    elif act in ["prev", "previous", "prev_track"]:
        vk = VK_MEDIA_PREV_TRACK
    elif act in ["vol_up", "volume_up"]:
        vk = VK_VOLUME_UP
    elif act in ["vol_down", "volume_down"]:
        vk = VK_VOLUME_DOWN
    elif act in ["mute"]:
        vk = VK_VOLUME_MUTE
    elif act in ["skip_ad", "skipad", "skip"]:
        last_media_time = now
        background_skip_youtube_ad()
        return

    if vk is not None and sys.platform == "win32":
        try:
            last_media_time = now
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
            print(f"[Media Hotkey] Windows VK Key 0x{vk:02X} triggered for action '{act}'")
        except Exception as e:
            print(f"[Media Hotkey Error] {e}")

# Common USB Serial Chip VID/PID for ESP32 boards
ESP32_VID_PIDS = [
    (0x10C4, 0xEA60),  # CP2102
    (0x1A86, 0x7523),  # CH340
    (0x1A86, 0x55D4)   # CH9102
]

def check_port_handshake(port):
    """Test connection and send PING to COM port, waiting for PONG."""
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=0.3)
        ser.dtr = False
        ser.rts = False
        time.sleep(0.2)
        ser.reset_input_buffer()

        start_time = time.time()
        last_ping = 0
        
        while time.time() - start_time < 8.0:
            now = time.time()
            if now - last_ping >= 0.5:
                ser.write(b"PING_DASHBOARD\n")
                last_ping = now
                
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if "PONG_DASHBOARD" in line:
                    print(f"--> [USB Serial]: Handshake success! Connected to ESP32 CYD on {port}")
                    return ser
            time.sleep(0.05)
            
        ser.close()
    except Exception as e:
        print(f"Port {port} check notice: {e}")
    return None

def find_esp32_serial():
    """Scan physical COM ports for ESP32 CYD."""
    ports = list(serial.tools.list_ports.comports())
    target_ports = []
    for p in ports:
        if p.vid is not None and p.pid is not None:
            for vid, pid in ESP32_VID_PIDS:
                if p.vid == vid and p.pid == pid:
                    target_ports.append(p.device)
                    break
                    
    for port in target_ports:
        print(f"Checking target ESP32 on port {port}...")
        ser = check_port_handshake(port)
        if ser:
            return ser
            
    for p in ports:
        port = p.device
        if port not in target_ports:
            print(f"Checking COM port {port}...")
            ser = check_port_handshake(port)
            if ser:
                return ser
    return None

def get_cpu_temp():
    """Estimate or read CPU Temperature in °C."""
    try:
        import wmi
        w = wmi.WMI(namespace="root\\wmi")
        temperature_info = w.MSAcpi_ThermalZoneTemperature()
        if temperature_info:
            return (temperature_info[0].CurrentTemperature / 10.0) - 273.15
    except Exception:
        pass
    cpu_load = psutil.cpu_percent()
    return 40.0 + (cpu_load * 0.35)

HAS_NVIDIA_SMI = None

def get_gpu_stats():
    """Get GPU Utilization and Temperature."""
    global HAS_NVIDIA_SMI
    gpu_stats = {"load": 0.0, "temp": 0.0, "vram_used": 0.0, "vram_total": 0.0}
    
    if HAS_NVIDIA_SMI is None:
        import shutil
        HAS_NVIDIA_SMI = shutil.which("nvidia-smi") is not None

    if HAS_NVIDIA_SMI:
        try:
            cmd = ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"]
            output = subprocess.check_output(cmd, creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8').strip()
            parts = [x.strip() for x in output.split(',')]
            if len(parts) >= 4:
                gpu_stats["load"] = float(parts[0])
                gpu_stats["temp"] = float(parts[1])
                gpu_stats["vram_used"] = float(parts[2]) / 1024.0
                gpu_stats["vram_total"] = float(parts[3]) / 1024.0
                return gpu_stats
        except Exception:
            HAS_NVIDIA_SMI = False

    try:
        import wmi
        w = wmi.WMI(namespace="root\\CIMV2")
        gpu_items = w.Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine()
        if gpu_items:
            vals = [int(item.UtilizationPercentage) for item in gpu_items if hasattr(item, 'UtilizationPercentage')]
            if vals:
                gpu_stats["load"] = float(max(vals))
                
        ram = psutil.virtual_memory()
        total_sys_ram_gb = ram.total / (1024.0**3)
        gpu_stats["vram_total"] = round(total_sys_ram_gb * 0.5, 1)
        gpu_stats["vram_used"] = round((ram.used / ram.total) * (gpu_stats["vram_total"] * 0.35), 1)
        gpu_stats["temp"] = round(get_cpu_temp() * 0.85, 0)
    except Exception:
        pass

    return gpu_stats

def get_disk_stats():
    """Get physical disk usage percentage."""
    disks = []
    seen = set()
    try:
        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            if 'cdrom' in part.opts:
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                drive_letter = part.mountpoint.split(':')[0].upper()
                if drive_letter and drive_letter not in seen:
                    disks.append({
                        "name": drive_letter,
                        "used": round(usage.percent, 0)
                    })
                    seen.add(drive_letter)
            except Exception:
                pass
    except Exception as e:
        pass

    if not disks:
        for letter in ['C', 'D', 'E', 'F']:
            path = f"{letter}:\\"
            if os.path.exists(path) and letter not in seen:
                try:
                    usage = psutil.disk_usage(path)
                    if usage.total > 0:
                        disks.append({
                            "name": letter,
                            "used": round(usage.percent, 0)
                        })
                        seen.add(letter)
                except Exception:
                    pass

    return disks

def main():
    print("=============================================")
    print("  ESP32 CYD DASHBOARD PC MONITOR SERVICE     ")
    print("  (Auto USB Serial Streamer)                 ")
    print("=============================================")
    
    last_net_bytes = psutil.net_io_counters()
    last_net_time = time.time()
    
    ser = None

    while True:
        if ser is None or not ser.is_open:
            print("Searching for ESP32 CYD Desk Dashboard...")
            ser = find_esp32_serial()
            
        if ser is None:
            print("ESP32 CYD not found via USB. Retrying in 3 seconds...")
            time.sleep(3.0)
            continue

        try:
            cpu_load = psutil.cpu_percent(interval=None)
            cpu_temp = get_cpu_temp()
            ram = psutil.virtual_memory()
            gpu = get_gpu_stats()
            disks = get_disk_stats()
            
            current_net_bytes = psutil.net_io_counters()
            current_net_time = time.time()
            time_diff = max(1.0, current_net_time - last_net_time)
            
            net_down = ((current_net_bytes.bytes_recv - last_net_bytes.bytes_recv) / 1024.0) / time_diff
            net_up = ((current_net_bytes.bytes_sent - last_net_bytes.bytes_sent) / 1024.0) / time_diff
            last_net_bytes, last_net_time = current_net_time, current_net_bytes

            payload = {
                "cpu": int(cpu_load),
                "cputemp": int(cpu_temp),
                "ram": int(ram.percent),
                "gpu": int(gpu["load"]),
                "gputemp": int(gpu["temp"]),
                "vram": int((gpu["vram_used"] / max(1.0, gpu["vram_total"])) * 100),
                "disks": disks,
                "net_down": int(net_down),
                "net_up": int(net_up)
            }

            if ser and ser.is_open:
                json_payload = json.dumps(payload) + "\n"
                ser.write(json_payload.encode('utf-8'))
                print(f"[USB Serial]: Sent -> CPU={cpu_load:.0f}% GPU={gpu['load']:.0f}% RAM={ram.percent}%")
                if ser.in_waiting:
                    try:
                        resp_line = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                        if "MEDIA_CMD:" in resp_line:
                            for l in resp_line.splitlines():
                                if "MEDIA_CMD:" in l:
                                    handle_media_action(l.split("MEDIA_CMD:")[1].strip())
                    except Exception:
                        pass
            
            time.sleep(2.0)

        except Exception as e:
            print(f"Transmission notice: {e}")
            if ser:
                try: ser.close()
                except Exception: pass
                ser = None
            time.sleep(3.0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting service. Goodbye!")
        sys.exit(0)
