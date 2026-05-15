[Setup]
; Unique AppId for stable uninstalls and updates
AppId={{6E7B3B5C-2A4D-4F1E-9C6A-8B4E3E3E3E3E}}
AppName=Lotus
AppVersion=3.1.0
AppPublisher=Satyam Pote
AppPublisherURL=https://github.com/Lotus-agent/Lotus
DefaultDirName={autopf}\Lotus
DefaultGroupName=Lotus
UninstallDisplayIcon={app}\Lotus.exe
Compression=lzma2/max
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=LotusSetup_v3.2
SetupIconFile=assets\lotus_icon.ico
WizardImageFile=assets\wizard_image.bmp
WizardSmallImageFile=assets\wizard_small.bmp
WizardStyle=modern
; Requires admin for Defender exclusions and ProgramData access
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableWelcomePage=no
CloseApplications=force

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Launch Lotus on Windows startup"; GroupDescription: "Options:"

[Files]
; Main Binaries
Source: "dist\Lotus.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\LotusTray.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "version.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Assets and Tools (bundled in EXE but also side-loaded for reliability)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{commonappdata}\Lotus"; Permissions: everyone-full
Name: "{commonappdata}\Lotus\logs"; Permissions: everyone-full
Name: "{commonappdata}\Lotus\config"; Permissions: everyone-full
Name: "{commonappdata}\Lotus\storage"; Permissions: everyone-full

[Icons]
Name: "{group}\Lotus"; Filename: "{app}\Lotus.exe"
Name: "{group}\{cm:UninstallProgram,Lotus}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Lotus"; Filename: "{app}\Lotus.exe"; Tasks: desktopicon

[Registry]
; Startup Entry
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "LotusTray"; ValueData: """{app}\LotusTray.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\Lotus.exe"; Description: "{cm:LaunchProgram,Lotus}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/F /IM Lotus.exe /T"; Flags: runhidden
Filename: "taskkill.exe"; Parameters: "/F /IM LotusTray.exe /T"; Flags: runhidden

[Code]
// ═══════════════════════════════════════════════════════════
// VC++ REDISTRIBUTABLE CHECK (Production Stable)
// ═══════════════════════════════════════════════════════════

function VCRedistNeedsInstall: Boolean;
var
  Version: String;
begin
  // Use HKLM64 to avoid CallSpawnServer issues with 32/64 bit redirection
  if RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Version) then
  begin
    Result := False;
  end
  else
  begin
    Result := True;
  end;
end;

procedure InitializeWizard;
var
  ErrorCode: Integer;
begin
  if VCRedistNeedsInstall then
  begin
    if MsgBox('Lotus requires the Microsoft Visual C++ Redistributable.' + #13#10 + #13#10 +
              'Download it now?', mbConfirmation, MB_YESNO) = idYes then
    begin
      ShellExec('open', 'https://aka.ms/vs/17/release/vc_redist.x64.exe', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Robust exclusion for both App and ProgramData
    Exec('powershell.exe', '-WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -Command "Add-MpPreference -ExclusionPath ''' + ExpandConstant('{app}') + ''',''' + ExpandConstant('{commonappdata}\Lotus') + '''"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;