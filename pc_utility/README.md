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

---

## 📦 Hướng Dẫn Đóng Gói Bộ Cài Đặt Thương Mại (Commercial Installer)

### Cách 1: Tự động đóng gói 1-Click bằng Script (Khuyên dùng)
Chạy file script đóng gói tự động:
```cmd
cd pc_utility/pc_monitor_app
package_app.bat
```
hoặc chạy bằng Python:
```bash
python package_app.py
```
Script này sẽ tự động:
1. Tạo bộ icon ứng dụng chất lượng cao (`app_icon.ico`, `app_icon.png` & các nút điều khiển media).
2. Đóng gói ứng dụng thành file `.exe` thương mại cùng toàn bộ thư viện CustomTkinter/Assets qua PyInstaller.
3. Nếu máy tính đã cài [Inno Setup Compiler](https://jrsoftware.org/isdl.php), script sẽ tự động tạo file bộ cài đặt **`Setup_Smart_Desk_Studio_v1.0.exe`**.

---

### Cách 2: Đóng gói thủ công từng bước

#### 1. Tạo Icons & Assets:
```bash
python generate_icons.py
```

#### 2. Đóng gói file `.exe` bằng PyInstaller Spec:
```bash
python -m PyInstaller --noconfirm Smart_Desk_Studio.spec
```
File thực thi ứng dụng sẽ được tạo tại:
`pc_utility/pc_monitor_app/dist/Smart_Desk_Studio/Smart_Desk_Studio.exe`.

#### 3. Tạo Bộ Cài Đặt (Setup Installer) bằng Inno Setup:
1. Cài đặt phần mềm miễn phí [Inno Setup 6](https://jrsoftware.org/isdl.php).
2. Mở file `Smart_Desk_Studio_Setup.iss` bằng Inno Setup Compiler.
3. Nhấn **Compile** (`Ctrl + F9`). File bộ cài đặt sẽ được tạo tại:
   `pc_utility/pc_monitor_app/installer_output/Setup_Smart_Desk_Studio_v1.0.exe`.

---

## 🌟 Tính Năng Của Bộ Cài Đặt (Windows Setup Installer)
- 🚀 **Trình cài đặt đồ họa chuyên nghiệp**: Hướng dẫn cài đặt theo chuẩn Windows Wizard.
- 📌 **Tự động tạo Shortcut**: Tạo Icon trên Desktop và Start Menu.
- ⚡ **Khởi động cùng Windows**: Tùy chọn bật/tắt tính năng tự động chạy ngầm khi Windows boot.
- 🗑️ **Trình gỡ cài đặt (Uninstaller)**: Gỡ sạch sẽ phần mềm trong **Windows Settings / Control Panel (Add or Remove Programs)**.
