# PC MONITOR SERVICE FOR ESP32 CYD DASHBOARD

Phần mềm giám sát thông số máy tính (CPU, GPU, RAM, Disks, Network speed) gửi qua cáp USB tới ESP32 CYD Desk Dashboard.

## Hướng Dẫn Cài Đặt & Chạy (Windows)

### Bước 1: Cài đặt thư viện Python
Mở **PowerShell** hoặc **Command Prompt** và chạy:
```bash
pip install psutil pyserial wmi pyinstaller
```

### Bước 2: Chạy thử nghiệm
Cắm cáp USB nối ESP32 CYD với máy tính, mở terminal tại thư mục `pc_utility` và chạy:
```bash
python pc_monitor.py
```
Dịch vụ sẽ tự động quét cổng COM (CP2102/CH340), bắt tay `PING` / `PONG` và bắt đầu đẩy dữ liệu JSON tới CYD.

### Bước 3: Đóng gói thành file `.exe` chạy ẩn
```bash
cd pc_utility
pyinstaller --onefile --noconsole pc_monitor.py
```
File `pc_monitor.exe` sẽ được tạo tại `pc_utility/dist/pc_monitor.exe`.

### Bước 4: Tự động khởi động cùng Windows
1. Nhấn `Windows + R`, gõ `shell:startup` và ấn **Enter**.
2. Copy file `pc_monitor.exe` dán vào thư mục Startup vừa mở.
