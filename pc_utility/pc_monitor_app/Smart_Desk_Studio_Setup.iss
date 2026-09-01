; Script generated for Inno Setup Installer
; Smart Desk Studio Pro - PC Monitor & Control Center Utility Setup

#define MyAppName "Smart Desk Studio Pro"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ESP32 CYD Studio"
#define MyAppURL "https://github.com/hainguyen8982/ESP32_CYD_Smart_Desk_Studio_Pro"
#define MyAppExeName "Smart_Desk_Studio.exe"

[Setup]
AppId={{D37B4A12-8921-4E65-B2A8-5712CFA9381A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=Setup_Smart_Desk_Studio_v1.0
OutputDir=installer_output
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Fix Privileges vs HKCU Warning (Cho phép cài đặt không cần quyền Admin hoặc tùy chọn Admin)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Tự động khởi động cùng Windows (Autostart with Windows)"; GroupDescription: "Tùy chọn bổ sung:"

[Files]
Source: "dist\Smart_Desk_Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "SmartDeskStudioPro"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
