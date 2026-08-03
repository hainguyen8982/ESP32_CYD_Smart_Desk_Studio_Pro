import sys
import time
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
        self.is_streaming = True
        self.tray_icon = None

        # Network speed tracking
        self.last_net = psutil.net_io_counters()
        self.last_time = time.time()

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        # Start background hardware metrics streaming thread
        self.stream_thread = threading.Thread(target=self.stream_loop, daemon=True)
        self.stream_thread.start()

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

        import json
        ser = None
        ser_port = ""

        # First call to initialize cpu_percent baseline
        psutil.cpu_percent(interval=None)

        while True:
            if not self.is_streaming:
                time.sleep(1)
                continue

            # 1. Collect Hardware Metrics (GUI label always updates)
            try:
                cpu_pct = int(psutil.cpu_percent(interval=None))
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
                import string
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

                # Update live GUI label IMMEDIATELY
                self.metrics_lbl.configure(
                    text=f"CPU: {cpu_pct}% | RAM: {ram_pct}% | Net Down: {down_speed} KB/s | Net Up: {up_speed} KB/s"
                )
            except Exception:
                time.sleep(1)
                continue

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
                                time.sleep(0.15)
                                res = s.read_all().decode('utf-8', errors='ignore')
                                if "PONG" in res or "PING" in res:
                                    ser = s
                                    ser_port = p.device
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
                except Exception:
                    try: ser.close()
                    except Exception: pass
                    ser = None

            # 3. WiFi HTTP Streaming
            ip = self.ip_entry.get().strip()
            if ip:
                try:
                    resp = requests.post(f"http://{ip}/api/pc", json=payload, timeout=1.0)
                    if resp.ok:
                        connected_wifi = True
                        try:
                            res_data = resp.json()
                            if "page" in res_data:
                                self.highlight_active_page(res_data["page"])
                            if "theme" in res_data:
                                self.highlight_active_theme(res_data["theme"])
                        except Exception:
                            pass
                except Exception:
                    pass

            # 4. Status Indicator Update
            if connected_usb:
                self.status_lbl.configure(text=f"● Connected (USB {ser_port})", text_color="#2ea043")
            elif connected_wifi:
                self.status_lbl.configure(text=f"● Connected (WiFi {ip})", text_color="#2ea043")
            else:
                self.status_lbl.configure(text="● Searching for CYD...", text_color="#d29922")

            time.sleep(1.0)

    def create_tray_icon(self):
        # Create a simple blue icon for system tray
        image = Image.new('RGB', (64, 64), color=(13, 17, 23))
        d = ImageDraw.Draw(image)
        d.ellipse((12, 12, 52, 52), fill=(88, 166, 255))
        d.rectangle((24, 24, 40, 40), fill=(13, 17, 23))

        menu = pystray.Menu(
            pystray.MenuItem("Open Studio", self.show_from_tray, default=True),
            pystray.MenuItem("Exit", self.exit_app)
        )
        self.tray_icon = pystray.Icon("CYDStudio", image, "ESP32 CYD Dashboard Studio", menu)
        self.tray_icon.run()

    def minimize_to_tray(self):
        self.withdraw()
        if not self.tray_icon:
            threading.Thread(target=self.create_tray_icon, daemon=True).start()

    def show_from_tray(self, icon=None, item=None):
        self.deiconify()

    def exit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = CYDMonitorApp()
    app.mainloop()
