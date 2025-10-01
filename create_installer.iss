; Inno Setup Script for Tender Management Utility
; To use:
; 1. Run build_exe.py to create the 'dist/TenderManagementUtility' folder.
; 2. Install Inno Setup Compiler (from jrsoftware.org).
; 3. Open this file in Inno Setup and click "Compile".

#define MyAppName "Tender Management Utility"
#define MyAppVersion "3.0"
#define MyAppPublisher "Your Name or Company"
#define MyAppURL "https://github.com/yourusername/tender-management"
#define MyAppExeName "TenderManagementUtility.exe"

[Setup]
AppId={{12345678-1234-1234-1234-123456789012}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=.\dist
OutputBaseFilename=TenderManagementUtility_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
; Set the installer icon
SetupIconFile=resources\app_icon.ico
; License and info
LicenseFile=resources\license.txt
InfoBeforeFile=resources\readme.txt
InfoAfterFile=resources\readme.txt

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

[Code]
function InitializeSetup(): Boolean;
var
  InstalledVersion: string;
  UninstallString: string;
  ResultCode: Integer;
begin
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{12345678-1234-1234-1234-123456789012}_is1', 'DisplayVersion', InstalledVersion) then
  begin
    if CompareStr(InstalledVersion, '{#MyAppVersion}') = 0 then
    begin
      case MsgBox('The same version ({#MyAppVersion}) is already installed. What would you like to do?', mbConfirmation, MB_ABORTRETRYIGNORE + MB_DEFBUTTON2) of
        IDABORT: Result := False;
        IDRETRY: begin
          // Repair: proceed with installation
          Result := True;
        end;
        IDIGNORE: begin
          // Uninstall and install
          if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{12345678-1234-1234-1234-123456789012}_is1', 'UninstallString', UninstallString) then
          begin
            Exec(RemoveQuotes(UninstallString), '/SILENT', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
          end;
          Result := True;
        end;
      end;
    end
    else if CompareStr(InstalledVersion, '{#MyAppVersion}') < 0 then
    begin
      // Older version installed, uninstall it
      if MsgBox('An older version (' + InstalledVersion + ') is installed. It will be uninstalled before installing the new version.', mbInformation, MB_OKCANCEL) = IDOK then
      begin
        if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{12345678-1234-1234-1234-123456789012}_is1', 'UninstallString', UninstallString) then
        begin
          Exec(RemoveQuotes(UninstallString), '/SILENT', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        end;
        Result := True;
      end
      else
      begin
        Result := False;
      end;
    end
    else
    begin
      // Newer version installed
      MsgBox('A newer version (' + InstalledVersion + ') is already installed. Installation aborted.', mbInformation, MB_OK);
      Result := False;
    end;
  end
  else
  begin
    Result := True;
  end;
end;
