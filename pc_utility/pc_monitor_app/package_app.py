#!/usr/bin/env python3
"""
Tự động đóng gói ứng dụng PC Smart Desk Studio Pro:
1. Tạo icon và assets thương mại (ICO / PNG).
2. Đóng gói ứng dụng thành file thực thi độc lập bằng PyInstaller.
3. (Tùy chọn) Biên dịch bộ cài đặt Inno Setup installer (nếu có ISCC.exe).
"""

import os
import sys
import subprocess
import shutil

# Reconfigure stdout for UTF-8 on Windows command line if needed
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_step(description, command, cwd=BASE_DIR):
    print(f"\n[BUILD STEP] {description}...")
    try:
        res = subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=False)
        print(f"[OK] {description} SUCCESS!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description} FAILED (Exit Code: {e.returncode})")
        return False

def main():
    print("==========================================================")
    print("  SMART DESK STUDIO PRO - PC INSTALLER AUTOMATED PACKATER")
    print("==========================================================")

    # 1. Generate Icons
    run_step("Generate App Icons & Assets (app_icon.ico / PNG)", [sys.executable, "generate_icons.py"])

    # 2. Run PyInstaller
    spec_file = os.path.join(BASE_DIR, "Smart_Desk_Studio.spec")
    success = run_step("Package Application with PyInstaller", [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_file])

    if not success:
        print("[ERROR] PyInstaller packaging failed.")
        sys.exit(1)

    dist_app_dir = os.path.join(BASE_DIR, "dist", "Smart_Desk_Studio")
    exe_file = os.path.join(dist_app_dir, "Smart_Desk_Studio.exe")

    if os.path.exists(exe_file):
        print(f"\n[INFO] Commercial Executable file ready at:")
        print(f"       {exe_file}")

    # 3. Check for Inno Setup compiler
    iscc_paths = [
        "iscc",
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]

    iscc_exe = None
    for p in iscc_paths:
        if shutil.which(p) or os.path.exists(p):
            iscc_exe = p
            break

    iss_file = os.path.join(BASE_DIR, "Smart_Desk_Studio_Setup.iss")
    if iscc_exe and os.path.exists(iss_file):
        print("\n[INFO] Inno Setup Compiler found! Compiling Setup.exe installer...")
        setup_success = run_step("Compile Inno Setup Installer", [iscc_exe, iss_file])
        if setup_success:
            setup_exe = os.path.join(BASE_DIR, "installer_output", "Setup_Smart_Desk_Studio_v1.0.exe")
            print(f"\n[SUCCESS] Windows Setup Installer packaged successfully at:")
            print(f"          {setup_exe}")
    else:
        print("\n[NOTE] Inno Setup Installer Script:")
        print("  - Script is ready at: Smart_Desk_Studio_Setup.iss")
        print("  - To compile into a single Setup_Smart_Desk_Studio_v1.0.exe installer, download free Inno Setup at:")
        print("    https://jrsoftware.org/isdl.php")
        print("  - After installing Inno Setup, open Smart_Desk_Studio_Setup.iss and click Compile (Ctrl+F9).")

    print("\n==========================================================")

if __name__ == "__main__":
    main()
