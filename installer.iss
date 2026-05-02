; ─────────────────────────────────────────────────────────
;  Lotus Installer — Inno Setup Script
;  Installs Lotus.exe with all directories and startup entry
; ─────────────────────────────────────────────────────────

[Setup]
AppName=Lotus Windows Control Agent
AppVersion=2.0
AppPublisher=Satyam Pote
AppPublisherURL=https://github.com/SatyamPote/Lotus
AppSupportURL=https://github.com/SatyamPote/Lotus/issues
AppUpdatesURL=https://github.com/SatyamPote/Lotus/releases
DefaultDirName={autopf}\Lotus
DefaultGroupName=Lotus
UninstallDisplayName=Lotus Control Panel
UninstallDisplayIcon={app}\Lotus.exe
OutputDir=Output
OutputBaseFilename=LotusSetup
SetupIconFile=assets\lotus_icon.ico
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
WizardSmallImageFile=assets\wizard_small.bmp
WizardImageFile=assets\wizard_image.bmp
DisableWelcomePage=no
CloseApplications=force

[Dirs]
Name: "{commonappdata}\Lotus"
Name: "{commonappdata}\Lotus\logs"
Name: "{commonappdata}\Lotus\config"
Name: "{commonappdata}\Lotus\storage"
Name: "{commonappdata}\Lotus\storage\videos"
Name: "{commonappdata}\Lotus\storage\audio"
Name: "{commonappdata}\Lotus\storage\images"
Name: "{commonappdata}\Lotus\storage\files"
Name: "{commonappdata}\Lotus\storage\temp"

[Files]
Source: "dist\Lotus.exe";    DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*";          DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Lotus Control Panel"; Filename: "{app}\Lotus.exe"; IconFilename: "{app}\assets\lotus_icon.ico"
Name: "{autodesktop}\Lotus";         Filename: "{app}\Lotus.exe"; IconFilename: "{app}\assets\lotus_icon.ico"

[Registry]
; Add bot service to Windows startup (silent background)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "LotusControlPanel"; \
  ValueData: """{app}\Lotus.exe"" --bot-service"; \
  Flags: uninsdeletevalue

[Run]
; Launch GUI after install
Filename: "{app}\Lotus.exe"; Description: "Launch Lotus Control Panel"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove startup entry on uninstall
Filename: "reg"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v LotusControlPanel /f"; \
  Flags: runhidden

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
  begin
    Exec('taskkill.exe', '/F /IM Lotus.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
