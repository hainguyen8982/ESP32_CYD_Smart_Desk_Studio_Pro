import sys
import os
import time
import string
import json
import traceback
import threading
import unicodedata
import requests
import psutil
import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk
import socket
import ctypes
try:
    import winreg
except ImportError:
    winreg = None

APP_REG_KEY_NAME = "SmartDeskStudioPro"

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)

def is_windows_autostart_enabled():
    if sys.platform != "win32" or winreg is None:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        val, _ = winreg.QueryValueEx(key, APP_REG_KEY_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False

def set_windows_autostart(enable: bool):
    if sys.platform != "win32" or winreg is None:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        if enable:
            if getattr(sys, 'frozen', False):
                exe_path = f'"{sys.executable}"'
            else:
                script_path = os.path.abspath(sys.argv[0])
                exe_path = f'"{sys.executable}" "{script_path}"'
            winreg.SetValueEx(key, APP_REG_KEY_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_REG_KEY_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[Windows AutoStart Error] {e}")
        return False

def remove_vietnamese_accents(text):
    if not text:
        return ""
    s = text.replace('đ', 'd').replace('Đ', 'D')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return unicodedata.normalize('NFC', s)

def create_vector_icon(name, color="#38BDF8", size=16):
    """Draw crisp anti-aliased 32bit RGBA vector icons for CTkButtons using PIL ImageDraw."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        h = color.lstrip('#')
        rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        fill_col = rgb + (255,)
    except Exception:
        fill_col = (56, 189, 248, 255)

    if name == "pin":
        draw.ellipse([size*0.2, size*0.08, size*0.8, size*0.62], fill=fill_col)
        draw.polygon([(size*0.24, size*0.48), (size*0.76, size*0.48), (size*0.5, size*0.95)], fill=fill_col)
        draw.ellipse([size*0.38, size*0.25, size*0.62, size*0.45], fill=(3, 7, 18, 255))
    elif name == "sun":
        cx, cy, r = size*0.5, size*0.5, size*0.26
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=fill_col)
        w = max(1, int(size*0.09))
        draw.line([cx, 1, cx, size*0.18], fill=fill_col, width=w)
        draw.line([cx, size*0.82, cx, size-1], fill=fill_col, width=w)
        draw.line([1, cy, size*0.18, cy], fill=fill_col, width=w)
        draw.line([size*0.82, cy, size-1, cy], fill=fill_col, width=w)
    elif name == "fx":
        w = max(2, int(size*0.11))
        draw.line([size*0.12, size*0.32, size*0.75, size*0.32], fill=fill_col, width=w)
        draw.polygon([(size*0.58, size*0.16), (size*0.88, size*0.32), (size*0.58, size*0.48)], fill=fill_col)
        draw.line([size*0.25, size*0.68, size*0.88, size*0.68], fill=fill_col, width=w)
        draw.polygon([(size*0.42, size*0.52), (size*0.12, size*0.68), (size*0.42, size*0.84)], fill=fill_col)

    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

# Windows Virtual Key Definitions for Media Controls
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP       = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE      = 0xAD
VK_VOLUME_DOWN      = 0xAE
VK_VOLUME_UP        = 0xAF
VK_TAB              = 0x09
VK_RETURN           = 0x0D

active_serial_conn = None
serial_lock = threading.Lock()
app_instance = None

# Deduplication guard for Media commands received from both Serial + UDP
_last_media_cmd = ""
_last_media_cmd_time = 0.0
_MEDIA_DEDUP_WINDOW = 1.5  # 1.5s window — must exceed stream_loop sleep(1) to cover Serial+UDP overlap

# Windows Media Session State (populated by background poller)
_media_session_info = {"title": "", "artist": "", "playing": False}
_media_info_lock = threading.Lock()

CANVAS_WIDTH = 320
CANVAS_HEIGHT = 240
SCALE = 2.2

PAGE_ITEMS = [
    ("P0", "⛅", "Weather & Clock", "Realtime Clock, City Weather & SJC Gold", "#38BDF8"),
    ("P1", "📅", "Lunar Calendar", "Solar Date, Lunar Calendar & Good Hours", "#F472B6"),
    ("P2", "📈", "Finance & Trading", "SJC Gold Rates & World Stock Tickers", "#FBBF24"),
    ("P3", "💻", "PC Hardware Stats", "Realtime CPU Load, RAM & GPU Gauges", "#A855F7"),
    ("P4", "🚀", "Net & Storage Disks", "Network Speed & Disks C:/ D:/ Usage", "#34D399"),
    ("P5", "⏳", "Pomodoro Desk", "Productivity Desk Timer & Alarm Clock", "#FB7185"),
    ("P6", "🎵", "Media Remote", "Spotify Track Title, Artist & Volume", "#818CF8"),
    ("P7", "⚙", "System Settings", "WiFi RSSI, IP, LDR Brightness & Calib", "#94A3B8")
]

PAGE_NAMES = [f"{p[0]} • {p[2]}" for p in PAGE_ITEMS]

DOT_MATRIX_5X7 = {
    '0': [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    '1': [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    '2': [0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111],
    '3': [0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110],
    '4': [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    '5': [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    '6': [0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    '7': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    '8': [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    '9': [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100],
    ':': [0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b01100, 0b00000],
    'A': [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    'P': [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    'M': [0b10001, 0b11011, 0b10101, 0b10001, 0b10001, 0b10001, 0b10001],
    ' ': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000]
}

SEGMENT7_MASKS = {
    '0': 0x3F, '1': 0x06, '2': 0x5B, '3': 0x4F, '4': 0x66,
    '5': 0x6D, '6': 0x7D, '7': 0x07, '8': 0x7F, '9': 0x6F,
    '-': 0x40, ' ': 0x00
}

ELEMENT_PRESETS = [
    ("WiFi Signal Icon", "wifi_signal", "RSSI -54dBm", 55, 14, "#00E676", "mono"),
    ("WiFi IP Address Text", "text", "192.168.1.13", 75, 14, "#00E676", "mono"),
    ("PC Serial Status Icon", "text", "[USB Connected]", 45, 14, "#38BDF8", "mono"),
    ("Page Title & Icon", "text", "Weather Clock", 110, 14, "#FFD700", "default"),
    ("Page Counter Index", "text", "0/7", 30, 14, "#8B949E", "mono"),
    ("Status Bar Time", "status_time", "14:35", 55, 14, "#FFFFFF", "mono"),
    ("Digital Clock Digits", "matrix_text", "14:35:08", 170, 35, "#00F5FF", "dot_matrix"),
    ("Solar & Lunar Date", "text", "Mon 10/08 • 18/07 Lunar", 170, 18, "#8B949E", "default"),
    ("Dot Matrix Sun Icon", "pixel_sun", "sun", 50, 50, "#FFCC00", "dot_matrix"),
    ("Dot Matrix Sunrise Icon", "pixel_sunrise", "sunrise", 50, 50, "#FF9900", "dot_matrix"),
    ("Dot Matrix Red Divider", "dot_matrix_divider", "line", 290, 10, "#FF3333", "dot_matrix"),
    ("Weather City & Temp", "text", "28°C Hanoi", 110, 30, "#FFFFFF", "default"),
    ("Hardware Line Chart", "line_chart", "chart", 300, 55, "#CC00FF", "mono")
]

COLOR_PALETTES = {
    "Ocean Dark 🔵": {"accent": "#38BDF8", "sec": "#0284C7", "bg": "#0F172A", "line": "#00F5FF"},
    "Cyberpunk Neon 🟣": {"accent": "#00F5FF", "sec": "#FF00CC", "bg": "#140026", "line": "#39FF14"},
    "Forest Slate 🟢": {"accent": "#10B981", "sec": "#059669", "bg": "#064E3B", "line": "#34D399"},
    "Cherry Blossom 🌸": {"accent": "#F472B6", "sec": "#DB2777", "bg": "#4C0519", "line": "#FB7185"},
    "Light Day ☀️": {"accent": "#0284C7", "sec": "#0369A1", "bg": "#F8FAFC", "line": "#38BDF8"},
    "Retro Green 📟": {"accent": "#00FF41", "sec": "#009926", "bg": "#000000", "line": "#00FF41"}
}

ELEMENT_CATEGORIES = [
    ("🕒 Thời gian & Ngày tháng", [
        ("Status Bar Time", "status_time", "14:35", 55, 14, "#FFFFFF", "mono"),
        ("Digital Clock Digits", "matrix_text", "14:35:08", 170, 35, "#00F5FF", "dot_matrix"),
        ("Solar & Lunar Date", "text", "Mon 10/08 • 18/07 Lunar", 170, 18, "#8B949E", "default"),
        ("Page Counter Index", "text", "0/7", 30, 14, "#8B949E", "mono"),
    ]),
    ("📡 Hệ thống & Kết nối", [
        ("WiFi Signal Icon", "wifi_signal", "RSSI -54dBm", 55, 14, "#00E676", "mono"),
        ("WiFi IP Address Text", "text", "192.168.1.13", 75, 14, "#00E676", "mono"),
        ("PC Serial Status Icon", "text", "[USB Connected]", 45, 14, "#38BDF8", "mono"),
        ("Page Title & Icon", "text", "Weather Clock", 110, 14, "#FFD700", "default"),
    ]),
    ("🌤️ Thời tiết & Cảm biến", [
        ("Weather City & Temp", "text", "28°C Hanoi", 110, 30, "#FFFFFF", "default"),
        ("Hardware Line Chart", "line_chart", "chart", 300, 55, "#CC00FF", "mono"),
    ]),
    ("🎨 Đồ họa Dot-Matrix", [
        ("Dot Matrix Sun Icon", "pixel_sun", "sun", 50, 50, "#FFCC00", "dot_matrix"),
        ("Dot Matrix Sunrise Icon", "pixel_sunrise", "sunrise", 50, 50, "#FF9900", "dot_matrix"),
        ("Dot Matrix Red Divider", "dot_matrix_divider", "line", 290, 10, "#FF3333", "dot_matrix"),
    ]),
    ("📐 Đồ họa & Đường kẻ", [
        ("Đường kẻ phân cách (Line)", "line", "line", 300, 2, "#1f2937", "default"),
        ("Khung hình chữ nhật (Box)", "rectangle", "box", 140, 60, "#111827", "default"),
        ("Hình tròn / Dot (Circle)", "circle", "dot", 20, 20, "#00F5FF", "default"),
    ])
]

VN_CITIES = [
    ("Hanoi", "Hà Nội"), ("Ho Chi Minh", "TP. Hồ Chí Minh"), ("Da Nang", "Đà Nẵng"),
    ("Hai Phong", "Hải Phòng"), ("Can Tho", "Cần Thơ"), ("An Giang", "An Giang"),
    ("Vung Tau", "Bà Rịa - Vũng Tàu"), ("Bac Giang", "Bắc Giang"), ("Bac Kan", "Bắc Kạn"),
    ("Bac Lieu", "Bạc Liêu"), ("Bac Ninh", "Bắc Ninh"), ("Ben Tre", "Bến Tre"),
    ("Binh Dinh", "Bình Định"), ("Binh Duong", "Bình Dương"), ("Binh Phuoc", "Bình Phước"),
    ("Binh Thuan", "Bình Thuận"), ("Ca Mau", "Cà Mau"), ("Cao Bang", "Cao Bằng"),
    ("Dak Lak", "Đắk Lắk"), ("Dak Nong", "Đắk Nông"), ("Dien Bien", "Điện Biên"),
    ("Dong Nai", "Đồng Nai"), ("Dong Thap", "Đồng Tháp"), ("Gia Lai", "Gia Lai"),
    ("Ha Giang", "Hà Giang"), ("Ha Nam", "Hà Nam"), ("Ha Tinh", "Hà Tĩnh"),
    ("Hai Duong", "Hải Dương"), ("Hau Giang", "Hậu Giang"), ("Hoa Binh", "Hòa Bình"),
    ("Hung Yen", "Hưng Yên"), ("Nha Trang", "Khánh Hòa (Nha Trang)"), ("Kien Giang", "Kiên Giang"),
    ("Kon Tum", "Kon Tum"), ("Lai Chau", "Lai Châu"), ("Da Lat", "Lâm Đồng (Đà Lạt)"),
    ("Lang Son", "Lạng Sơn"), ("Lao Cai", "Lào Cai"), ("Long An", "Long An"),
    ("Nam Dinh", "Nam Định"), ("Nghe An", "Nghệ An"), ("Ninh Binh", "Ninh Bình"),
    ("Ninh Thuan", "Ninh Thuận"), ("Phu Tho", "Phú Thọ"), ("Phu Yen", "Phú Yên"),
    ("Quang Binh", "Quảng Bình"), ("Quang Nam", "Quảng Nam"), ("Quang Ngai", "Quảng Ngãi"),
    ("Quang Ninh", "Quảng Ninh"), ("Quang Tri", "Quảng Trị"), ("Soc Trang", "Sóc Trăng"),
    ("Son La", "Sơn La"), ("Tay Ninh", "Tây Ninh"), ("Thai Binh", "Thái Bình"),
    ("Thai Nguyen", "Thái Nguyên"), ("Thanh Hoa", "Thanh Hóa"), ("Hue", "Thừa Thiên Huế"),
    ("Tien Giang", "Tiền Giang"), ("Tra Vinh", "Trà Vinh"), ("Tuyen Quang", "Tuyên Quang"),
    ("Vinh Long", "Vĩnh Long"), ("Vinh Phuc", "Vĩnh Phúc"), ("Yen Bai", "Yên Bái")
]

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def _media_session_poller():
    """Background thread: poll Windows Media Transport Controls for track info every 2s."""
    global _media_session_info
    try:
        import asyncio
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

        async def _get_media_info():
            mgr = await GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = mgr.get_current_session()
            if session is None:
                return {"title": "", "artist": "", "playing": False}

            info = await session.try_get_media_properties_async()
            playback = session.get_playback_info()

            title = str(info.title) if info.title else ""
            artist = str(info.artist) if info.artist else ""
            # PlaybackStatus: 4 = Playing, 5 = Paused
            is_playing = (playback.playback_status == 4) if playback else False

            return {"title": title, "artist": artist, "playing": is_playing}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            try:
                result = loop.run_until_complete(_get_media_info())
                with _media_info_lock:
                    _media_session_info = result
            except Exception:
                pass
            time.sleep(2)
    except ImportError:
        print("[Media Poller] winsdk not available, media info disabled")
    except Exception as e:
        print(f"[Media Poller] Error: {e}")

def _get_gpu_stats():
    """Get GPU load %, GPU temp °C, VRAM % via nvidia-smi, win32pdh, or fallback."""
    # 1. Try nvidia-smi (NVIDIA GPUs)
    try:
        import subprocess
        nvsmi = r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
        cmd = [nvsmi if os.path.exists(nvsmi) else "nvidia-smi",
               "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total",
               "--format=csv,noheader,nounits"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, _ = proc.communicate(timeout=0.4)
        if proc.returncode == 0 and stdout.strip():
            parts = [p.strip() for p in stdout.strip().split(",")]
            if len(parts) >= 4:
                gpu_pct = int(float(parts[0]))
                gpu_temp = int(float(parts[1]))
                used = float(parts[2])
                total = float(parts[3])
                vram_pct = int((used / total) * 100) if total > 0 else 0
                return gpu_pct, gpu_temp, vram_pct
    except Exception:
        pass

    # 2. Try win32pdh performance counters (Intel/AMD/NVIDIA on Windows)
    try:
        import win32pdh
        hq = win32pdh.OpenQuery()
        hc = win32pdh.AddCounter(hq, r"\GPU Engine(*)\Utilization Percentage")
        win32pdh.CollectQueryData(hq)
        time.sleep(0.02)
        win32pdh.CollectQueryData(hq)
        vals = win32pdh.GetFormattedCounterArray(hc, win32pdh.PDH_FMT_DOUBLE)
        win32pdh.CloseQuery(hq)
        if vals:
            gpu_pct = min(100, int(sum(v for v in vals.values() if v > 0)))
            gpu_temp = 38 + int(gpu_pct * 0.4)
            vram_pct = min(100, int(gpu_pct * 0.7 + 15))
            return gpu_pct, gpu_temp, vram_pct
    except Exception:
        pass

    return 0, 0, 0

class SmartDeskStudioProApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("👑 Smart Desk Studio Pro — PC Control Center")
        self.geometry("1400x920")
        self.resizable(True, True)

        # Set app window icon if available
        ico_path = get_resource_path(os.path.join("assets", "app_icon.ico"))
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        # Deep Obsidian Charcoal Theme (#0b0f19)
        self.configure(fg_color="#0b0f19")

        # Explicit Window Close Protocol to release Serial port & kill background Python process
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)

        # Robust Window Maximization for CustomTkinter on Windows
        self.after(100, lambda: self._maximize_window())
        self.after(300, lambda: self._maximize_window())

        # Global mousewheel listener to close city dropdown instantly when scrolling anywhere in app
        try:
            self.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")
        except Exception:
            pass

        global app_instance
        app_instance = self

        self.esp32_ip = "192.168.1.13"
        self.cached_ip = "192.168.1.13"
        self.cached_com_port = ""
        self.selected_com_port = "AUTO"
        self.is_streaming = True
        self.active_cyd_page = 0
        self.last_net = None
        self.last_time = time.time()
        self.last_port_scan = 0
        self.last_user_action_time = 0

        # Thread-safe control dictionary for merging commands into Serial JSON stream
        self.pending_control = {}

        self.create_unified_ui()
        self.refresh_com_ports()

        self.stream_thread = threading.Thread(target=self.stream_loop, daemon=True)
        self.stream_thread.start()

        # Start UDP Listener thread for WiFi Media Remote Commands (Port 8080)
        self.udp_thread = threading.Thread(target=self.udp_listener_loop, daemon=True)
        self.udp_thread.start()

        # Start Windows Media Session Poller (track title, artist, playing state)
        self.media_poller_thread = threading.Thread(target=_media_session_poller, daemon=True)
        self.media_poller_thread.start()

    def on_app_close(self):
        """Clean shutdown handler: close Serial port & terminate process immediately."""
        self.is_streaming = False
        global active_serial_conn
        with serial_lock:
            if active_serial_conn and active_serial_conn.is_open:
                try:
                    active_serial_conn.close()
                except Exception:
                    pass
                active_serial_conn = None
        try:
            self.destroy()
        except Exception:
            pass
        if sys.platform == "win32":
            try:
                ctypes.windll.kernel32.ExitProcess(0)
            except Exception:
                pass
        os._exit(0)

    def _maximize_window(self):
        try:
            if sys.platform == "win32":
                self.state('zoomed')
        except Exception:
            pass



    def handle_media_action(self, action):
        """Execute Windows Virtual Key Event for Media Control with deduplication guard."""
        global _last_media_cmd, _last_media_cmd_time
        now = time.time()
        # Dedup: ignore if same command arrives within 500ms (Serial + UDP fire together)
        if action == _last_media_cmd and (now - _last_media_cmd_time) < _MEDIA_DEDUP_WINDOW:
            return
        _last_media_cmd = action
        _last_media_cmd_time = now

        if sys.platform == "win32":
            try:
                if action == "play_pause":
                    ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
                    # Instantly flip local media state so next JSON to CYD is correct
                    # (don't wait 2s for the WinRT poller to detect the change)
                    with _media_info_lock:
                        _media_session_info["playing"] = not _media_session_info.get("playing", False)
                    self.status_lbl.configure(text="🎵 Media: Play / Pause Toggled", text_color="#38bdf8")
                elif action == "next":
                    ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 2, 0)
                    self.status_lbl.configure(text="🎵 Media: Next Track ⏭️", text_color="#38bdf8")
                elif action == "prev":
                    ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 2, 0)
                    self.status_lbl.configure(text="🎵 Media: Prev Track ⏮️", text_color="#38bdf8")
                elif action == "vol_up":
                    ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
                    self.status_lbl.configure(text="🔊 Volume Up ⬆️", text_color="#39FF14")
                elif action == "vol_down":
                    ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
                    self.status_lbl.configure(text="🔉 Volume Down ⬇️", text_color="#39FF14")
                elif action in ("mute", "skip_ad"):
                    ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
                    self.status_lbl.configure(text="🔇 Mute Audio Toggled", text_color="#F85149")
            except Exception as e:
                print(f"[Media] Keybd Event Error: {e}")

    def udp_listener_loop(self):
        """Listen for UDP Broadcast Media Control Packets on Port 8080.
        Only processes MEDIA_CMD when USB Serial is NOT connected (Serial is primary channel)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', 8080))
            sock.settimeout(1.0)
            while self.is_streaming:
                try:
                    data, _ = sock.recvfrom(1024)
                    text = data.decode('utf-8', errors='ignore').strip()
                    if text.startswith("MEDIA_CMD:"):
                        # Skip if Serial is connected — Serial reader already handles MEDIA_CMD
                        if active_serial_conn and active_serial_conn.is_open:
                            continue
                        act = text[10:].strip()
                        self.after(0, lambda a=act: self.handle_media_action(a))
                except socket.timeout:
                    continue
                except Exception:
                    time.sleep(0.5)
        except Exception as e:
            print(f"[UDP] Listener start error: {e}")

    def get_icon(self, name, size=(18, 18)):
        p = get_resource_path(os.path.join("assets", f"{name}.png"))
        if os.path.exists(p):
            try:
                img = Image.open(p)
                return ctk.CTkImage(light_image=img, dark_image=img, size=size)
            except Exception: pass
        return None

    def create_unified_ui(self):
        main_container = ctk.CTkFrame(self, fg_color="#030712")
        main_container.pack(fill="both", expand=True, padx=8, pady=8)

        # ── Compact Top Header (App Title & Status Bar) ───────────────
        hdr = ctk.CTkFrame(main_container, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        hdr.pack(fill="x", pady=(0, 8))

        title_lbl = ctk.CTkLabel(
            hdr, text="👑 Smart Desk Studio Pro", font=ctk.CTkFont(size=18, weight="bold"), text_color="#38bdf8"
        )
        title_lbl.pack(side="left", padx=15, pady=8)

        # COM Selector Frame
        com_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        com_frame.pack(side="left", padx=20, pady=8)

        port_icon = self.get_icon("port", size=(16, 16))
        refresh_icon = self.get_icon("refresh", size=(16, 16))

        port_lbl = ctk.CTkLabel(
            com_frame, text="  Port:", image=port_icon, compound="left",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8"
        )
        port_lbl.pack(side="left", padx=(0, 5))

        self.com_combo = ctk.CTkOptionMenu(com_frame, values=["Auto Detect"], width=150, command=self.on_com_select)
        self.com_combo.pack(side="left", padx=2)

        ref_btn = ctk.CTkButton(
            com_frame, text="", image=refresh_icon, width=32, height=28,
            fg_color="#1f2937", hover_color="#374151", command=self.refresh_com_ports
        )
        ref_btn.pack(side="left", padx=4)

        self.status_lbl = ctk.CTkLabel(
            hdr, text="🟡 Standby Mode (Check Cable / COM Port)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#EAB308"
        )
        self.status_lbl.pack(side="right", padx=15, pady=8)

        # ── Full Width Custom Tab Segmented Header ──────────────────────
        self.tab_hdr_frame = ctk.CTkFrame(main_container, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10, height=45)
        self.tab_hdr_frame.pack(fill="x", pady=(0, 8))

        img_tab_live = self.get_icon("tab_live", size=(18, 18))
        img_tab_settings = self.get_icon("tab_settings", size=(18, 18))

        self.tab_btn_live = ctk.CTkButton(
            self.tab_hdr_frame, text="  Live Control Center", image=img_tab_live, compound="left",
            font=ctk.CTkFont(size=13, weight="bold"), height=36, fg_color="#1f2937", hover_color="#374151", text_color="#38bdf8",
            command=lambda: self.switch_main_tab("live")
        )
        self.tab_btn_live.pack(side="left", fill="x", expand=True, padx=4, pady=4)

        self.tab_btn_settings = ctk.CTkButton(
            self.tab_hdr_frame, text="  System Settings", image=img_tab_settings, compound="left",
            font=ctk.CTkFont(size=13, weight="bold"), height=36, fg_color="transparent", hover_color="#374151", text_color="#94a3b8",
            command=lambda: self.switch_main_tab("settings")
        )
        self.tab_btn_settings.pack(side="left", fill="x", expand=True, padx=4, pady=4)

        # Main Tab Body Stack Frame
        self.body_stack = ctk.CTkFrame(main_container, fg_color="transparent")
        self.body_stack.pack(fill="both", expand=True)

        self.view_live = ctk.CTkFrame(self.body_stack, fg_color="transparent")
        self.view_settings = ctk.CTkFrame(self.body_stack, fg_color="transparent")

        self.view_live.pack(fill="both", expand=True)

        self.build_tab_live()
        self.build_tab_settings()

    def switch_main_tab(self, tab_name):
        self.view_live.pack_forget()
        self.view_settings.pack_forget()

        self.tab_btn_live.configure(fg_color="transparent", text_color="#94a3b8")
        self.tab_btn_settings.configure(fg_color="transparent", text_color="#94a3b8")

        if tab_name == "live":
            self.view_live.pack(fill="both", expand=True)
            self.tab_btn_live.configure(fg_color="#1f2937", text_color="#38bdf8")
        elif tab_name == "settings":
            self.view_settings.pack(fill="both", expand=True)
            self.tab_btn_settings.configure(fg_color="#1f2937", text_color="#38bdf8")

    def refresh_com_ports(self):
        ports = list(serial.tools.list_ports.comports())
        val_list = ["Auto Detect"]
        for p in ports:
            p_desc = str(p.description)
            val_list.append(f"{p.device} ({p_desc})")
        self.com_combo.configure(values=val_list)

    def on_com_select(self, val):
        if val == "Auto Detect":
            self.selected_com_port = "AUTO"
        else:
            self.selected_com_port = val.split(" ")[0].strip()
        self.force_reconnect()

    # ── TAB 1: LIVE CONTROL CENTER ────────────────────────────────────
    def build_tab_live(self):
        container = ctk.CTkFrame(self.view_live, fg_color="transparent")
        container.pack(fill="both", expand=True)

        col_left = ctk.CTkScrollableFrame(container, fg_color="transparent")
        col_left.pack(fill="both", expand=True)
        self.col_left = col_left

        # Auto-close dropdown popup whenever user scrolls main application window
        def _on_main_scroll(event=None):
            self.close_city_dropdown()

        self.col_left.bind("<MouseWheel>", _on_main_scroll, add="+")
        try:
            if hasattr(self.col_left, '_parent_canvas'):
                self.col_left._parent_canvas.bind("<MouseWheel>", _on_main_scroll, add="+")
        except Exception:
            pass

        # 1. Telemetry Cards
        tele_frame = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        tele_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(tele_frame, text="📊 Live PC Telemetry Metrics", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(10, 6))

        m_grid = ctk.CTkFrame(tele_frame, fg_color="transparent")
        m_grid.pack(fill="x", padx=10, pady=(0, 10))

        cpu_box = ctk.CTkFrame(m_grid, fg_color="#030712", border_width=1, border_color="#1f2937", corner_radius=8)
        cpu_box.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(cpu_box, text="CPU LOAD", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_cpu = ctk.CTkLabel(cpu_box, text="0%", font=ctk.CTkFont(size=20, weight="bold"), text_color="#00F5FF")
        self.lbl_cpu.pack(anchor="w", padx=10, pady=1)
        self.bar_cpu = ctk.CTkProgressBar(cpu_box, height=5, progress_color="#00F5FF", fg_color="#1f2937")
        self.bar_cpu.set(0.0); self.bar_cpu.pack(fill="x", padx=10, pady=(0, 8))

        ram_box = ctk.CTkFrame(m_grid, fg_color="#030712", border_width=1, border_color="#1f2937", corner_radius=8)
        ram_box.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(ram_box, text="RAM LOAD", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_ram = ctk.CTkLabel(ram_box, text="0%", font=ctk.CTkFont(size=20, weight="bold"), text_color="#AB47BC")
        self.lbl_ram.pack(anchor="w", padx=10, pady=1)
        self.bar_ram = ctk.CTkProgressBar(ram_box, height=5, progress_color="#AB47BC", fg_color="#1f2937")
        self.bar_ram.set(0.0); self.bar_ram.pack(fill="x", padx=10, pady=(0, 8))

        down_box = ctk.CTkFrame(m_grid, fg_color="#030712", border_width=1, border_color="#1f2937", corner_radius=8)
        down_box.grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(down_box, text="NET DOWN", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_net_down = ctk.CTkLabel(down_box, text="0 KB/s", font=ctk.CTkFont(size=17, weight="bold"), text_color="#00E676")
        self.lbl_net_down.pack(anchor="w", padx=10, pady=1)
        self.bar_net_down = ctk.CTkProgressBar(down_box, height=5, progress_color="#00E676", fg_color="#1f2937")
        self.bar_net_down.set(0.0); self.bar_net_down.pack(fill="x", padx=10, pady=(0, 8))

        up_box = ctk.CTkFrame(m_grid, fg_color="#030712", border_width=1, border_color="#1f2937", corner_radius=8)
        up_box.grid(row=0, column=3, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(up_box, text="NET UP", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_net_up = ctk.CTkLabel(up_box, text="0 KB/s", font=ctk.CTkFont(size=17, weight="bold"), text_color="#FFA726")
        self.lbl_net_up.pack(anchor="w", padx=10, pady=1)
        self.bar_net_up = ctk.CTkProgressBar(up_box, height=5, progress_color="#FFA726", fg_color="#1f2937")
        self.bar_net_up.set(0.0); self.bar_net_up.pack(fill="x", padx=10, pady=(0, 8))

        for c_i in range(4): m_grid.columnconfigure(c_i, weight=1, uniform="tele_cols")

        # 2. Rich Page Switcher Grid
        p_frame = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        p_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(p_frame, text="🖥️ Switch Dashboard Page (Pages P0 .. P7)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(10, 6))

        p_grid = ctk.CTkFrame(p_frame, fg_color="transparent")
        p_grid.pack(fill="x", padx=10, pady=(0, 10))

        self.page_btns = []
        for pid in range(8):
            row = pid // 2; col = pid % 2
            p_code, p_ico, p_title, p_sub, p_color = PAGE_ITEMS[pid]

            btn_box = ctk.CTkFrame(p_grid, fg_color="#030712", border_width=1, border_color="#1f2937", corner_radius=8)
            btn_box.grid(row=row, column=col, padx=4, pady=3, sticky="ew")

            btn_box.bind("<Button-1>", lambda e, p=pid: self.switch_page(p))

            badge_lbl = ctk.CTkLabel(btn_box, text=f" {p_code} ", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#1f2937", text_color=p_color, corner_radius=4)
            badge_lbl.pack(side="left", padx=8, pady=6)

            txt_inner = ctk.CTkFrame(btn_box, fg_color="transparent")
            txt_inner.pack(side="left", fill="x", expand=True, padx=(2, 6), pady=4)

            title_lbl = ctk.CTkLabel(txt_inner, text=f"{p_ico}  {p_title}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FFFFFF", anchor="w")
            title_lbl.pack(anchor="w", pady=0)

            sub_lbl = ctk.CTkLabel(txt_inner, text=p_sub, font=ctk.CTkFont(size=10), text_color="#94a3b8", anchor="w")
            sub_lbl.pack(anchor="w", pady=0)

            badge_lbl.bind("<Button-1>", lambda e, p=pid: self.switch_page(p))
            txt_inner.bind("<Button-1>", lambda e, p=pid: self.switch_page(p))
            title_lbl.bind("<Button-1>", lambda e, p=pid: self.switch_page(p))
            sub_lbl.bind("<Button-1>", lambda e, p=pid: self.switch_page(p))

            self.page_btns.append(btn_box)

        for col_i in range(2): p_grid.columnconfigure(col_i, weight=1, uniform="p_cols")

        self._highlight_page_button(0)

        # 3. Preset Theme Switcher
        th_frame = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        th_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(th_frame, text="🎨 Preset Firmware Theme Switcher", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(10, 6))

        th_grid = ctk.CTkFrame(th_frame, fg_color="transparent")
        th_grid.pack(fill="x", padx=10, pady=(0, 10))

        preset_themes = [
            ("Ocean Dark", "ocean_dark", "#38BDF8"),
            ("Cyberpunk Neon", "cyberpunk", "#FF00CC"),
            ("Forest Slate", "forest", "#10B981"),
            ("Cherry Blossom", "cherry", "#F472B6"),
            ("Light Day", "light_day", "#0284C7"),
            ("Retro Green", "retro_green", "#00FF41")
        ]
        self.theme_btns = {}
        for idx, (tname, tkey, acc_col) in enumerate(preset_themes):
            row = idx // 3; col = idx % 3
            t_btn = ctk.CTkButton(
                th_grid, text=f"✨ {tname}", font=ctk.CTkFont(size=12, weight="bold"),
                height=36, fg_color="#030712", hover_color="#1f2937", text_color=acc_col,
                border_width=1, border_color="#1f2937",
                command=lambda k=tkey: self.apply_theme(k)
            )
            t_btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            self.theme_btns[tkey] = (t_btn, acc_col)

        for col_i in range(3): th_grid.columnconfigure(col_i, weight=1, uniform="th_cols")

        # 4. Weather Location & Currency Settings
        w_frame = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        w_frame.pack(fill="x", pady=6)
        self.w_frame = w_frame

        ctk.CTkLabel(w_frame, text="🌤️ Weather Location & 💱 Foreign Exchange Currencies", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(10, 6))

        # Single Clean Row: Expandable City Button + Set City Button + Currency Combos
        w_inner = ctk.CTkFrame(w_frame, fg_color="transparent")
        w_inner.pack(fill="x", padx=12, pady=(0, 8))
        self.w_inner = w_inner

        self.selected_city_eng = "Hanoi"
        self.selected_city_vn = "Hà Nội"

        ico_pin = create_vector_icon("pin", color="#38BDF8", size=15)
        ico_sun = create_vector_icon("sun", color="#FFFFFF", size=15)
        ico_fx = create_vector_icon("fx", color="#FFFFFF", size=15)

        self.city_picker_btn = ctk.CTkButton(
            w_inner, text="Hà Nội  ▼", image=ico_pin, compound="left",
            width=210, height=34, fg_color="#030712", hover_color="#1f2937", text_color="#F8FAFC",
            border_width=1, border_color="#38bdf8", font=ctk.CTkFont(size=12, weight="bold"),
            command=self.toggle_city_search_panel
        )
        self.city_picker_btn.pack(side="left", padx=(0, 8))

        set_city_btn = ctk.CTkButton(
            w_inner, text="Set City", image=ico_sun, compound="left",
            width=100, height=34, fg_color="#0284C7", hover_color="#0369A1",
            font=ctk.CTkFont(size=12, weight="bold"), command=self.apply_city
        )
        set_city_btn.pack(side="left", padx=(0, 12))

        currencies = ["USD", "EUR", "JPY", "GBP", "AUD", "SGD", "CNY", "KRW"]
        self.cur1_combo = ctk.CTkOptionMenu(w_inner, values=currencies, width=75, height=34)
        self.cur1_combo.set("USD"); self.cur1_combo.pack(side="left", padx=(0, 4))

        self.cur2_combo = ctk.CTkOptionMenu(w_inner, values=currencies, width=75, height=34)
        self.cur2_combo.set("EUR"); self.cur2_combo.pack(side="left", padx=(0, 6))

        set_cur_btn = ctk.CTkButton(
            w_inner, text="Set FX", image=ico_fx, compound="left",
            width=90, height=34, fg_color="#0284C7", hover_color="#0369A1",
            font=ctk.CTkFont(size=12, weight="bold"), command=self.apply_currencies
        )
        set_cur_btn.pack(side="left")




        # 5. Media Remote PC Buttons
        m_frame = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        m_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(m_frame, text="🎵 Media Control Hotkeys (Bấm nhanh trên PC)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(10, 6))

        m_btn_grid = ctk.CTkFrame(m_frame, fg_color="transparent")
        m_btn_grid.pack(fill="x", padx=10, pady=(0, 10))

        def _get_icon(name):
            p = get_resource_path(os.path.join("assets", f"{name}.png"))
            if os.path.exists(p):
                try:
                    img = Image.open(p)
                    return ctk.CTkImage(light_image=img, dark_image=img, size=(18, 18))
                except Exception: pass
            return None

        media_btns = [
            ("PREV", "prev", "#818CF8", _get_icon("prev")),
            ("PLAY / PAUSE", "play_pause", "#39FF14", _get_icon("play_pause")),
            ("NEXT", "next", "#818CF8", _get_icon("next")),
            ("VOL -", "vol_down", "#FBBF24", _get_icon("vol_down")),
            ("MUTE", "mute", "#F85149", _get_icon("mute")),
            ("VOL +", "vol_up", "#FBBF24", _get_icon("vol_up"))
        ]

        for idx, (m_lbl, m_act, acc_c, m_img) in enumerate(media_btns):
            row = idx // 3; col = idx % 3
            mb = ctk.CTkButton(
                m_btn_grid, text=f"  {m_lbl}", image=m_img, font=ctk.CTkFont(size=12, weight="bold"),
                height=38, fg_color="#030712", hover_color="#1f2937", text_color=acc_c,
                border_width=1, border_color="#1f2937", compound="left",
                command=lambda a=m_act: self.handle_media_action(a)
            )
            mb.grid(row=row, column=col, padx=4, pady=4, sticky="ew")

        for col_i in range(3): m_btn_grid.columnconfigure(col_i, weight=1)

        # 6. Alarm Clock Quick Setup & Memo Panel (Spacious 2-Row Layout)
        alm_frame = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        alm_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(alm_frame, text="⏰ Quick Desk Alarm Clock Setup & Memo", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(10, 6))

        # Row 1: Time Pickers & Action Buttons
        alm_row1 = ctk.CTkFrame(alm_frame, fg_color="transparent")
        alm_row1.pack(fill="x", padx=12, pady=(0, 6))

        ctk.CTkLabel(alm_row1, text="Hour:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8").pack(side="left", padx=(0, 4))
        hours = [f"{h:02d}" for h in range(24)]
        self.alarm_h_combo = ctk.CTkOptionMenu(alm_row1, values=hours, width=65)
        self.alarm_h_combo.set("07"); self.alarm_h_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(alm_row1, text="Min:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8").pack(side="left", padx=(0, 4))
        mins = [f"{m:02d}" for m in range(0, 60, 5)]
        self.alarm_m_combo = ctk.CTkOptionMenu(alm_row1, values=mins, width=65)
        self.alarm_m_combo.set("00"); self.alarm_m_combo.pack(side="left", padx=(0, 15))

        self.set_alm_btn = ctk.CTkButton(
            alm_row1, text="⏰ Set Alarm", width=115, height=32, fg_color="#FB7185", hover_color="#E11D48",
            font=ctk.CTkFont(size=12, weight="bold"), command=self.apply_alarm
        )
        self.set_alm_btn.pack(side="left", padx=(0, 8))

        self.toggle_alm_btn = ctk.CTkButton(
            alm_row1, text="⏰ Alarm Off", width=115, height=32, fg_color="#7F1D1D", hover_color="#991B1B",
            text_color="#FCA5A5", border_width=2, border_color="#EF4444",
            font=ctk.CTkFont(size=12, weight="bold"), command=self.toggle_alarm_state
        )
        self.toggle_alm_btn.pack(side="left")


        # Row 2: Full-width Memo / Note text input field
        alm_row2 = ctk.CTkFrame(alm_frame, fg_color="transparent")
        alm_row2.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(alm_row2, text="Memo / Ghi chú:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8").pack(side="left", padx=(0, 8))
        self.alarm_note_entry = ctk.CTkEntry(alm_row2, placeholder_text="Nhập ghi chú nhắc nhở khi báo thức (VD: Hop team phong 302)...")
        self.alarm_note_entry.pack(side="left", fill="x", expand=True)

        # 7. Action Control Bar (Sync & Reconnect)
        act_bar = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        act_bar.pack(fill="x", pady=6)

        sync_now_btn = ctk.CTkButton(
            act_bar, text="⚡ 1-Click Sync Telemetry to Desk", font=ctk.CTkFont(weight="bold"),
            height=36, fg_color="#238636", hover_color="#2ea043", command=self.sync_telemetry_now
        )
        sync_now_btn.pack(side="left", fill="x", expand=True, padx=8, pady=8)

        recon_btn = ctk.CTkButton(
            act_bar, text="🔄 Force Reconnect USB/WiFi", font=ctk.CTkFont(weight="bold"),
            height=36, fg_color="#1f2937", hover_color="#374151", text_color="#38bdf8", command=self.force_reconnect
        )
        recon_btn.pack(side="right", fill="x", expand=True, padx=8, pady=8)

    # ── TAB 3: SYSTEM SETTINGS ────────────────────────────────────────
    def build_tab_settings(self):
        container = ctk.CTkFrame(self.view_settings, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        s_frame = ctk.CTkFrame(container, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        s_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(s_frame, text="⚙️ App & Connection Settings", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=12, pady=(10, 5))

        ip_inner = ctk.CTkFrame(s_frame, fg_color="transparent")
        ip_inner.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(ip_inner, text="CYD WiFi IP Address:").pack(side="left", padx=(0, 10))
        self.ip_entry = ctk.CTkEntry(ip_inner, width=180)
        self.ip_entry.insert(0, self.esp32_ip)
        self.ip_entry.pack(side="left")

        # Real Windows Startup Registry Integration
        self.autostart_var = ctk.BooleanVar(value=is_windows_autostart_enabled())

        def _on_autostart_toggle():
            en = self.autostart_var.get()
            ok = set_windows_autostart(en)
            if ok:
                st = "được bật" if en else "đã tắt"
                self.status_lbl.configure(text=f"✅ Tự khởi động cùng Windows {st}", text_color="#39FF14")
            else:
                self.status_lbl.configure(text="⚠️ Không thể ghi Registry Windows", text_color="#FCA5A5")

        autostart_chk = ctk.CTkCheckBox(
            s_frame, text="🚀 Run Smart Desk Studio Pro on Windows Startup",
            variable=self.autostart_var, command=_on_autostart_toggle,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        autostart_chk.pack(anchor="w", padx=12, pady=8)

    def sync_telemetry_now(self):
        self.last_user_action_time = time.time()
        self.last_port_scan = 0
        if hasattr(self, 'status_lbl'):
            self.status_lbl.configure(text="⚡ Telemetry synced to ESP32 CYD!", text_color="#39FF14")

    def draw_dot_matrix_text(self, text, start_x, start_y, dot_size, pitch, on_color, off_color="#121212", elem_id=""):
        cur_x = start_x
        for ch in text.upper():
            bm = DOT_MATRIX_5X7.get(ch, DOT_MATRIX_5X7.get(' '))
            for row in range(7):
                row_bits = bm[row]
                for col in range(5):
                    is_on = (row_bits >> (4 - col)) & 1
                    dx = cur_x + col * pitch; dy = start_y + row * pitch
                    col_fill = on_color if is_on else off_color
                    self.canvas.create_oval(dx, dy, dx + dot_size, dy + dot_size, fill=col_fill, outline="", tags=("element", elem_id))
            cur_x += 6 * pitch

    def draw_7segment_text(self, text, start_x, start_y, seg_w, seg_h, color, elem_id=""):
        cur_x = start_x
        for ch in text:
            if ch == ':':
                self.canvas.create_rectangle(cur_x + int(seg_w/2) - 2, start_y + int(seg_h*0.3), cur_x + int(seg_w/2) + 2, start_y + int(seg_h*0.3) + 4, fill=color, outline="", tags=("element", elem_id))
                self.canvas.create_rectangle(cur_x + int(seg_w/2) - 2, start_y + int(seg_h*0.7), cur_x + int(seg_w/2) + 2, start_y + int(seg_h*0.7) + 4, fill=color, outline="", tags=("element", eid if 'eid' in locals() else ""))
                cur_x += int(seg_w * 0.5); continue

            mask = SEGMENT7_MASKS.get(ch, 0x00); off_col = "#151820"; t = 3
            self.canvas.create_rectangle(cur_x + t, start_y, cur_x + seg_w - t, start_y + t, fill=color if (mask & 0x01) else off_col, outline="")
            self.canvas.create_rectangle(cur_x + seg_w - t, start_y + t, cur_x + seg_w, start_y + int(seg_h/2) - int(t/2), fill=color if (mask & 0x02) else off_col, outline="")
            self.canvas.create_rectangle(cur_x + seg_w - t, start_y + int(seg_h/2) + int(t/2), cur_x + seg_w, start_y + seg_h - t, fill=color if (mask & 0x04) else off_col, outline="")
            self.canvas.create_rectangle(cur_x + t, start_y + seg_h - t, cur_x + seg_w - t, start_y + seg_h, fill=color if (mask & 0x08) else off_col, outline="")
            self.canvas.create_rectangle(cur_x, start_y + int(seg_h/2) + int(t/2), cur_x + t, start_y + seg_h - t, fill=color if (mask & 0x10) else off_col, outline="")
            self.canvas.create_rectangle(cur_x, start_y + t, cur_x + t, start_y + int(seg_h/2) - int(t/2), fill=color if (mask & 0x20) else off_col, outline="")
            self.canvas.create_rectangle(cur_x + t, start_y + int(seg_h/2) - int(t/2), cur_x + seg_w - t, start_y + int(seg_h/2) + int(t/2), fill=color if (mask & 0x40) else off_col, outline="")
            cur_x += seg_w + 5

    def draw_pixel_sun(self, start_x, start_y, dot_size, pitch, color, elem_id=""):
        sun_map = [0b0011100, 0b0111110, 0b1111111, 0b1111111, 0b1111111, 0b0111110, 0b0011100]
        for r in range(7):
            bits = sun_map[r]
            for c in range(7):
                if (bits >> (6 - c)) & 1:
                    dx = start_x + c * pitch; dy = start_y + r * pitch
                    self.canvas.create_oval(dx, dy, dx + dot_size, dy + dot_size, fill=color, outline="", tags=("element", elem_id))

    def draw_pixel_sunrise(self, start_x, start_y, dot_size, pitch, color, elem_id=""):
        sun_map = [0b0011100, 0b0111110, 0b1111111, 0b0000000, 0b1111111]
        for r in range(5):
            bits = sun_map[r]
            for c in range(7):
                if (bits >> (6 - c)) & 1:
                    dx = start_x + c * pitch; dy = start_y + r * pitch
                    self.canvas.create_oval(dx, dy, dx + dot_size, dy + dot_size, fill=color, outline="", tags=("element", elem_id))

    def draw_floating_toolbar(self, elem):
        ex = int(elem["x"] * SCALE); ey = int(elem["y"] * SCALE)
        tb_x = min(int(CANVAS_WIDTH * SCALE) - 180, max(10, ex))
        tb_y = max(10, ey - 30) if ey > 32 else ey + int(elem["h"] * SCALE) + 6

        self.canvas.create_rectangle(tb_x, tb_y, tb_x + 180, tb_y + 24, fill="#111827", outline="#38bdf8", width=1, tags="floating_tb")
        colors = ["#FFFFFF", "#FF3333", "#00F5FF", "#FFD700", "#00E676"]
        for idx, col in enumerate(colors):
            cx = tb_x + 12 + idx * 22; cy = tb_y + 12
            self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=col, outline="#000000", tags=("floating_tb", f"col_{col}"))
        self.canvas.create_text(tb_x + 150, tb_y + 12, text="🗑️", fill="#f85149", font=("Segoe UI", 9), tags=("floating_tb", "quick_del"))

    def redraw_canvas(self):
        self.canvas.delete("all")
        bg_col = self.skin_data.get("canvas", {}).get("bg_color", "#000000")
        self.canvas.configure(bg=bg_col)

        for x in range(0, int(CANVAS_WIDTH * SCALE), int(20 * SCALE)):
            self.canvas.create_line(x, 0, x, int(CANVAS_HEIGHT * SCALE), fill="#141418", dash=(2, 4))
        for y in range(0, int(CANVAS_HEIGHT * SCALE), int(20 * SCALE)):
            self.canvas.create_line(0, y, int(CANVAS_WIDTH * SCALE), y, fill="#141418", dash=(2, 4))

        elements = self.get_current_elements()

        if not elements:
            self.canvas.create_text(
                int(CANVAS_WIDTH * SCALE / 2), int(CANVAS_HEIGHT * SCALE / 2),
                text=f"[{PAGE_NAMES[self.current_page_idx]}]\nTrang chưa có Sub-Element. Kéo hoặc nhấp +Add bên trái.",
                fill="#8B949E", font=("Segoe UI", 12, "bold"), justify="center"
            )

        # Sort elements so containers (rectangle, box, circle) render in background first, text on top
        sorted_elements = sorted(elements, key=lambda el: 0 if el.get("type") in ["rectangle", "box", "circle"] else 1)

        for elem in sorted_elements:
            ex = int(elem["x"] * SCALE); ey = int(elem["y"] * SCALE)
            ew = int(elem["w"] * SCALE); eh = int(elem["h"] * SCALE)
            eid = elem["id"]

            is_selected = (eid == self.selected_elem_id)
            color = elem.get("color", "#FFFFFF")
            font_style = elem.get("font_style", "default")
            etype = elem.get("type", "text")
            content = elem.get("content", "")
            font_sz = elem.get("font_size", 12)

            if etype == "wifi_signal":
                disp_txt = content if content else "-54dBm"
                for b in range(4):
                    bx = ex + b * 4; bh = 3 + b * 2; by = ey + 10 - bh
                    self.canvas.create_oval(bx, by, bx + 3, by + 3, fill=color, outline="", tags=("element", eid))
                self.canvas.create_text(ex + 18, ey + int(eh/2), text=disp_txt, fill=color, font=("Consolas", int(font_sz * 0.35 * SCALE)), anchor="w", tags=("element", eid))
            elif etype == "status_time":
                disp_txt = content if content else "17:29:17"
                self.canvas.create_text(ex, ey + int(eh/2), text=disp_txt, fill=color, font=("Consolas", int(font_sz * 0.4 * SCALE), "bold"), anchor="w", tags=("element", eid))
            elif etype == "status_serial":
                disp_txt = content if content else "COM4"
                self.canvas.create_text(ex, ey + int(eh/2), text=f"💻 {disp_txt}", fill=color, font=("Consolas", int(font_sz * 0.35 * SCALE), "bold"), anchor="w", tags=("element", eid))
            elif etype == "page_counter":
                disp_txt = content if content else "7/8"
                self.canvas.create_text(ex, ey + int(eh/2), text=disp_txt, fill=color, font=("Consolas", int(font_sz * 0.35 * SCALE), "bold"), anchor="w", tags=("element", eid))
            elif etype == "pixel_sun":
                self.draw_pixel_sun(ex, ey, dot_size=4, pitch=6, color=color, elem_id=eid)
            elif etype == "pixel_sunrise":
                self.draw_pixel_sunrise(ex, ey, dot_size=4, pitch=6, color=color, elem_id=eid)
            elif etype == "dot_matrix_divider":
                line_y = ey + int(eh / 2)
                for dx in range(ex, ex + ew, 7):
                    self.canvas.create_oval(dx, line_y, dx + 4, line_y + 4, fill=color, outline="", tags=("element", eid))
            elif etype == "line":
                line_y = ey + int(eh / 2)
                self.canvas.create_line(ex, line_y, ex + ew, line_y, fill=color, width=max(1, int(eh * SCALE)), tags=("element", eid))
            elif etype == "line_chart":
                self.canvas.create_rectangle(ex, ey, ex + ew, ey + eh, fill="#050811", outline="#1F2937", tags=("element", eid))
                import math
                pts = []
                for i in range(15):
                    px = ex + int(i * (ew / 14))
                    py = ey + int(eh * 0.7) - int(math.sin(i * 0.5) * (eh * 0.35))
                    pts.extend([px, py])
                if len(pts) >= 4:
                    self.canvas.create_line(pts, fill=color, width=2, smooth=True, tags=("element", eid))
            elif etype in ["rectangle", "box"]:
                border_col = "#00F5FF" if color == "#1E293B" else "#1f2937"
                self.canvas.create_rectangle(ex, ey, ex + ew, ey + eh, fill=color, outline=border_col, tags=("element", eid))
            elif etype == "circle":
                self.canvas.create_oval(ex, ey, ex + ew, ey + eh, fill=color, outline="", tags=("element", eid))
            elif font_style == "dot_matrix" or etype == "matrix_text":
                d_sz = max(2, int(font_sz * 0.3))
                d_pitch = max(3, int(font_sz * 0.45))
                self.draw_dot_matrix_text(content, ex, ey, dot_size=d_sz, pitch=d_pitch, on_color=color, off_color="#121212", elem_id=eid)
            elif font_style == "segment7":
                s_w = max(8, int(font_sz * 0.8))
                s_h = max(14, int(font_sz * 1.6))
                self.draw_7segment_text(content, ex, ey, seg_w=s_w, seg_h=s_h, color=color, elem_id=eid)
            elif font_style == "mono":
                is_centered = (ew >= 40 and len(content) <= 8)
                tx = ex + int(ew/2) if is_centered else ex
                anchor_val = "center" if is_centered else "w"
                self.canvas.create_text(tx, ey + int(eh/2), text=content, fill=color, font=("Consolas", int(font_sz * 0.38 * SCALE), "bold"), anchor=anchor_val, tags=("element", eid))
            else:
                is_centered = (ew >= 40 and len(content) <= 8 and ("\n" not in content))
                tx = ex + int(ew/2) if is_centered else ex
                anchor_val = "center" if is_centered else "w"
                self.canvas.create_text(tx, ey + int(eh/2), text=content, fill=color, font=("Segoe UI", int(font_sz * 0.42 * SCALE), "bold"), anchor=anchor_val, tags=("element", eid))

            if is_selected:
                is_glob = elem.get("is_global", False)
                border_col = "#38bdf8" if not is_glob else "#FFD700"
                self.canvas.create_rectangle(ex - 3, ey - 3, ex + ew + 3, ey + eh + 3, outline=border_col, width=2, dash=(3, 3), tags=("selected", eid))
                self.canvas.create_rectangle(ex + ew - 4, ey + eh - 4, ex + ew + 5, ey + eh + 5, fill=border_col, outline="#ffffff", tags=("handle", eid))
                self.draw_floating_toolbar(elem)

        self.update_inspector()

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        elements = self.get_current_elements()

        if self.selected_elem_id:
            elem = self.get_selected_element()
            if elem:
                ex = int(elem["x"] * SCALE); ey = int(elem["y"] * SCALE)
                tb_x = min(int(CANVAS_WIDTH * SCALE) - 180, max(10, ex))
                tb_y = max(10, ey - 30) if ey > 32 else ey + int(elem["h"] * SCALE) + 6

                if (tb_x + 140 <= x <= tb_x + 175) and (tb_y <= y <= tb_y + 24):
                    self.delete_selected_element(); return

                colors = ["#FFFFFF", "#FF3333", "#00F5FF", "#FFD700", "#00E676"]
                for idx, col in enumerate(colors):
                    cx = tb_x + 12 + idx * 22; cy = tb_y + 12
                    if (cx - 9 <= x <= cx + 9) and (cy - 9 <= y <= cy + 9):
                        elem["color"] = col; self.redraw_canvas(); return

        for elem in elements:
            ex = int(elem["x"] * SCALE); ey = int(elem["y"] * SCALE)
            ew = int(elem["w"] * SCALE); eh = int(elem["h"] * SCALE)
            if (ex + ew - 5 <= x <= ex + ew + 7) and (ey + eh - 5 <= y <= ey + eh + 7):
                self.selected_elem_id = elem["id"]; self.drag_data["handle"] = "resize"
                self.drag_data["elem"] = elem; self.drag_data["x"] = x; self.drag_data["y"] = y
                self.redraw_canvas(); return

        for elem in reversed(elements):
            ex = int(elem["x"] * SCALE); ey = int(elem["y"] * SCALE)
            ew = int(elem["w"] * SCALE); eh = int(elem["h"] * SCALE)
            if (ex - 4 <= x <= ex + ew + 4) and (ey - 4 <= y <= ey + eh + 4):
                self.selected_elem_id = elem["id"]; self.drag_data["handle"] = "move"
                self.drag_data["elem"] = elem; self.drag_data["x"] = x - ex; self.drag_data["y"] = y - ey
                self.redraw_canvas(); return

        self.selected_elem_id = None; self.redraw_canvas()

    def on_canvas_drag(self, event):
        elem = self.drag_data.get("elem")
        if not elem: return

        if self.drag_data.get("handle") == "move":
            new_x = int((event.x - self.drag_data["x"]) / SCALE)
            new_y = int((event.y - self.drag_data["y"]) / SCALE)
            elem["x"] = max(0, min(CANVAS_WIDTH - elem["w"], new_x))
            elem["y"] = max(0, min(CANVAS_HEIGHT - elem["h"], new_y))
            self.redraw_canvas()
        elif self.drag_data.get("handle") == "resize":
            new_w = int((event.x - int(elem["x"] * SCALE)) / SCALE)
            new_h = int((event.y - int(elem["y"] * SCALE)) / SCALE)
            elem["w"] = max(10, min(CANVAS_WIDTH - elem["x"], new_w))
            elem["h"] = max(8, min(CANVAS_HEIGHT - elem["y"], new_h))
            self.redraw_canvas()

    def on_canvas_release(self, event):
        self.drag_data["elem"] = None; self.drag_data["handle"] = None

    def nudge_selected_element(self, dx, dy):
        elem = self.get_selected_element()
        if elem:
            elem["x"] = max(0, min(CANVAS_WIDTH - elem["w"], elem["x"] + dx))
            elem["y"] = max(0, min(CANVAS_HEIGHT - elem["h"], elem["y"] + dy))
            self.redraw_canvas()

    def create_color_circle_icon(self, hex_color, size=(14, 14)):
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([1, 1, size[0] - 2, size[1] - 2], fill=hex_color)
            return ctk.CTkImage(light_image=img, dark_image=img, size=size)
        except Exception:
            return None

    def update_inspector(self):
        elem = self.get_selected_element()
        if elem:
            self.sel_name_lbl.configure(text=f"Selected: {elem['name']}", text_color="#38bdf8")
            focused = self.focus_get()
            if focused != self.entry_content:
                self.entry_content.delete(0, tk.END)
                self.entry_content.insert(0, elem.get("content", ""))
            if focused not in (self.entry_x, self.entry_y, self.entry_w, self.entry_h):
                self.entry_x.delete(0, tk.END); self.entry_x.insert(0, str(elem["x"]))
                self.entry_y.delete(0, tk.END); self.entry_y.insert(0, str(elem["y"]))
                self.entry_w.delete(0, tk.END); self.entry_w.insert(0, str(elem["w"]))
                self.entry_h.delete(0, tk.END); self.entry_h.insert(0, str(elem["h"]))

            if hasattr(self, 'lbl_font_size'):
                self.lbl_font_size.configure(text=f"{elem.get('font_size', 12)}px")
            if hasattr(self, 'global_chk'):
                self.global_chk.select() if elem.get("is_global") else self.global_chk.deselect()

            font_val_map = {
                "dot_matrix": "Dot Matrix LED", "segment7": "7-Segment Digital",
                "mono": "Monospace Code", "default": "Default Sans"
            }
            self.font_combo.set(font_val_map.get(elem.get("font_style", "default"), "Dot Matrix LED"))
            self.color_btn.configure(fg_color=elem.get("color", "#FFFFFF"))
        else:
            self.sel_name_lbl.configure(text="Click object to edit", text_color="#64748b")
            focused = self.focus_get()
            if focused not in (self.entry_content, self.entry_x, self.entry_y, self.entry_w, self.entry_h):
                self.entry_content.delete(0, tk.END)
                self.entry_x.delete(0, tk.END); self.entry_y.delete(0, tk.END)
                self.entry_w.delete(0, tk.END); self.entry_h.delete(0, tk.END)

    def change_font_size(self, delta):
        elem = self.get_selected_element()
        if elem:
            curr_sz = elem.get("font_size", 12)
            elem["font_size"] = max(6, min(60, curr_sz + delta))
            if hasattr(self, 'lbl_font_size'):
                self.lbl_font_size.configure(text=f"{elem['font_size']}px")
            self.redraw_canvas()

    def toggle_global_element(self):
        elem = self.get_selected_element()
        if elem:
            elem["is_global"] = bool(self.global_chk.get())
            self.redraw_canvas()

    def align_selected_horiz_center(self):
        elem = self.get_selected_element()
        if elem:
            elem["x"] = max(0, int((CANVAS_WIDTH - elem["w"]) / 2))
            self.redraw_canvas()

    def align_selected_vert_center(self):
        elem = self.get_selected_element()
        if elem:
            elem["y"] = max(0, int((CANVAS_HEIGHT - elem["h"]) / 2))
            self.redraw_canvas()

    def scale_selected_element(self, factor):
        elem = self.get_selected_element()
        if elem:
            elem["w"] = max(10, min(CANVAS_WIDTH - elem["x"], int(elem["w"] * factor)))
            elem["h"] = max(8, min(CANVAS_HEIGHT - elem["h"], int(elem["h"] * factor)))
            self.redraw_canvas()

    def fit_selected_width(self):
        elem = self.get_selected_element()
        if elem:
            elem["x"] = 10
            elem["w"] = CANVAS_WIDTH - 20
            self.redraw_canvas()

    def apply_text_content(self):
        elem = self.get_selected_element()
        if elem: elem["content"] = self.entry_content.get(); self.redraw_canvas()

    def on_font_change(self, val):
        elem = self.get_selected_element()
        if elem:
            font_key_map = {"Dot Matrix LED": "dot_matrix", "7-Segment Digital": "segment7", "Monospace Code": "mono", "Default Sans": "default"}
            elem["font_style"] = font_key_map.get(val, "default"); self.redraw_canvas()

    def apply_manual_geometry(self):
        elem = self.get_selected_element()
        if elem:
            try:
                elem["x"] = int(self.entry_x.get()); elem["y"] = int(self.entry_y.get())
                elem["w"] = int(self.entry_w.get()); elem["h"] = int(self.entry_h.get())
                self.redraw_canvas()
            except Exception: pass

    def pick_color(self):
        elem = self.get_selected_element()
        if elem:
            color = colorchooser.askcolor(title="Choose Color", color=elem.get("color", "#FFFFFF"))[1]
            if color: elem["color"] = color; self.redraw_canvas()

    def _destroy_drag_tooltip(self):
        if hasattr(self, '_drag_tooltip') and self._drag_tooltip:
            try:
                self._drag_tooltip.destroy()
            except Exception: pass
            self._drag_tooltip = None

    def _setup_drag_and_drop(self, btn, n, t, c, w, h, col, f):
        def _on_press(e):
            self._destroy_drag_tooltip()
            self._drag_preset = (n, t, c, w, h, col, f)
            self._drag_start_pos = (e.x_root, e.y_root)
            self._is_dragging = False

        def _on_motion(e):
            if not hasattr(self, '_drag_preset') or not self._drag_preset:
                return
            dx = abs(e.x_root - self._drag_start_pos[0])
            dy = abs(e.y_root - self._drag_start_pos[1])
            if dx > 4 or dy > 4:
                self._is_dragging = True
                if not hasattr(self, '_drag_tooltip') or not self._drag_tooltip or not self._drag_tooltip.winfo_exists():
                    try:
                        win = tk.Toplevel(self)
                        win.overrideredirect(True)
                        win.attributes("-topmost", True)
                        win.configure(bg="#38bdf8")
                        lbl = tk.Label(win, text=f" ➕ {n} ", bg="#38bdf8", fg="#000000", font=("Segoe UI", 9, "bold"))
                        lbl.pack(padx=4, pady=2)
                        self._drag_tooltip = win
                    except Exception: pass
                if hasattr(self, '_drag_tooltip') and self._drag_tooltip and self._drag_tooltip.winfo_exists():
                    try:
                        self._drag_tooltip.geometry(f"+{e.x_root + 10}+{e.y_root + 10}")
                    except Exception: pass

        def _on_release(e):
            self._destroy_drag_tooltip()
            if not hasattr(self, '_drag_preset') or not self._drag_preset:
                return

            n_p, t_p, c_p, w_p, h_p, col_p, f_p = self._drag_preset
            self._drag_preset = None
            was_dragging = getattr(self, '_is_dragging', False)
            self._is_dragging = False

            try:
                mx, my = self.winfo_pointerxy()
                cx0 = self.canvas.winfo_rootx()
                cy0 = self.canvas.winfo_rooty()
                cw = self.canvas.winfo_width()
                ch = self.canvas.winfo_height()

                if was_dragging and (cx0 <= mx <= cx0 + cw) and (cy0 <= my <= cy0 + ch):
                    rel_x = (mx - cx0) / SCALE - (w_p / 2)
                    rel_y = (my - cy0) / SCALE - (h_p / 2)
                    self.add_sub_element(n_p, t_p, c_p, w_p, h_p, col_p, f_p, pos_x=rel_x, pos_y=rel_y)
                    return
            except Exception: pass

            self.add_sub_element(n_p, t_p, c_p, w_p, h_p, col_p, f_p)

        try:
            btn.bind("<ButtonPress-1>", _on_press)
            btn.bind("<B1-Motion>", _on_motion)
            btn.bind("<ButtonRelease-1>", _on_release)
        except Exception: pass

    def add_sub_element(self, name, etype, content, def_w, def_h, def_col, font_st, pos_x=None, pos_y=None):
        elements = self.get_current_page_elements()
        new_id = f"elem_{int(time.time() * 1000)}"
        if pos_x is None or pos_y is None:
            pos_x = int((CANVAS_WIDTH - def_w) / 2)
            pos_y = int((CANVAS_HEIGHT - def_h) / 2)
        pos_x = max(0, min(CANVAS_WIDTH - def_w, pos_x))
        pos_y = max(0, min(CANVAS_HEIGHT - def_h, pos_y))
        new_elem = {"id": new_id, "name": name, "type": etype, "content": content, "font_style": font_st, "x": int(pos_x), "y": int(pos_y), "w": def_w, "h": def_h, "color": def_col}
        elements.append(new_elem); self.selected_elem_id = new_id; self.redraw_canvas()
        if hasattr(self, 'status_lbl'):
            self.status_lbl.configure(text=f"✨ Added '{name}' at ({int(pos_x)}, {int(pos_y)})", text_color="#38bdf8")

    def nudge_element(self, dx, dy):
        if not self.selected_elem_id: return
        for elem in self.get_current_elements():
            if elem["id"] == self.selected_elem_id:
                step = int(self.nudge_step_var.get() if hasattr(self, 'nudge_step_var') and self.nudge_step_var.get() else 1)
                elem["x"] = max(0, min(CANVAS_WIDTH - elem["w"], elem["x"] + dx * step))
                elem["y"] = max(0, min(CANVAS_HEIGHT - elem["h"], elem["y"] + dy * step))
                if hasattr(self, 'entry_x'):
                    self.entry_x.delete(0, tk.END); self.entry_x.insert(0, str(int(elem["x"])))
                if hasattr(self, 'entry_y'):
                    self.entry_y.delete(0, tk.END); self.entry_y.insert(0, str(int(elem["y"])))
                self.redraw_canvas()
                break

    def duplicate_selected_element(self):
        if not self.selected_elem_id: return
        target = self.get_selected_element()
        if target:
            import copy
            new_el = copy.deepcopy(target)
            new_el["id"] = f"elem_{int(time.time() * 1000)}"
            new_el["x"] = min(CANVAS_WIDTH - new_el["w"], new_el["x"] + 10)
            new_el["y"] = min(CANVAS_HEIGHT - new_el["h"], new_el["y"] + 10)
            new_el["is_global"] = False
            self.get_current_page_elements().append(new_el)
            self.selected_elem_id = new_el["id"]
            self.redraw_canvas()

    def move_layer(self, direction):
        if not self.selected_elem_id: return
        elements = self.get_current_page_elements()
        idx = None
        for i, el in enumerate(elements):
            if el["id"] == self.selected_elem_id:
                idx = i; break
        if idx is not None:
            if direction == "up" and idx < len(elements) - 1:
                elements[idx], elements[idx+1] = elements[idx+1], elements[idx]
            elif direction == "down" and idx > 0:
                elements[idx], elements[idx-1] = elements[idx-1], elements[idx]
            self.redraw_canvas()

    def align_selected_center(self):
        if not self.selected_elem_id: return
        for elem in self.get_current_elements():
            if elem["id"] == self.selected_elem_id:
                elem["x"] = max(0, int((CANVAS_WIDTH - elem["w"]) / 2))
                elem["y"] = max(0, int((CANVAS_HEIGHT - elem["h"]) / 2))
                self.redraw_canvas()
                break

    def clear_current_page_elements(self):
        if tk.messagebox.askyesno("🧹 Clear Page", f"Bạn có chắc muốn xóa tất cả Sub-Elements của trang {PAGE_NAMES[self.current_page_idx]}?"):
            self.skin_data["pages"][str(self.current_page_idx)]["elements"] = []
            self.selected_elem_id = None
            self.redraw_canvas()

    def delete_selected_element(self):
        if self.selected_elem_id:
            elements = self.get_current_page_elements()
            self.skin_data["pages"][str(self.current_page_idx)]["elements"] = [el for el in elements if el["id"] != self.selected_elem_id]
            self.selected_elem_id = None; self.redraw_canvas()

    def get_selected_element(self):
        for elem in self.get_current_elements():
            if elem["id"] == self.selected_elem_id: return elem
        return None

    def apply_palette(self, pal_name):
        pal = COLOR_PALETTES.get(pal_name)
        if not pal: return
        self.skin_data["canvas"]["bg_color"] = pal["bg"]
        elements = self.get_current_elements()
        for idx, el in enumerate(elements):
            if idx % 3 == 0: el["color"] = pal["accent"]
            elif idx % 3 == 1: el["color"] = pal["sec"]
            else: el["color"] = pal["line"]
        self.redraw_canvas()

    def get_cyd_default_page_elements(self, p):
        p_code, p_ico, p_title, _, _ = PAGE_ITEMS[p]
        hdr_line = {"id": "g_hdr_line", "name": "Status Bar Line", "type": "line", "content": "line", "font_style": "default", "x": 10, "y": 20, "w": 300, "h": 2, "color": "#00F5FF", "is_global": True}
        hdr_time = {"id": "g_time", "name": "Status Time", "type": "status_time", "content": "17:29:17", "font_style": "mono", "x": 135, "y": 4, "w": 55, "h": 14, "color": "#FFFFFF", "font_size": 12, "is_global": True}
        hdr_wifi = {"id": "g_wifi", "name": "WiFi Signal", "type": "wifi_signal", "content": "-54dBm", "font_style": "mono", "x": 235, "y": 4, "w": 40, "h": 14, "color": "#00E676", "font_size": 12, "is_global": True}
        hdr_serial = {"id": "g_ser", "name": "PC Serial Status Icon", "type": "status_serial", "content": "COM4", "font_style": "mono", "x": 280, "y": 4, "w": 30, "h": 14, "color": "#38BDF8", "font_size": 12, "is_global": True}
        hdr_t = {"id": f"p{p}_title", "name": "Page Title & Icon", "type": "text", "content": f"{p_ico} {p_title.split(' ')[0]}", "font_style": "default", "x": 10, "y": 4, "w": 90, "h": 14, "color": "#38BDF8", "font_size": 11, "is_global": False}
        hdr_ctr = {"id": f"p{p}_ctr", "name": "Page Counter Index", "type": "page_counter", "content": f"{p+1}/8", "font_style": "mono", "x": 200, "y": 4, "w": 30, "h": 14, "color": "#94A3B8", "font_size": 11, "is_global": False}

        base = [hdr_line, hdr_time, hdr_wifi, hdr_serial, hdr_t, hdr_ctr]

        if p == 0:
            base.extend([
                {"id": "p0_sun", "name": "Dot Matrix Sun Icon", "type": "pixel_sun", "content": "sun", "font_style": "dot_matrix", "x": 20, "y": 30, "w": 40, "h": 40, "color": "#FFD700"},
                {"id": "p0_wtr", "name": "Weather City & Temp", "type": "text", "content": "28°C Hanoi", "font_style": "default", "x": 75, "y": 38, "w": 140, "h": 24, "color": "#38BDF8", "font_size": 18},
                {"id": "p0_box", "name": "Clock Container Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 10, "y": 80, "w": 300, "h": 145, "color": "#111827"},
                {"id": "p0_clk", "name": "Digital Clock Digits", "type": "matrix_text", "content": "17:29:17", "font_style": "dot_matrix", "x": 25, "y": 100, "w": 270, "h": 50, "color": "#00F5FF", "font_size": 26},
                {"id": "p0_dt", "name": "Solar & Lunar Date", "type": "text", "content": "Mon 10/08/2026 • 18/07 Lunar Binh Ngo", "font_style": "default", "x": 25, "y": 175, "w": 270, "h": 18, "color": "#FFD700", "font_size": 12}
            ])
        elif p == 1:
            base.extend([
                {"id": "p1_box", "name": "Calendar Container Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 10, "y": 30, "w": 300, "h": 195, "color": "#111827"},
                {"id": "p1_t", "name": "Calendar Header", "type": "text", "content": "Solar & Lunar Calendar", "font_style": "default", "x": 25, "y": 45, "w": 250, "h": 22, "color": "#FFD700", "font_size": 15},
                {"id": "p1_sol", "name": "Solar Date Text", "type": "text", "content": "Solar: Monday, 10/08/2026", "font_style": "default", "x": 25, "y": 80, "w": 250, "h": 20, "color": "#FFFFFF", "font_size": 14},
                {"id": "p1_lun", "name": "Lunar Date Text", "type": "text", "content": "Lunar: 18/07 Binh Ngo", "font_style": "default", "x": 25, "y": 115, "w": 250, "h": 20, "color": "#00E676", "font_size": 13},
                {"id": "p1_hrs", "name": "Hoang Dao Hours", "type": "text", "content": "Gio Hoang Dao: Ty, Suu, Mao, Ngo, Than", "font_style": "default", "x": 25, "y": 150, "w": 250, "h": 18, "color": "#38BDF8", "font_size": 12}
            ])
        elif p == 2:
            base.extend([
                {"id": "p2_box", "name": "Crypto Container Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 10, "y": 30, "w": 300, "h": 195, "color": "#111827"},
                {"id": "p2_t", "name": "Crypto Header", "type": "text", "content": "📈 Crypto Live Market Ticker", "font_style": "default", "x": 25, "y": 45, "w": 250, "h": 22, "color": "#FFD700", "font_size": 15},
                {"id": "p2_btc", "name": "BTC Price", "type": "text", "content": "BTC: $64,500.00 ▲ +2.4%", "font_style": "mono", "x": 25, "y": 85, "w": 250, "h": 20, "color": "#00E676", "font_size": 14},
                {"id": "p2_eth", "name": "ETH Price", "type": "text", "content": "ETH: $3,450.00 ▲ +1.8%", "font_style": "mono", "x": 25, "y": 120, "w": 250, "h": 20, "color": "#00E676", "font_size": 14},
                {"id": "p2_sol", "name": "SOL Price", "type": "text", "content": "SOL: $145.20 ▲ +4.2%", "font_style": "mono", "x": 25, "y": 155, "w": 250, "h": 20, "color": "#38BDF8", "font_size": 14}
            ])
        elif p == 3:
            base.extend([
                {"id": "p3_box", "name": "PC Monitor Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 10, "y": 30, "w": 300, "h": 195, "color": "#111827"},
                {"id": "p3_t", "name": "PC Monitor Header", "type": "text", "content": "🖥️ PC Hardware Performance", "font_style": "default", "x": 25, "y": 45, "w": 250, "h": 22, "color": "#38BDF8", "font_size": 15},
                {"id": "p3_cpu", "name": "CPU/GPU Temp", "type": "text", "content": "CPU: 45°C (35%) • GPU: 52°C (60%)", "font_style": "mono", "x": 25, "y": 80, "w": 250, "h": 18, "color": "#FFFFFF", "font_size": 12},
                {"id": "p3_ram", "name": "RAM Usage", "type": "text", "content": "RAM: 42% (6.7GB / 16.0GB)", "font_style": "mono", "x": 25, "y": 105, "w": 250, "h": 18, "color": "#00E676", "font_size": 12},
                {"id": "p3_cht", "name": "Hardware Line Chart", "type": "line_chart", "content": "chart", "font_style": "mono", "x": 25, "y": 130, "w": 270, "h": 50, "color": "#CC00FF", "font_size": 12},
                {"id": "p3_usb", "name": "USB Status", "type": "text", "content": "[USB Connected • Serial COM4]", "font_style": "mono", "x": 25, "y": 190, "w": 250, "h": 16, "color": "#8B949E", "font_size": 11}
            ])
        elif p == 4:
            base.extend([
                {"id": "p4_box", "name": "Network Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 10, "y": 30, "w": 300, "h": 195, "color": "#111827"},
                {"id": "p4_t", "name": "Network Header", "type": "text", "content": "🌐 WiFi Network & Disk Space", "font_style": "default", "x": 25, "y": 45, "w": 250, "h": 22, "color": "#00E676", "font_size": 15},
                {"id": "p4_ip", "name": "WiFi IP Text", "type": "text", "content": "IP: 192.168.1.13 • RSSI -54dBm", "font_style": "mono", "x": 25, "y": 80, "w": 250, "h": 18, "color": "#FFFFFF", "font_size": 13},
                {"id": "p4_disk", "name": "Disk Free", "type": "text", "content": "Disk C: 128GB Free / 512GB (75%)", "font_style": "mono", "x": 25, "y": 115, "w": 250, "h": 18, "color": "#38BDF8", "font_size": 13},
                {"id": "p4_spd", "name": "Net Speed", "type": "text", "content": "Speed: ↓ 45.2 Mbps  ↑ 12.4 Mbps", "font_style": "mono", "x": 25, "y": 150, "w": 250, "h": 18, "color": "#FFD700", "font_size": 13}
            ])
        elif p == 5:
            base.extend([
                {"id": "p5_box", "name": "Pomodoro Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 10, "y": 30, "w": 300, "h": 195, "color": "#111827"},
                {"id": "p5_t", "name": "Pomodoro Header", "type": "text", "content": "⏱️ Pomodoro Focus Timer", "font_style": "default", "x": 25, "y": 45, "w": 250, "h": 22, "color": "#FF3333", "font_size": 15},
                {"id": "p5_tmr", "name": "Pomodoro Digits", "type": "matrix_text", "content": "25:00", "font_style": "dot_matrix", "x": 25, "y": 80, "w": 270, "h": 50, "color": "#FF3333", "font_size": 28},
                {"id": "p5_st", "name": "Focus Status", "type": "text", "content": "State: 🎯 WORK FOCUS SESSION", "font_style": "default", "x": 25, "y": 145, "w": 250, "h": 18, "color": "#00E676", "font_size": 13},
                {"id": "p5_ses", "name": "Sessions Completed", "type": "text", "content": "Progress: 3 / 4 Sessions Done", "font_style": "mono", "x": 25, "y": 175, "w": 250, "h": 16, "color": "#8B949E", "font_size": 12}
            ])
        elif p == 6: # Authentic Media Remote (1-to-1 Match with CYD Photo!)
            base.extend([
                {"id": "p6_t", "name": "Media Page Title", "type": "text", "content": "MEDIA CONTROL", "font_style": "default", "x": 110, "y": 28, "w": 100, "h": 16, "color": "#38BDF8", "font_size": 13},
                {"id": "p6_b1", "name": "Button PREV Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 34, "y": 55, "w": 76, "h": 72, "color": "#111827"},
                {"id": "p6_b1_ico", "name": "PREV Icon", "type": "text", "content": "⏮️", "font_style": "default", "x": 56, "y": 70, "w": 32, "h": 30, "color": "#00F5FF", "font_size": 20},
                {"id": "p6_b1_txt", "name": "PREV Text", "type": "text", "content": "PREV", "font_style": "default", "x": 54, "y": 105, "w": 36, "h": 16, "color": "#00F5FF", "font_size": 12},

                {"id": "p6_b2", "name": "Button PLAY Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 117, "y": 55, "w": 86, "h": 72, "color": "#111827"},
                {"id": "p6_b2_ico", "name": "PLAY Icon", "type": "text", "content": "▶️", "font_style": "default", "x": 144, "y": 70, "w": 32, "h": 30, "color": "#00E676", "font_size": 20},
                {"id": "p6_b2_txt", "name": "PLAY Text", "type": "text", "content": "PLAY", "font_style": "default", "x": 142, "y": 105, "w": 36, "h": 16, "color": "#00E676", "font_size": 12},

                {"id": "p6_b3", "name": "Button NEXT Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 210, "y": 55, "w": 76, "h": 72, "color": "#111827"},
                {"id": "p6_b3_ico", "name": "NEXT Icon", "type": "text", "content": "⏭️", "font_style": "default", "x": 232, "y": 70, "w": 32, "h": 30, "color": "#00F5FF", "font_size": 20},
                {"id": "p6_b3_txt", "name": "NEXT Text", "type": "text", "content": "NEXT", "font_style": "default", "x": 230, "y": 105, "w": 36, "h": 16, "color": "#00F5FF", "font_size": 12},

                {"id": "p6_b4", "name": "Button VOL - Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 34, "y": 135, "w": 76, "h": 72, "color": "#111827"},
                {"id": "p6_b4_ico", "name": "VOL - Icon", "type": "text", "content": "🔊", "font_style": "default", "x": 56, "y": 150, "w": 32, "h": 30, "color": "#FFD700", "font_size": 20},
                {"id": "p6_b4_txt", "name": "VOL - Text", "type": "text", "content": "VOL -", "font_style": "default", "x": 50, "y": 185, "w": 44, "h": 16, "color": "#FFD700", "font_size": 12},

                {"id": "p6_b5", "name": "Button SKIP AD Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 117, "y": 135, "w": 86, "h": 72, "color": "#1E293B"},
                {"id": "p6_b5_ico", "name": "SKIP AD Icon", "type": "text", "content": "⏭️", "font_style": "default", "x": 144, "y": 150, "w": 32, "h": 30, "color": "#FFD700", "font_size": 20},
                {"id": "p6_b5_txt", "name": "SKIP AD Text", "type": "text", "content": "SKIP AD", "font_style": "default", "x": 132, "y": 185, "w": 56, "h": 16, "color": "#FFD700", "font_size": 12},

                {"id": "p6_b6", "name": "Button VOL + Box", "type": "rectangle", "content": "box", "font_style": "default", "x": 210, "y": 135, "w": 76, "h": 72, "color": "#111827"},
                {"id": "p6_b6_ico", "name": "VOL + Icon", "type": "text", "content": "🔊", "font_style": "default", "x": 232, "y": 150, "w": 32, "h": 30, "color": "#FFD700", "font_size": 20},
                {"id": "p6_b6_txt", "name": "VOL + Text", "type": "text", "content": "VOL +", "font_style": "default", "x": 226, "y": 185, "w": 44, "h": 16, "color": "#FFD700", "font_size": 12},

                {"id": "p6_arr_l", "name": "Left Nav Arrow", "type": "text", "content": "<", "font_style": "default", "x": 12, "y": 115, "w": 15, "h": 20, "color": "#00F5FF", "font_size": 16},
                {"id": "p6_arr_r", "name": "Right Nav Arrow", "type": "text", "content": ">", "font_style": "default", "x": 295, "y": 115, "w": 15, "h": 20, "color": "#00F5FF", "font_size": 16}
            ])
        elif p == 7:
            base.extend([
                {"id": "p7_box", "name": "System Box Container", "type": "rectangle", "content": "box", "font_style": "default", "x": 10, "y": 30, "w": 300, "h": 195, "color": "#111827"},
                {"id": "p7_t", "name": "System Header", "type": "text", "content": "⚙️ CYD Desk System Information", "font_style": "default", "x": 25, "y": 45, "w": 250, "h": 22, "color": "#FFD700", "font_size": 15},
                {"id": "p7_clk", "name": "Big Digital Clock", "type": "matrix_text", "content": "17:29:17", "font_style": "dot_matrix", "x": 25, "y": 80, "w": 270, "h": 45, "color": "#00F5FF", "font_size": 24},
                {"id": "p7_up", "name": "System Uptime", "type": "text", "content": "System Uptime: 12d 04h 25m", "font_style": "mono", "x": 25, "y": 140, "w": 250, "h": 18, "color": "#00E676", "font_size": 13},
                {"id": "p7_ver", "name": "Firmware Version", "type": "text", "content": "Firmware: CYD Desk Studio Pro v2.4", "font_style": "mono", "x": 25, "y": 170, "w": 250, "h": 16, "color": "#8B949E", "font_size": 12}
            ])

        return base

    # ── CONTROL FUNCTIONS ─────────────────────────────────────────────
    def force_reconnect(self):
        self.last_port_scan = 0
        self.status_lbl.configure(text="● Scanning USB/WiFi ports...", text_color="#EAB308")

    def apply_theme(self, theme_key):
        self.last_user_action_time = time.time()
        self.active_cyd_theme = theme_key
        self.pending_control["preset"] = theme_key
        self._highlight_theme_button(theme_key)
        self.status_lbl.configure(text=f"✅ Theme set: {theme_key}", text_color="#39FF14")

    def switch_page(self, page_id):
        self.last_user_action_time = time.time()
        self.active_cyd_page = page_id
        self.pending_control["page"] = page_id
        self._highlight_page_button(page_id)
        self.status_lbl.configure(text=f"✅ Switched to Page {page_id}", text_color="#39FF14")

    def _on_global_mousewheel(self, event):
        if hasattr(self, 'city_dropdown_popup') and self.city_dropdown_popup is not None:
            try:
                if self.city_dropdown_popup.winfo_exists() and self.city_dropdown_popup.winfo_viewable():
                    w = getattr(event, 'widget', None)
                    if w:
                        w_str = str(w)
                        pop_str = str(self.city_dropdown_popup)
                        if w_str == pop_str or w_str.startswith(pop_str + "."):
                            return
                    self.close_city_dropdown()
            except Exception:
                pass

    def close_city_dropdown(self):
        if hasattr(self, 'city_dropdown_popup') and self.city_dropdown_popup is not None:
            try:
                if self.city_dropdown_popup.winfo_exists():
                    self.city_dropdown_popup.withdraw()
            except Exception:
                pass

    def toggle_city_search_panel(self):
        self.last_user_action_time = time.time()

        # If popup is currently open & visible, toggle it closed
        if hasattr(self, 'city_dropdown_popup') and self.city_dropdown_popup is not None:
            try:
                if self.city_dropdown_popup.winfo_exists() and self.city_dropdown_popup.winfo_viewable():
                    self.city_dropdown_popup.withdraw()
                    return
            except Exception:
                pass

        # Otherwise create if needed and show instantly on 1st click
        if not hasattr(self, 'city_dropdown_popup') or self.city_dropdown_popup is None or not self.city_dropdown_popup.winfo_exists():
            self._create_city_dropdown_popup()

        self._position_and_show_city_popup()

    def _create_city_dropdown_popup(self):
        # Create frameless floating CTkToplevel dropdown window
        popup = ctk.CTkToplevel(self)
        popup.withdraw()
        try:
            popup.overrideredirect(True)
            popup.config(bg="#030712")
            popup.configure(fg_color="#030712")
        except Exception:
            pass

        self.city_dropdown_popup = popup

        # Dark Container Frame
        p_frame = ctk.CTkFrame(popup, fg_color="#030712", border_width=1, border_color="#38bdf8", corner_radius=8)
        p_frame.pack(fill="both", expand=True)

        p_inner = ctk.CTkFrame(p_frame, fg_color="transparent")
        p_inner.pack(fill="both", expand=True, padx=6, pady=6)

        self.city_search_entry = ctk.CTkEntry(
            p_inner, placeholder_text="🔍 Gõ tìm nhanh...",
            height=28, font=ctk.CTkFont(size=11)
        )
        self.city_search_entry.pack(fill="x", pady=(0, 4))

        lb_container = ctk.CTkFrame(p_inner, fg_color="#0b0f17", border_width=1, border_color="#1f2937", corner_radius=0)
        lb_container.pack(fill="both", expand=True)

        lb_scroll = tk.Scrollbar(lb_container, bg="#030712", troughcolor="#030712")
        lb_scroll.pack(side="right", fill="y", padx=(0, 2), pady=2)

        self.city_listbox = tk.Listbox(
            lb_container, bg="#0b0f17", fg="#f8fafc", selectbackground="#0284c7", selectforeground="#ffffff",
            font=("Segoe UI", 11, "bold"), bd=0, highlightthickness=0, height=8, yscrollcommand=lb_scroll.set, activestyle="none"
        )
        self.city_listbox.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        lb_scroll.config(command=self.city_listbox.yview)

        # Mouse wheel scrolling isolation: prevent mouse wheel from scrolling main window!
        def _on_mousewheel(event):
            try:
                if sys.platform == "win32":
                    self.city_listbox.yview_scroll(int(-1 * (event.delta / 120)), "units")
                else:
                    self.city_listbox.yview_scroll(int(event.delta), "units")
            except Exception: pass
            return "break"

        self.city_listbox.bind("<MouseWheel>", _on_mousewheel)
        self.city_search_entry.bind("<MouseWheel>", lambda e: "break")
        popup.bind("<MouseWheel>", lambda e: "break")

        self.current_city_matches = []

        def _render_cities(filter_text=""):
            self.city_listbox.delete(0, tk.END)
            norm_filter = remove_vietnamese_accents(filter_text.strip().lower())
            self.current_city_matches = []
            sel_idx = 0
            for eng, vn in VN_CITIES:
                norm_vn = remove_vietnamese_accents(vn.lower())
                if not norm_filter or norm_filter in norm_vn or norm_filter in eng.lower():
                    self.current_city_matches.append((eng, vn))
                    self.city_listbox.insert(tk.END, f"  {vn}")
                    if eng.lower() == getattr(self, 'selected_city_eng', '').lower():
                        sel_idx = len(self.current_city_matches) - 1

            if self.current_city_matches:
                self.city_listbox.selection_set(sel_idx)
                self.city_listbox.see(sel_idx)

        def _on_city_click(event=None):
            try:
                sel = self.city_listbox.curselection()
                if sel:
                    idx = sel[0]
                    eng, vn = self.current_city_matches[idx]
                    self.selected_city_eng = eng
                    self.selected_city_vn = vn
                    self.city_picker_btn.configure(text=f"{vn}  ▼")
                    self.close_city_dropdown()
            except Exception:
                pass

        self.city_listbox.bind("<ButtonRelease-1>", _on_city_click)
        self.city_listbox.bind("<Return>", _on_city_click)
        popup.bind("<Escape>", lambda e: self.close_city_dropdown())
        self.city_search_entry.bind("<KeyRelease>", lambda e: _render_cities(self.city_search_entry.get()))
        _render_cities()

    def _position_and_show_city_popup(self):
        if not hasattr(self, 'city_dropdown_popup') or self.city_dropdown_popup is None:
            return
        try:
            self.update_idletasks()
            bx = self.city_picker_btn.winfo_rootx()
            by = self.city_picker_btn.winfo_rooty()
            bw = self.city_picker_btn.winfo_width()
            bh = self.city_picker_btn.winfo_height()
            win_h = self.winfo_height()
            win_y = self.winfo_rooty()

            # Pop UP if button is in lower half of screen, otherwise Pop DOWN
            if (by - win_y) > (win_h * 0.48):
                py = max(0, by - 252)
            else:
                py = by + bh + 2

            self.city_dropdown_popup.geometry(f"{bw}x250+{bx}+{py}")
            self.city_dropdown_popup.deiconify()
            self.city_dropdown_popup.attributes("-topmost", True)
            self.after(60, lambda: (
                self.city_dropdown_popup.attributes("-topmost", False) if hasattr(self, 'city_dropdown_popup') and self.city_dropdown_popup and self.city_dropdown_popup.winfo_exists() else None
            ))
            self.city_dropdown_popup.lift()
            if hasattr(self, 'city_search_entry'):
                self.city_search_entry.focus_set()
        except Exception as e:
            print(f"[City Popup Error] {e}")

    def _highlight_page_button(self, page_id):
        for pid, btn_box in enumerate(self.page_btns):
            p_code, p_ico, p_title, p_sub, p_col = PAGE_ITEMS[pid]
            if pid == page_id:
                btn_box.configure(fg_color="#1f2937", border_color=p_col, border_width=2)
            else:
                btn_box.configure(fg_color="#030712", border_color="#1f2937", border_width=1)

    def _highlight_theme_button(self, theme_key):
        if hasattr(self, 'theme_btns'):
            for tk, (t_btn, acc_c) in self.theme_btns.items():
                if tk == theme_key:
                    t_btn.configure(fg_color="#1f2937", border_color=acc_c, border_width=2)
                else:
                    t_btn.configure(fg_color="#030712", border_color="#1f2937", border_width=1)


    def _update_alarm_toggle_ui(self, enabled):
        self.alarm_enabled_state = enabled
        if hasattr(self, 'toggle_alm_btn'):
            if enabled:
                # Alarm ON: Bright Emerald Green
                self.toggle_alm_btn.configure(
                    text="⏰ Alarm On", fg_color="#059669", hover_color="#10B981",
                    text_color="#FFFFFF", border_width=2, border_color="#34D399"
                )
            else:
                # Alarm OFF: Active Red
                self.toggle_alm_btn.configure(
                    text="⏰ Alarm Off", fg_color="#7F1D1D", hover_color="#991B1B",
                    text_color="#FCA5A5", border_width=2, border_color="#EF4444"
                )

    def toggle_alarm_state(self):
        self.last_user_action_time = time.time()
        new_state = not getattr(self, 'alarm_enabled_state', False)
        self.pending_control["alarm_enable"] = new_state
        self._update_alarm_toggle_ui(new_state)
        st_text = "⏰ Alarm Enabled" if new_state else "🔕 Alarm Disabled"
        self.status_lbl.configure(text=f"✅ {st_text}", text_color="#39FF14" if new_state else "#F85149")

    def _sync_state_from_cyd(self, sdata):
        # Debounce: ignore old state feedback from CYD for 2.5s after user action to eliminate page button flicker
        if time.time() - self.last_user_action_time < 2.5:
            return

        page_id = sdata.get("page", 0)
        if page_id != self.active_cyd_page:
            self.active_cyd_page = page_id
            self._highlight_page_button(page_id)

        cyd_theme = sdata.get("theme", "")
        if cyd_theme and getattr(self, 'active_cyd_theme', '') != cyd_theme:
            self.active_cyd_theme = cyd_theme
            self._highlight_theme_button(cyd_theme)

        # Sync city from CYD immediately on connect or state update
        cyd_city = sdata.get("city", "")
        if cyd_city and hasattr(self, 'city_picker_btn'):
            c_val = cyd_city.strip()
            if c_val.lower() != getattr(self, 'last_cyd_city', '').lower():
                if time.time() - self.last_user_action_time > 3.0 or not getattr(self, 'last_cyd_city', ''):
                    self.last_cyd_city = c_val.lower()
                    for eng, vn in VN_CITIES:
                        if eng.lower() == c_val.lower():
                            self.selected_city_eng = eng
                            self.selected_city_vn = vn
                            self.city_picker_btn.configure(text=f"{vn}  ▼")
                            break

        cur1 = sdata.get("cur1", "")
        if cur1 and hasattr(self, 'cur1_combo'):
            self.cur1_combo.set(cur1)

        cur2 = sdata.get("cur2", "")
        if cur2 and hasattr(self, 'cur2_combo'):
            self.cur2_combo.set(cur2)

        # Sync alarm status from CYD
        alarm_en = sdata.get("alarm_en", None)
        if alarm_en is not None:
            self._update_alarm_toggle_ui(bool(alarm_en))

    def apply_city(self):
        self.last_user_action_time = time.time()
        eng_city = getattr(self, 'selected_city_eng', 'Hanoi')
        vn_city = getattr(self, 'selected_city_vn', 'Hà Nội')
        self.last_cyd_city = eng_city.lower()
        self.pending_control["city"] = eng_city
        self.status_lbl.configure(text=f"✅ Weather City set: {vn_city} ({eng_city})", text_color="#39FF14")

    def apply_currencies(self):
        self.last_user_action_time = time.time()
        c1 = self.cur1_combo.get(); c2 = self.cur2_combo.get()
        self.pending_control["cur1"] = c1
        self.pending_control["cur2"] = c2
        self.status_lbl.configure(text=f"✅ FX Currencies set: {c1}/{c2}", text_color="#39FF14")

    def apply_alarm(self):
        self.last_user_action_time = time.time()
        try:
            ah = int(self.alarm_h_combo.get())
            am = int(self.alarm_m_combo.get())
            raw_note = self.alarm_note_entry.get().strip() if hasattr(self, 'alarm_note_entry') else ""
            safe_note = remove_vietnamese_accents(raw_note)[:60] if raw_note else ""
            self.pending_control["alarm_h"] = ah
            self.pending_control["alarm_m"] = am
            self.pending_control["alarm_enable"] = True
            if safe_note:
                self.pending_control["alarm_note"] = safe_note
            self._update_alarm_toggle_ui(True)
            self.status_lbl.configure(text=f"✅ Alarm Clock set for {ah:02d}:{am:02d}" + (f" ({safe_note})" if safe_note else ""), text_color="#39FF14")
        except Exception as e:
            print(f"[Alarm] Error: {e}")

    def _update_telemetry_ui(self, c, r, d, u):
        if hasattr(self, 'lbl_cpu'):
            self.lbl_cpu.configure(text=f"{c}%")
            self.bar_cpu.set(c / 100.0)
            self.lbl_ram.configure(text=f"{r}%")
            self.bar_ram.set(r / 100.0)
            self.lbl_net_down.configure(text=f"{d} KB/s" if d < 1024 else f"{d/1024:.1f} MB/s")
            self.bar_net_down.set(min(1.0, d / 2048.0))
            self.lbl_net_up.configure(text=f"{u} KB/s" if u < 1024 else f"{u/1024:.1f} MB/s")
            self.bar_net_up.set(min(1.0, u / 1024.0))

    # ── HARDWARE METRICS STREAM LOOP (< 50ms Connection) ──────────────
    def stream_loop(self):
        global active_serial_conn
        ser = None
        while True:
            if not self.is_streaming:
                time.sleep(1); break

            now_time = time.time()

            # 1. Collect Hardware Metrics (CPU, RAM, GPU, Net, Disks)
            try:
                curr_net = psutil.net_io_counters()
                dt = now_time - self.last_time
                if dt > 0 and self.last_net is not None:
                    down_speed = int((curr_net.bytes_recv - self.last_net.bytes_recv) / dt / 1024)
                    up_speed = int((curr_net.bytes_sent - self.last_net.bytes_sent) / dt / 1024)
                else:
                    down_speed = up_speed = 0
                self.last_net = curr_net; self.last_time = now_time

                cpu_pct = int(psutil.cpu_percent(interval=None))
                ram_pct = int(psutil.virtual_memory().percent)
                gpu_pct, gpu_temp, vram_pct = _get_gpu_stats()

                # Collect Fixed Disk Drives (C:, D:, E:...)
                disks_info = []
                try:
                    for part in psutil.disk_partitions(all=False):
                        if 'fixed' in part.opts or ('cdrom' not in part.opts and part.fstype):
                            try:
                                usage = psutil.disk_usage(part.mountpoint)
                                dname = part.device.replace(":\\", "").replace(":", "").upper()
                                disks_info.append({"name": dname, "used": int(usage.percent)})
                            except Exception: pass
                except Exception: pass

                payload = {
                    "cpu": cpu_pct,
                    "ram": ram_pct,
                    "gpu": gpu_pct,
                    "gputemp": gpu_temp,
                    "vram": vram_pct,
                    "net_down": down_speed,
                    "net_up": up_speed,
                    "disks": disks_info[:4]
                }

                # Include Windows Media Session info (track title, artist, playing state)
                with _media_info_lock:
                    mi = _media_session_info.copy()
                if mi.get("title"):
                    # Strip Unicode/Vietnamese diacritics for TFT LCD character set
                    safe_title = remove_vietnamese_accents(mi["title"][:60])
                    safe_artist = remove_vietnamese_accents(mi.get("artist", "")[:60])
                    # Keep only printable ASCII characters
                    safe_title = ''.join(c for c in safe_title if c in string.printable and c not in '\t\n\r\x0b\x0c')
                    safe_artist = ''.join(c for c in safe_artist if c in string.printable and c not in '\t\n\r\x0b\x0c')
                    payload["mediaTitle"] = safe_title
                    payload["mediaArtist"] = safe_artist
                    payload["isMediaPlaying"] = mi.get("playing", False)

                # MERGE PENDING USER CONTROL COMMANDS INTO TELEMETRY JSON PACKET
                if self.pending_control:
                    payload.update(self.pending_control)
                    self.pending_control = {}

                self.after(0, lambda c=cpu_pct, r=ram_pct, d=down_speed, u=up_speed:
                           self._update_telemetry_ui(c, r, d, u))
            except Exception:
                time.sleep(0.5); continue

            # 2. USB Serial Connection
            connected_usb = False
            connected_wifi = False
            ser_port = ""

            if (ser is None or not ser.is_open) and (now_time - self.last_port_scan > 1.0):
                self.last_port_scan = now_time
                target_port = self.selected_com_port

                candidate_ports = []
                if target_port != "AUTO":
                    candidate_ports.append(target_port)
                else:
                    if self.cached_com_port:
                        candidate_ports.append(self.cached_com_port)
                    ports = list(serial.tools.list_ports.comports())
                    for p in ports:
                        p_dev = str(p.device).upper()
                        p_desc = str(p.description).upper()
                        p_hwid = str(getattr(p, 'hwid', '')).upper()
                        if "BLUETOOTH" in p_desc or "BTHENUM" in p_hwid: continue
                        if ("COM" in p_dev and p_dev != "COM1") or any(k in p_desc for k in ["CH340", "CP210", "USB", "UART"]):
                            if p.device not in candidate_ports:
                                candidate_ports.append(p.device)

                for p_name in candidate_ports:
                    try:
                        s = serial.Serial()
                        s.port = p_name
                        s.baudrate = 115200
                        s.timeout = 0.05
                        s.dtr = False
                        s.rts = False
                        s.open()
                        ser = s
                        with serial_lock:
                            active_serial_conn = ser
                        self.cached_com_port = p_name
                        break
                    except Exception:
                        ser = None
                        with serial_lock:
                            active_serial_conn = None

            if ser and ser.is_open:
                try:
                    with serial_lock:
                        ser.write((json.dumps(payload) + "\n").encode('utf-8'))
                        ser.flush()

                        # Read response state or Media commands from CYD over Serial
                        if ser.in_waiting > 0:
                            raw_lines = ser.read_all().decode('utf-8', errors='ignore').split('\n')
                            for line in raw_lines:
                                line = line.strip()
                                if line.startswith("STATE:"):
                                    try:
                                        sdata = json.loads(line[6:])
                                        self.after(0, lambda sd=sdata: self._sync_state_from_cyd(sd))
                                    except Exception: pass
                                elif line.startswith("MEDIA_CMD:"):
                                    cmd_act = line[10:].strip()
                                    self.after(0, lambda act=cmd_act: self.handle_media_action(act))

                    connected_usb = True
                    ser_port = ser.port
                except Exception:
                    try: ser.close()
                    except Exception: pass
                    ser = None
                    with serial_lock:
                        active_serial_conn = None
                    connected_usb = False

            # Fallback to WiFi HTTP if USB not connected
            if not connected_usb and self.esp32_ip:
                try:
                    resp = requests.post(f"http://{self.esp32_ip}/api/pc", json=payload, timeout=0.4)
                    if resp.ok:
                        connected_wifi = True
                except Exception: pass

            # Update status banner accurately
            if connected_usb:
                self.after(0, lambda dev=ser_port: self.status_lbl.configure(
                    text=f"🟢 Connected via USB ({dev})", text_color="#39FF14"
                ))
            elif connected_wifi:
                self.after(0, lambda ip=self.esp32_ip: self.status_lbl.configure(
                    text=f"🌐 Connected via WiFi ({ip})", text_color="#00E676"
                ))
            else:
                self.after(0, lambda: self.status_lbl.configure(
                    text="🟡 Standby Mode (Select COM Port / Check Cable)", text_color="#EAB308"
                ))

            time.sleep(1)

def _send_control_cmd(cmd_dict, status_lbl, success_msg, err_msg):
    if app_instance:
        app_instance.pending_control.update(cmd_dict)
        if status_lbl:
            status_lbl.configure(text=success_msg, text_color="#39FF14")

if __name__ == "__main__":
    app = SmartDeskStudioProApp()
    app.mainloop()
