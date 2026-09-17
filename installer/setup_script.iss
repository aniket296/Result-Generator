; ═══════════════════════════════════════════════════════════════════════════════
; Teacher Result Card Generator - Inno Setup Script
; Version: 2.0.0
; Publisher: Academic Suite
; ═══════════════════════════════════════════════════════════════════════════════

#define MyAppName "Teacher Result Card Generator"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Academic Suite"
#define MyAppURL "https://github.com/aniket296/Result-Generator"
#define MyAppExeName "TeacherResultSoftware.exe"

[Setup]
; Unique AppId generated for Teacher Result Card Generator
AppId={{8B44A293-3F64-46E1-B590-3D90E659A1D1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Destination Directories
DefaultDirName={autopf}\TeacherResultSoftware
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; Output Configuration
OutputDir=..\dist_installer
OutputBaseFilename=TeacherResultSoftware_Setup_v2.0
SetupIconFile=assets\app_icon.ico

; Uninstaller Configuration
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression & Architecture
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableProgramGroupPage=auto

; Privileges (Allows user-level or administrative installs seamlessly)
PrivilegesRequiredOverridesAllowed=dialog commandline

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Desktop icon shortcut (checked by default)
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application binaries and dependencies from PyInstaller dist directory
Source: "..\dist\TeacherResultSoftware\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Application icon asset
Source: "assets\app_icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
; Start Menu Shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop Shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Option to launch the application immediately after setup completes
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

