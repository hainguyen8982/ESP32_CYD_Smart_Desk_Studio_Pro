# SMART DESK STUDIO - PC MONITOR UTILITY FOR ESP32 CYD DASHBOARD

Phần mềm giám sát thông số máy tính (CPU, GPU, RAM, Disks, Network speed) và trung tâm điều khiển từ xa (Remote Page, Themes, Weather, Exchange rates) dành cho ESP32 CYD Smart Desk Dashboard.

## Hướng Dẫn Cài Đặt & Chạy (Windows)

### Bước 1: Cài đặt thư viện Python
Mở **PowerShell** hoặc **Command Prompt** và chạy:
```bash
pip install customtkinter psutil pyserial requests pystray pillow pywin32 pyinstaller
```

### Bước 2: Chạy ứng dụng từ nguồn
Cắm cáp USB nối ESP32 CYD với máy tính (hoặc kết nối cùng mạng WiFi), mở terminal tại thư mục `pc_utility/pc_monitor_app` và chạy:
```bash
cd pc_utility/pc_monitor_app
python main.py
```
Ứng dụng sẽ tự động quét cổng COM (CH340/CP2102) hoặc kết nối qua WiFi, bắt đầu đẩy dữ liệu telemetry và lắng nghe tín hiệu UDP/Serial tốc độ cao (0ms latency).

### Bước 3: Đóng gói thành file `.exe` thương mại (Chạy ẩn, không Terminal)
```bash
cd pc_utility/pc_monitor_app
python -m PyInstaller --noconfirm --onedir --windowed --name "Smart_Desk_Studio" main.py
```
File thực thi thương mại `Smart_Desk_Studio.exe` sẽ được tạo tại:
`pc_utility/pc_monitor_app/dist/Smart_Desk_Studio/Smart_Desk_Studio.exe`.

### Bước 4: Tự động khởi động cùng Windows
1. Nhấn `Windows + R`, gõ `shell:startup` và ấn **Enter**.
2. Tạo Shortcut của file `Smart_Desk_Studio.exe` dán vào thư mục Startup vừa mở.

---

## 📦 Future Commercial Installer Roadmap (Plan)
Kế hoạch đóng gói bộ cài đặt thương mại chuyên nghiệp cho người dùng cuối:
- [ ] Dùng **Inno Setup / NSIS** tạo file `Setup_Smart_Desk_Studio.exe` đóng gói chuẩn Windows.
- [ ] Tự động tạo Shortcut Desktop & Start Menu.
- [ ] Tích hợp tính năng *Autostart with Windows* lựa chọn lúc cài đặt.
- [ ] Tích hợp Trình Gỡ Cài Đặt (Uninstaller) trong Windows Control Panel.
