[Setup]
AppName=Lotus Windows Control Agent
AppVersion=Beta
AppPublisher=Satyam Pote
AppPublisherURL=https://github.com/SatyamPote/Lotus
DefaultDirName={autopf}\Lotus
DefaultGroupName=Lotus
UninstallDisplayIcon={app}\Lotus.exe
OutputDir=Output
OutputBaseFilename=LotusSetup
SourceDir=.
SetupIconFile=assets\lotus_icon.ico
WizardImageFile=assets\wizard_image.bmp
WizardSmallImageFile=assets\wizard_small.bmp
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
DisableWelcomePage=no
CloseApplications=force

[Dirs]
Name: "{app}\logs"

[Files]
Source: "dist\Lotus.exe";              DestDir: "{app}";                 Flags: ignoreversion
Source: "assets\*";                    DestDir: "{app}\assets";          Flags: ignoreversion recursesubdirs createallsubdirs
Source: "install_scripts\*";           DestDir: "{app}\install_scripts"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "requirements.txt";            DestDir: "{app}";                 Flags: ignoreversion

[Icons]
Name: "{group}\Lotus Control Panel"; Filename: "{app}\Lotus.exe"; IconFilename: "{app}\assets\lotus_icon.ico"
Name: "{autodesktop}\Lotus";         Filename: "{app}\Lotus.exe"; IconFilename: "{app}\assets\lotus_icon.ico"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "LotusControlPanel"; ValueData: """{app}\Lotus.exe"" --bot-service"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Lotus.exe"; Description: "Launch Lotus"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "reg"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v LotusControlPanel /f"; Flags: runhidden

[Code]

// ═══════════════════════════════════════════════════════════
// 1. EXTERNAL API  — must come BEFORE const and var
// ═══════════════════════════════════════════════════════════

function SetTimer(hWnd: LongWord; nIDEvent: LongWord; uElapse: LongWord;
  lpTimerFunc: LongWord): LongWord; external 'SetTimer@user32.dll stdcall';

function KillTimer(hWnd: LongWord; uIDEvent: LongWord): Boolean;
  external 'KillTimer@user32.dll stdcall';

function SendMessageW(hWnd: LongWord; Msg: LongWord; wParam: LongInt;
  lParam: LongInt): LongInt; external 'SendMessageW@user32.dll stdcall';

// ═══════════════════════════════════════════════════════════
// 2. CONSTANTS
// ═══════════════════════════════════════════════════════════

const
  EM_SETSEL      = $00B1;
  EM_SCROLLCARET = $00B7;

// ═══════════════════════════════════════════════════════════
// 3. VARIABLES
// ═══════════════════════════════════════════════════════════

var
  AISetupPage:        TInputOptionWizardPage;
  ExistingModelPage:  TInputOptionWizardPage;
  DownloadModelPage:  TInputOptionWizardPage;
  ConfigPage:         TInputQueryWizardPage;
  CustomInstallPage:  TWizardPage;
  LogMemo:            TMemo;
  ProgressBack:       TLabel;
  ProgressFill:       TLabel;
  StatusLabel:        TLabel;
  TimerId:            LongWord;
  TimerCallback:      LongWord;
  LastLogLines:       Integer;
  LogFilePath:        String;
  SelectedModel:      String;
  ResultPython:       Integer;
  ResultRequirements: Integer;
  ResultFFmpeg:       Integer;
  ResultTools:        Integer;
  ResultOllama:       Integer;
  ResultModel:        Integer;
  ResultConfig:       Boolean;

// ═══════════════════════════════════════════════════════════
// 4. LOG STREAMING
// ═══════════════════════════════════════════════════════════

procedure ScrollLog;
begin
  SendMessageW(LogMemo.Handle, EM_SETSEL, -1, -1);
  SendMessageW(LogMemo.Handle, EM_SCROLLCARET, 0, 0);
end;

procedure UpdateLogs;
var
  Lines:    TArrayOfString;
  NewCount: Integer;
  I:        Integer;
begin
  if not FileExists(LogFilePath) then Exit;
  if not LoadStringsFromFile(LogFilePath, Lines) then Exit;
  NewCount := GetArrayLength(Lines);
  if NewCount <= LastLogLines then Exit;
  I := LastLogLines;
  while I < NewCount do
  begin
    LogMemo.Lines.Add(Lines[I]);
    I := I + 1;
  end;
  LastLogLines := NewCount;
  ScrollLog;
end;

procedure TimerProc(Wnd: LongWord; Msg: LongWord; TimerID: LongWord; Time: LongWord);
begin
  UpdateLogs;
end;

// ═══════════════════════════════════════════════════════════
// 5. SCRIPT RUNNER  (path and args are SEPARATE parameters)
// ═══════════════════════════════════════════════════════════

function RunScript(ScriptPath: String; ScriptArgs: String;
  StatusMsg: String; Pct: Integer): Integer;
var
  Code: Integer;
begin
  StatusLabel.Caption := StatusMsg;
  UpdateLogs;
  Exec('powershell.exe',
    '-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "' +
    ScriptPath + '" ' + ScriptArgs,
    '', SW_HIDE, ewWaitUntilTerminated, Code);
  ProgressFill.Width := (ProgressBack.Width * Pct) div 100;
  UpdateLogs;
  Result := Code;
end;

// ═══════════════════════════════════════════════════════════
// 6. PAGE CREATION
// ═══════════════════════════════════════════════════════════

procedure CreateCustomPages;
begin
  // AI Setup choice
  AISetupPage := CreateInputOptionPage(wpSelectTasks,
    'AI Setup', 'Configure the local AI engine.',
    'Lotus uses Ollama to run AI locally. Choose how you want to set it up.',
    True, False);
  AISetupPage.Add('Download and install new AI model  (Recommended)');
  AISetupPage.Add('Use existing Ollama models on this PC');
  AISetupPage.Add('Skip AI setup  (configure later)');
  AISetupPage.Values[0] := True;

  // Existing model selection — populated dynamically
  ExistingModelPage := CreateInputOptionPage(AISetupPage.ID,
    'Select Existing Model', 'Ollama models found on your system.',
    'Select the model you want Lotus to use.',
    True, False);

  // Download model selection
  DownloadModelPage := CreateInputOptionPage(ExistingModelPage.ID,
    'Download AI Model', 'Choose a model to download.',
    'The installer will download your chosen model. This may take several minutes.',
    True, False);
  DownloadModelPage.Add('phi3    — Fast     (~2.3 GB, recommended)');
  DownloadModelPage.Add('mistral — Balanced (~4.1 GB)');
  DownloadModelPage.Add('llama3  — Smart    (~4.7 GB)');
  DownloadModelPage.Values[0] := True;

  // Bot configuration
  ConfigPage := CreateInputQueryPage(DownloadModelPage.ID,
    'Lotus Configuration', 'Enter your Telegram Bot details.',
    'These details connect the Lotus bot to your Telegram account.');
  ConfigPage.Add('Your Name:', False);
  ConfigPage.Add('Telegram Bot Token:', False);
  ConfigPage.Add('Allowed User ID  (numbers only):', False);

  // Progress page
  CustomInstallPage := CreateCustomPage(wpInstalling,
    'Installing Lotus AI Agent',
    'Please wait while setup installs all components.');

  StatusLabel := TLabel.Create(CustomInstallPage);
  StatusLabel.Parent  := CustomInstallPage.Surface;
  StatusLabel.Left    := 0;
  StatusLabel.Top     := 0;
  StatusLabel.Width   := CustomInstallPage.SurfaceWidth;
  StatusLabel.Height  := 20;
  StatusLabel.Caption := 'Preparing...';
  StatusLabel.Font.Style := [fsBold];

  ProgressBack := TLabel.Create(CustomInstallPage);
  ProgressBack.Parent      := CustomInstallPage.Surface;
  ProgressBack.Left        := 0;
  ProgressBack.Top         := 25;
  ProgressBack.Width       := CustomInstallPage.SurfaceWidth;
  ProgressBack.Height      := 14;
  ProgressBack.Color       := clSilver;
  ProgressBack.Transparent := False;
  ProgressBack.Caption     := '';

  ProgressFill := TLabel.Create(CustomInstallPage);
  ProgressFill.Parent      := CustomInstallPage.Surface;
  ProgressFill.Left        := 0;
  ProgressFill.Top         := 25;
  ProgressFill.Width       := 0;
  ProgressFill.Height      := 14;
  ProgressFill.Color       := $00B469FF;
  ProgressFill.Transparent := False;
  ProgressFill.Caption     := '';

  LogMemo := TMemo.Create(CustomInstallPage);
  LogMemo.Parent      := CustomInstallPage.Surface;
  LogMemo.Left        := 0;
  LogMemo.Top         := 48;
  LogMemo.Width       := CustomInstallPage.SurfaceWidth;
  LogMemo.Height      := CustomInstallPage.SurfaceHeight - 48;
  LogMemo.ReadOnly    := True;
  LogMemo.ScrollBars  := ssVertical;
  LogMemo.Color       := clBlack;
  LogMemo.Font.Color  := clLime;
  LogMemo.Font.Name   := 'Consolas';
  LogMemo.Font.Size   := 9;
end;

// ═══════════════════════════════════════════════════════════
// 7. PAGE SKIP LOGIC
// ═══════════════════════════════════════════════════════════

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = ExistingModelPage.ID then
    Result := not AISetupPage.Values[1];
  if PageID = DownloadModelPage.ID then
    Result := not AISetupPage.Values[0];
end;

// ═══════════════════════════════════════════════════════════
// 8. NEXT BUTTON — detect existing models + validation
// ═══════════════════════════════════════════════════════════

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ScriptFile:  String;
  ModelsFile:  String;
  ScriptLines: TArrayOfString;
  RawLines:    TArrayOfString;
  ModelName:   String;
  UserID:      String;
  I:           Integer;
  Code:        Integer;
  C:           Char;
begin
  Result := True;

  // ── Validate config page ───────────────────────────────
  if CurPageID = ConfigPage.ID then
  begin
    if Trim(ConfigPage.Values[1]) = '' then
    begin
      MsgBox('Telegram Bot Token cannot be empty.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    UserID := Trim(ConfigPage.Values[2]);
    I := 1;
    while I <= Length(UserID) do
    begin
      C := UserID[I];
      if (C < '0') or (C > '9') then
      begin
        MsgBox('Allowed User ID must contain numbers only.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      I := I + 1;
    end;
  end;

  // ── Detect existing Ollama models ──────────────────────
  if (CurPageID = AISetupPage.ID) and AISetupPage.Values[1] then
  begin
    ScriptFile := ExpandConstant('{tmp}\detect_ollama.ps1');
    ModelsFile := ExpandConstant('{tmp}\ollama_models.txt');

    // Write the detection script to disk at runtime — no ExtractTemporaryFiles needed
    SetArrayLength(ScriptLines, 25);
    ScriptLines[0]  := 'param([string]$OutFile = '''')';
    ScriptLines[1]  := 'if (-not $OutFile) { exit 1 }';
    ScriptLines[2]  := '$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")';
    ScriptLines[3]  := 'try {';
    ScriptLines[4]  := '  $ver = & ollama --version 2>&1';
    ScriptLines[5]  := '  if ($LASTEXITCODE -ne 0) { exit 1 }';
    ScriptLines[6]  := '  $list = & ollama list 2>&1';
    ScriptLines[7]  := '  if ($LASTEXITCODE -ne 0) { exit 1 }';
    ScriptLines[8]  := '  $lines = $list -split "`r?`n"';
    ScriptLines[9]  := '  $models = @()';
    ScriptLines[10] := '  foreach ($line in $lines) {';
    ScriptLines[11] := '    $line = $line.Trim()';
    ScriptLines[12] := '    if ([string]::IsNullOrWhiteSpace($line)) { continue }';
    ScriptLines[13] := '    if ($line -match "^NAME") { continue }';
    ScriptLines[14] := '    $parts = $line -split "\s+"';
    ScriptLines[15] := '    if ($parts.Count -gt 0 -and $parts[0] -ne "") { $models += $parts[0] }';
    ScriptLines[16] := '  }';
    ScriptLines[17] := '  if ($models.Count -gt 0) {';
    ScriptLines[18] := '    $models | Out-File -FilePath $OutFile -Encoding UTF8';
    ScriptLines[19] := '    exit 0';
    ScriptLines[20] := '  }';
    ScriptLines[21] := '  exit 2';
    ScriptLines[22] := '} catch { exit 1 }';
    ScriptLines[23] := '';
    ScriptLines[24] := '';
    SaveStringsToFile(ScriptFile, ScriptLines, False);

    Exec('powershell.exe',
      '-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "' +
      ScriptFile + '" -OutFile "' + ModelsFile + '"',
      '', SW_HIDE, ewWaitUntilTerminated, Code);

    ExistingModelPage.CheckListBox.Items.Clear;

    if (Code = 0) and FileExists(ModelsFile) then
    begin
      LoadStringsFromFile(ModelsFile, RawLines);
      I := 0;
      while I < GetArrayLength(RawLines) do
      begin
        ModelName := Trim(RawLines[I]);
        if ModelName <> '' then
          ExistingModelPage.Add(ModelName);
        I := I + 1;
      end;
    end;

    if ExistingModelPage.CheckListBox.Items.Count = 0 then
    begin
      MsgBox('No Ollama models found on this PC.' + #13#10 +
             'Switching to Download mode.', mbInformation, MB_OK);
      AISetupPage.Values[0] := True;
      AISetupPage.Values[1] := False;
      Result := False;
    end
    else
      ExistingModelPage.Values[0] := True;
  end;
end;  // NextButtonClick

// ═══════════════════════════════════════════════════════════
// 9. MAIN INSTALLATION
// ═══════════════════════════════════════════════════════════

procedure RunInstallSteps;
var
  ScriptsDir:    String;
  ConfigContent: TArrayOfString;
  Summary:       String;
  HasFailure:    Boolean;
  ModelIdx:      Integer;
begin
  ScriptsDir  := ExpandConstant('{app}\install_scripts');
  LogFilePath := ExpandConstant('{app}\logs\install.log');
  ForceDirectories(ExpandConstant('{app}\logs'));
  LastLogLines := 0;

  TimerCallback := CreateCallback(@TimerProc);
  TimerId := SetTimer(0, 0, 800, TimerCallback);

  try
    WizardForm.NextButton.Enabled := False;
    WizardForm.BackButton.Enabled := False;

    // 0–10%  system check
    RunScript(ScriptsDir + '\system_check.ps1',      '', '5%  -> System check...',              10);

    // 10–30%  Python + pip
    ResultPython       := RunScript(ScriptsDir + '\install_python.ps1',       '', '15% -> Installing Python...',          20);
    ResultRequirements := RunScript(ScriptsDir + '\install_requirements.ps1', '', '25% -> Installing Python packages...', 30);

    // 30–50%  media tools
    ResultFFmpeg := RunScript(ScriptsDir + '\install_ffmpeg.ps1',  '', '35% -> Installing FFmpeg...',         40);
    ResultTools  := RunScript(ScriptsDir + '\download_tools.ps1',  '', '45% -> Downloading yt-dlp and mpv...', 50);

    // 50–70%  Ollama
    ResultOllama := RunScript(ScriptsDir + '\install_ollama.ps1', '', '60% -> Installing Ollama...', 70);

    // 70–90%  AI model
    SelectedModel := 'skip';
    ResultModel   := 0;

    if AISetupPage.Values[0] then  // Download new model
    begin
      if DownloadModelPage.Values[0]      then SelectedModel := 'phi3'
      else if DownloadModelPage.Values[1] then SelectedModel := 'mistral'
      else                                     SelectedModel := 'llama3';

      // ScriptArgs are OUTSIDE the quoted script path
      ResultModel := RunScript(
        ScriptsDir + '\pull_model.ps1',
        '-ModelName ' + SelectedModel,
        '80% -> Downloading model: ' + SelectedModel + '...',
        90);
    end
    else if AISetupPage.Values[1] then  // Use existing model
    begin
      ModelIdx := ExistingModelPage.SelectedValueIndex;
      if ModelIdx >= 0 then
        SelectedModel := ExistingModelPage.CheckListBox.Items[ModelIdx]
      else
        SelectedModel := 'phi3';
      ResultModel := 0;
    end;

    // 90–100%  write config
    StatusLabel.Caption := '95% -> Writing configuration...';
    SetArrayLength(ConfigContent, 6);
    ConfigContent[0] := '{';
    ConfigContent[1] := '  "name": "'           + Trim(ConfigPage.Values[0]) + '",';
    ConfigContent[2] := '  "telegram_token": "' + Trim(ConfigPage.Values[1]) + '",';
    ConfigContent[3] := '  "allowed_user_id": "' + Trim(ConfigPage.Values[2]) + '",';
    ConfigContent[4] := '  "model": "'           + SelectedModel + '"';
    ConfigContent[5] := '}';
    ResultConfig := SaveStringsToFile(ExpandConstant('{app}\config.json'), ConfigContent, False);
    ProgressFill.Width := ProgressBack.Width;
    UpdateLogs;

    // Summary
    HasFailure := (ResultPython <> 0) or (ResultRequirements <> 0) or
                  (ResultOllama <> 0) or
                  ((SelectedModel <> 'skip') and (ResultModel <> 0)) or
                  (not ResultConfig);

    Summary := 'Installation Summary:' + #13#10 + #13#10;

    if ResultPython = 0
      then Summary := Summary + #$2714 + ' Python installation'             + #13#10
      else Summary := Summary + #$274C + ' Python installation  (FAILED)'  + #13#10;

    if ResultRequirements = 0
      then Summary := Summary + #$2714 + ' Python dependencies'            + #13#10
      else Summary := Summary + #$274C + ' Python dependencies  (FAILED)'  + #13#10;

    if ResultFFmpeg = 0
      then Summary := Summary + #$2714 + ' FFmpeg installation'            + #13#10
      else Summary := Summary + '   FFmpeg skipped (optional)'             + #13#10;

    if ResultTools = 0
      then Summary := Summary + #$2714 + ' Media tools (yt-dlp, mpv)'     + #13#10
      else Summary := Summary + '   Media tools skipped (optional)'        + #13#10;

    if ResultOllama = 0
      then Summary := Summary + #$2714 + ' Ollama framework'               + #13#10
      else Summary := Summary + #$274C + ' Ollama framework  (FAILED)'     + #13#10;

    if SelectedModel = 'skip' then
      Summary := Summary + '   AI Model: skipped'                          + #13#10
    else if ResultModel = 0 then
      Summary := Summary + #$2714 + ' AI Model: ' + SelectedModel          + #13#10
    else
      Summary := Summary + #$274C + ' AI Model (' + SelectedModel + ')  (FAILED)' + #13#10;

    if ResultConfig
      then Summary := Summary + #$2714 + ' Configuration deployed'         + #13#10
      else Summary := Summary + #$274C + ' Configuration  (FAILED)'        + #13#10;

    Summary := Summary + #13#10;
    if HasFailure then
      Summary := Summary + 'Some components failed. See {app}\logs\install.log for details.'
    else
      Summary := Summary + 'Lotus is fully installed and ready to use!';

    if HasFailure then MsgBox(Summary, mbError, MB_OK)
    else               MsgBox(Summary, mbInformation, MB_OK);

  finally
    KillTimer(0, TimerId);
    UpdateLogs;
    StatusLabel.Caption := 'Installation complete!';
    WizardForm.NextButton.Enabled := True;
    WizardForm.NextButton.OnClick(WizardForm.NextButton);
  end;
end;

// ═══════════════════════════════════════════════════════════
// 10. WIZARD HOOKS
// ═══════════════════════════════════════════════════════════

procedure InitializeWizard;
begin
  CreateCustomPages;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = CustomInstallPage.ID then RunInstallSteps;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var Code: Integer;
begin
  if CurStep = ssInstall then
    Exec('taskkill.exe', '/F /IM Lotus.exe /T', '', SW_HIDE, ewWaitUntilTerminated, Code);
end;