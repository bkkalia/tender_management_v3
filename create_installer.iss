; Inno Setup Script for Tender Management Utility
; To use:
; 1. Run build_exe.py to create the 'dist/TenderManagementUtility' folder.
; 2. Install Inno Setup Compiler (from jrsoftware.org).
; 3. Open this file in Inno Setup and click "Compile".

[Setup]
AppName=Tender Management Utility
AppVersion=3.0
AppPublisher=Your Name or Company
AppPublisherURL=https://github.com/yourusername/tender-management
AppSupportURL=https://github.com/yourusername/tender-management
AppUpdatesURL=https://github.com/yourusername/tender-management/releases
DefaultDirName={autopf}\Tender Management Utility
DefaultGroupName=Tender Management Utility
OutputDir=.\dist
OutputBaseFilename=TenderManagementUtility_Setup_v3.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\TenderManagementUtility.exe
; Set the installer icon
SetupIconFile=resources\app_icon.ico
; Set the wizard images (optional - you can create these later)
WizardImageFile=resources\installer_banner.bmp
WizardSmallImageFile=resources\installer_small.bmp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; This includes the entire output of the PyInstaller build
Source: "dist\TenderManagementUtility\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Include the icon file separately for uninstaller
Source: "resources\app_icon.ico"; DestDir: "{app}\resources"; Flags: ignoreversion

[Icons]
Name: "{group}\Tender Management Utility"; Filename: "{app}\TenderManagementUtility.exe"; IconFilename: "{app}\resources\app_icon.ico"
Name: "{group}\Uninstall Tender Management Utility"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Tender Management Utility"; Filename: "{app}\TenderManagementUtility.exe"; IconFilename: "{app}\resources\app_icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Run]
Filename: "{app}\TenderManagementUtility.exe"; Description: "{cm:LaunchProgram,Tender Management Utility}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\config\*.json.backup"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\data\temp"
