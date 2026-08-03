import sys
import os
import time
import string
import json
import traceback
import threading
import requests
import psutil
import serial
import serial.tools.list_ports
import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

# Set CustomTkinter theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

VN_CITIES = [
    ("Hanoi", "Hà Nội"),
    ("Ho Chi Minh", "TP. Hồ Chí Minh"),
    ("Da Nang", "Đà Nẵng"),
    ("Hai Phong", "Hải Phòng"),
    ("Can Tho", "Cần Thơ"),
    ("Nha Trang", "Nha Trang (Khánh Hòa)"),
    ("Da Lat", "Đà Lạt (Lâm Đồng)"),
    ("Hue", "Thừa Thiên Huế"),
    ("Vung Tau", "Bà Rịa - Vũng Tàu"),
    ("Quy Nhon", "Quy Nhơn (Bình Định)"),
    ("Buon Ma Thuot", "Buôn Ma Thuột"),
    ("Ha Long", "Hạ Long (Quảng Ninh)"),
    ("Phan Thiet", "Phan Thiết"),
    ("Thanh Hoa", "Thanh Hóa"),
    ("Vinh", "Vinh (Nghệ An)"),
    ("Phu Quoc", "Đảo Phú Quốc"),
    ("Rach Gia", "Rạch Giá (Kiên Giang)"),
    ("Ca Mau", "Cà Mau")
]

THEMES = [
    ("Ocean Dark", "ocean_dark"),
    ("Cyberpunk", "cyberpunk"),
    ("Forest", "forest"),
    ("Cherry", "cherry"),
    ("Light Day", "light_day"),
    ("Retro Green", "retro_green")
]

class CYDMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ESP32 CYD Desk Dashboard Studio")
        self.geometry("560x740")
        self.resizable(False, False)

        self.esp32_ip = "192.168.1.13"
        self.cached_ip = self.esp32_ip  # thread-safe copy — never call ip_entry.get() from bg thread!
        self.is_streaming = True
        self.tray_icon = None

        # Network speed tracking
        self.last_net = psutil.net_io_counters()
        self.last_time = time.time()

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        # Clear debug log on each startup
        try:
            open("debug.log", "w").close()
        except Exception:
            pass

        # Start background hardware metrics streaming thread
        self.stream_thread = threading.Thread(target=self.stream_loop, daemon=True)
        self.stream_thread.start()

        # Poll & sync IP from entry box every 2s on main thread
        self._sync_ip_loop()

    def create_widgets(self):
        # ── Header Frame ──────────────────────────────────────────────
        hdr_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        hdr_frame.pack(fill="x", padx=15, pady=(15, 10))

        title_lbl = ctk.CTkLabel(
            hdr_frame, text="💻 ESP32 CYD Smart Dashboard Studio",
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#58a6ff"
        )
        title_lbl.pack(pady=10)

        # ── Connection Settings ───────────────────────────────────────
        conn_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        conn_frame.pack(fill="x", padx=15, pady=5)

        ip_lbl = ctk.CTkLabel(conn_frame, text="ESP32 IP Address:", font=ctk.CTkFont(size=13))
        ip_lbl.pack(side="left", padx=12, pady=10)

        self.ip_entry = ctk.CTkEntry(conn_frame, width=140)
        self.ip_entry.insert(0, self.esp32_ip)
        self.ip_entry.pack(side="left", padx=5, pady=10)

        self.status_lbl = ctk.CTkLabel(
            conn_frame, text="● Searching for CYD...", font=ctk.CTkFont(size=12, weight="bold"), text_color="#d29922"
        )
        self.status_lbl.pack(side="right", padx=15, pady=10)

        # ── Weather Location Section ──────────────────────────────────
        w_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        w_frame.pack(fill="x", padx=15, pady=5)

        w_title = ctk.CTkLabel(w_frame, text="🌤️ Weather Location", font=ctk.CTkFont(size=14, weight="bold"))
        w_title.pack(anchor="w", padx=12, pady=(10, 5))

        w_inner = ctk.CTkFrame(w_frame, fg_color="transparent")
        w_inner.pack(fill="x", padx=12, pady=(0, 10))

        city_names = [c[1] for c in VN_CITIES]
        self.city_combo = ctk.CTkOptionMenu(w_inner, values=city_names, width=280)
        self.city_combo.set("Hà Nội")
        self.city_combo.pack(side="left", padx=(0, 10))

        set_city_btn = ctk.CTkButton(w_inner, text="Set City", width=100, command=self.apply_city)
        set_city_btn.pack(side="left")

        # ── Foreign Exchange Rates Section ─────────────────────────────
        ex_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        ex_frame.pack(fill="x", padx=15, pady=5)

        ex_title = ctk.CTkLabel(ex_frame, text="💱 Foreign Exchange Rates (Chọn 2 Tỷ Giá)", font=ctk.CTkFont(size=14, weight="bold"))
        ex_title.pack(anchor="w", padx=12, pady=(10, 5))

        ex_inner = ctk.CTkFrame(ex_frame, fg_color="transparent")
        ex_inner.pack(fill="x", padx=12, pady=(0, 10))

        currencies = ["USD", "EUR", "JPY", "GBP", "AUD", "SGD", "CNY", "KRW", "CAD"]

        self.cur1_combo = ctk.CTkOptionMenu(ex_inner, values=currencies, width=130)
        self.cur1_combo.set("USD")
        self.cur1_combo.pack(side="left", padx=(0, 10))

        self.cur2_combo = ctk.CTkOptionMenu(ex_inner, values=currencies, width=130)
        self.cur2_combo.set("EUR")
        self.cur2_combo.pack(side="left", padx=(0, 10))

        set_ex_btn = ctk.CTkButton(ex_inner, text="Set Currencies", width=110, command=self.apply_currencies)
        set_ex_btn.pack(side="left")

        self.page_buttons = {}
        self.theme_buttons = {}
        self.active_page_id = -1
        self.active_theme_key = ""

        # ── Theme Presets Section ─────────────────────────────────────
        t_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        t_frame.pack(fill="x", padx=15, pady=5)

        t_title = ctk.CTkLabel(t_frame, text="🎨 Theme Presets", font=ctk.CTkFont(size=14, weight="bold"))
        t_title.pack(anchor="w", padx=12, pady=(10, 5))

        t_grid = ctk.CTkFrame(t_frame, fg_color="transparent")
        t_grid.pack(fill="x", padx=10, pady=(0, 10))

        for idx, (name, key) in enumerate(THEMES):
            r, c = divmod(idx, 3)
            btn = ctk.CTkButton(
                t_grid, text=name, width=155, height=32,
                fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9",
                command=lambda k=key: self.apply_theme(k)
            )
            btn.grid(row=r, column=c, padx=5, pady=5)
            self.theme_buttons[key] = btn

        # ── Remote Page Switcher ──────────────────────────────────────
        p_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        p_frame.pack(fill="x", padx=15, pady=5)

        p_title = ctk.CTkLabel(p_frame, text="📱 Remote Page Switcher", font=ctk.CTkFont(size=14, weight="bold"))
        p_title.pack(anchor="w", padx=12, pady=(10, 5))

        p_grid = ctk.CTkFrame(p_frame, fg_color="transparent")
        p_grid.pack(fill="x", padx=10, pady=(0, 10))

        pages = [
            ("0: Weather Clock", 0), ("1: Lunar Calendar", 1), ("2: Gold & Finance", 2),
            ("3: PC CPU/RAM", 3),     ("4: PC GPU/VRAM", 4),     ("5: PC Net/Disks", 5),
            ("6: Desk Utilities", 6)
        ]

        for idx, (p_name, p_id) in enumerate(pages):
            r, c = divmod(idx, 3)
            btn = ctk.CTkButton(
                p_grid, text=p_name, width=155, height=30,
                fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9",
                command=lambda pid=p_id: self.switch_page(pid)
            )
            btn.grid(row=r, column=c, padx=5, pady=4)
            self.page_buttons[p_id] = btn

        # Highlight default active buttons at launch
        self.highlight_active_page(0)
        self.highlight_active_theme("ocean_dark")

        # ── Hardware Live Status Preview ──────────────────────────────
        m_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        m_frame.pack(fill="x", padx=15, pady=5)

        m_title = ctk.CTkLabel(m_frame, text="📊 Live Hardware Metrics Streamed", font=ctk.CTkFont(size=14, weight="bold"))
        m_title.pack(anchor="w", padx=12, pady=(10, 5))

        self.metrics_lbl = ctk.CTkLabel(
            m_frame, text="CPU: 0% | RAM: 0% | Net Down: 0 KB/s | Net Up: 0 KB/s",
            font=ctk.CTkFont(size=12), text_color="#8b949e"
        )
        self.metrics_lbl.pack(anchor="w", padx=12, pady=(0, 10))

    def _sync_ip_loop(self):
        """Runs on main thread every 2s — copies IP entry to cached_ip for background thread."""
        try:
            self.cached_ip = self.ip_entry.get().strip()
        except Exception:
            pass
        self.after(2000, self._sync_ip_loop)

    def _set_metrics_text(self, cpu, ram, down, up):
        self.metrics_lbl.configure(
            text=f"CPU: {cpu}% | RAM: {ram}% | Net\u2193 {down} KB/s | Net\u2191 {up} KB/s"
        )

    def _set_status(self, text, color):
        self.status_lbl.configure(text=text, text_color=color)

    def highlight_active_page(self, page_id):
        if page_id == self.active_page_id:
            return
        self.active_page_id = page_id
        for pid, btn in self.page_buttons.items():
            if pid == page_id:
                btn.configure(fg_color="#1f6feb", hover_color="#388bfd", text_color="#ffffff")
            else:
                btn.configure(fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9")

    def highlight_active_theme(self, theme_key):
        if theme_key == self.active_theme_key:
            return
        self.active_theme_key = theme_key
        for key, btn in self.theme_buttons.items():
            if key == theme_key:
                btn.configure(fg_color="#238636", hover_color="#2ea043", text_color="#ffffff")
            else:
                btn.configure(fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9")

    def apply_city(self):
        sel = self.city_combo.get()
        eng_city = "Hanoi"
        for eng, vn in VN_CITIES:
            if vn == sel:
                eng_city = eng
                break

        ip = self.ip_entry.get().strip()
        try:
            resp = requests.post(f"http://{ip}/api/weather/city", json={"city": eng_city}, timeout=2)
            if resp.ok:
                self.status_lbl.configure(text=f"✅ City: {sel}", text_color="#2ea043")
        except Exception as e:
            self.status_lbl.configure(text="❌ Error setting city", text_color="#f85149")

    def apply_currencies(self):
        c1 = self.cur1_combo.get()
        c2 = self.cur2_combo.get()
        ip = self.ip_entry.get().strip()
        try:
            resp = requests.post(f"http://{ip}/api/exchange", json={"cur1": c1, "cur2": c2}, timeout=2)
            if resp.ok:
                self.status_lbl.configure(text=f"✅ Currencies: {c1}/{c2}", text_color="#2ea043")
        except Exception:
            self.status_lbl.configure(text="❌ Currency error", text_color="#f85149")

    def apply_theme(self, theme_key):
        self.highlight_active_theme(theme_key)
        ip = self.ip_entry.get().strip()
        try:
            resp = requests.post(f"http://{ip}/api/theme", json={"preset": theme_key}, timeout=2)
            if resp.ok:
                self.status_lbl.configure(text=f"✅ Theme: {theme_key}", text_color="#2ea043")
        except Exception:
            self.status_lbl.configure(text="❌ Theme error", text_color="#f85149")

    def switch_page(self, page_id):
        self.highlight_active_page(page_id)
        ip = self.ip_entry.get().strip()
        try:
            requests.get(f"http://{ip}/api/page?id={page_id}", timeout=2)
        except Exception:
            pass

    def stream_loop(self):
        # Sync current selected currencies to ESP32 on connect
        time.sleep(1)
        try:
            c1 = self.cur1_combo.get()
            c2 = self.cur2_combo.get()
            ip = self.ip_entry.get().strip()
            requests.post(f"http://{ip}/api/exchange", json={"cur1": c1, "cur2": c2}, timeout=1)
        except Exception:
            pass

        ser = None
        ser_port = ""
        connected_usb = False
        connected_wifi = False

        # Blocking first call so next call(interval=1) gives real data right away
        psutil.cpu_percent(interval=1)

        while True:
            if not self.is_streaming:
                time.sleep(1)
                continue

            # 1. Collect Hardware Metrics (GUI label always updates)
            try:
                cpu_pct = int(psutil.cpu_percent(interval=1))  # blocking 1s for accurate reading
                ram_pct = int(psutil.virtual_memory().percent)

                now_time = time.time()
                curr_net = psutil.net_io_counters()
                dt = now_time - self.last_time
                if dt > 0:
                    down_speed = int((curr_net.bytes_recv - self.last_net.bytes_recv) / dt / 1024)
                    up_speed = int((curr_net.bytes_sent - self.last_net.bytes_sent) / dt / 1024)
                else:
                    down_speed = up_speed = 0

                self.last_net = curr_net
                self.last_time = now_time

                disks = []
                for letter in string.ascii_uppercase:
                    drive_path = f"{letter}:\\"
                    if os.path.exists(drive_path):
                        try:
                            usage = psutil.disk_usage(drive_path)
                            if usage.total > 0:
                                used_pct = int(round((usage.used / usage.total) * 100))
                                disks.append({"name": letter, "used": used_pct})
                        except Exception:
                            pass

                payload = {
                    "cpu": cpu_pct,
                    "cpuLoad": cpu_pct,
                    "cputemp": 45,
                    "cpuTemp": 45,
                    "ram": ram_pct,
                    "ramLoad": ram_pct,
                    "gpu": cpu_pct,
                    "gpuLoad": cpu_pct,
                    "gputemp": 48,
                    "gpuTemp": 48,
                    "vram": ram_pct,
                    "vramLoad": ram_pct,
                    "net_down": down_speed,
                    "netDown": down_speed,
                    "net_up": up_speed,
                    "netUp": up_speed,
                    "disks": disks
                }

                # Update live GUI label IMMEDIATELY (thread-safe)
                self.after(0, lambda c=cpu_pct, r=ram_pct, d=down_speed, u=up_speed:
                           self._set_metrics_text(c, r, d, u))
            except Exception:
                with open("debug.log", "a") as _f:
                    _f.write(f"[METRICS ERR] {time.time():.0f}: {traceback.format_exc()}\n")
                time.sleep(1)
                continue

            # Reset connection flags each loop iteration
            connected_usb = False
            connected_wifi = False

            # 2. USB Serial Auto Connection
            if ser is None or not ser.is_open:
                try:
                    ports = list(serial.tools.list_ports.comports())
                    for p in ports:
                        if p.vid is not None and p.pid is not None:
                            try:
                                s = serial.Serial()
                                s.port = p.device
                                s.baudrate = 115200
                                s.dtr = False
                                s.rts = False
                                s.timeout = 0.2
                                s.open()
                                time.sleep(0.1)
                                s.write(b"PING_DASHBOARD\n")
                                time.sleep(0.5)  # Give ESP32 enough time to respond
                                res = s.read_all().decode('utf-8', errors='ignore')
                                if "PONG" in res:
                                    ser = s
                                    ser_port = p.device
                                    # Parse real-time page/theme state from PONG response
                                    try:
                                        brace_start = res.find("{")
                                        brace_end = res.rfind("}")
                                        if brace_start != -1 and brace_end > brace_start:
                                            j_str = res[brace_start:brace_end+1]
                                            st_data = json.loads(j_str)
                                            if "page" in st_data:
                                                self.after(0, lambda v=st_data["page"]: self.highlight_active_page(v))
                                            if "theme" in st_data:
                                                self.after(0, lambda v=st_data["theme"]: self.highlight_active_theme(v))
                                    except Exception:
                                        pass
                                    break
                                s.close()
                            except Exception:
                                pass
                except Exception:
                    ser = None

            if ser and ser.is_open:
                try:
                    json_line = json.dumps(payload) + "\n"
                    ser.write(json_line.encode('utf-8'))
                    connected_usb = True
                    # Read any response for page/theme sync (non-blocking)
                    if ser.in_waiting:
                        try:
                            resp_line = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            if "{" in resp_line:
                                j_str = resp_line[resp_line.find("{"):resp_line.rfind("}")+1]
                                st_data = json.loads(j_str)
                                if "page" in st_data:
                                    self.after(0, lambda v=st_data["page"]: self.highlight_active_page(v))
                                if "theme" in st_data:
                                    self.after(0, lambda v=st_data["theme"]: self.highlight_active_theme(v))
                        except Exception:
                            pass
                except Exception:
                    try: ser.close()
                    except Exception: pass
                    ser = None

            # 3. WiFi HTTP Streaming — use cached_ip (thread-safe, no Tkinter call)
            ip = self.cached_ip
            if ip:
                try:
                    resp = requests.post(f"http://{ip}/api/pc", json=payload, timeout=1.5)
                    if resp.ok:
                        connected_wifi = True
                        try:
                            res_data = resp.json()
                            page_val = res_data.get("page", -1)
                            theme_val = res_data.get("theme", "")
                            if page_val >= 0:
                                self.after(0, lambda v=page_val: self.highlight_active_page(v))
                            if theme_val:
                                self.after(0, lambda v=theme_val: self.highlight_active_theme(v))
                        except Exception:
                            pass
                except Exception as wifi_ex:
                    with open("debug.log", "a") as _f:
                        _f.write(f"[WIFI ERR] {time.time():.0f} ip={ip}: {wifi_ex}\n")

            # 4. Status Indicator Update (thread-safe via after)
            if connected_usb:
                self.after(0, lambda p=ser_port: self._set_status(f"\u25cf Connected (USB {p})", "#2ea043"))
            elif connected_wifi:
                self.after(0, lambda i=ip: self._set_status(f"\u25cf Connected (WiFi {i})", "#2ea043"))
            else:
                self.after(0, lambda: self._set_status("\u25cf Searching for CYD...", "#d29922"))

            # no extra sleep — cpu_percent(interval=1) already blocked 1s

    def create_tray_icon(self):
        """Runs in its own non-daemon thread. Blocking call."""
        # Draw ESP32 chip icon
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(image)
        d.rectangle((8, 8, 56, 56), fill=(13, 17, 23))
        d.ellipse((16, 16, 48, 48), fill=(88, 166, 255))
        d.rectangle((26, 26, 38, 38), fill=(13, 17, 23))

        def on_open(icon, item):
            self.after(0, self.deiconify)

        def on_exit(icon, item):
            icon.stop()
            self.after(0, self._do_exit)

        menu = pystray.Menu(
            pystray.MenuItem("Open Studio", on_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", on_exit)
        )
        self.tray_icon = pystray.Icon("CYDStudio", image, "CYD Dashboard Studio", menu)
        self.tray_icon.run()  # blocks until icon.stop()

    def minimize_to_tray(self):
        self.withdraw()
        if self.tray_icon is None:
            t = threading.Thread(target=self.create_tray_icon, daemon=False)
            t.start()
        # if already running, just stay hidden

    def show_from_tray(self, icon=None, item=None):
        self.deiconify()

    def _do_exit(self):
        self.tray_icon = None
        self.destroy()
        sys.exit(0)

    def exit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self._do_exit()

if __name__ == "__main__":
    app = CYDMonitorApp()
    app.mainloop()
