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
Source: "dist\Lotus.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "install_scripts\*"; DestDir: "{app}\install_scripts"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Lotus Control Panel"; Filename: "{app}\Lotus.exe"; IconFilename: "{app}\assets\lotus_icon.ico"
Name: "{autodesktop}\Lotus"; Filename: "{app}\Lotus.exe"; IconFilename: "{app}\assets\lotus_icon.ico"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "LotusControlPanel"; ValueData: """{app}\Lotus.exe"" --bot-service"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Lotus.exe"; Description: "Launch Lotus"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "reg"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v LotusControlPanel /f"; Flags: runhidden

[Code]
var
  ModelPage: TInputOptionWizardPage;
  ConfigPage: TInputQueryWizardPage;
  CustomInstallPage: TWizardPage;
  LogMemo: TMemo;
  ProgressBack: TLabel;
  ProgressFill: TLabel;
  StatusLabel: TLabel;
  TimerId: LongWord;
  TimerCallback: LongWord;
  LastLogLines: Integer;
  LogFilePath: String;
  ResultPython: Integer;
  ResultRequirements: Integer;
  ResultFFmpeg: Integer;
  ResultTools: Integer;
  ResultOllama: Integer;
  ResultModel: Integer;
  ResultPostInstall: Integer;
  ResultConfig: Boolean;

function SetTimer(hWnd: LongWord; nIDEvent, uElapse: LongWord; lpTimerFunc: LongWord): LongWord; external 'SetTimer@user32.dll stdcall';
function KillTimer(hWnd: LongWord; uIDEvent: LongWord): Boolean; external 'KillTimer@user32.dll stdcall';
function SendMessage(hWnd: LongWord; Msg: LongWord; wParam, lParam: LongInt): LongInt; external 'SendMessageW@user32.dll stdcall';

const
  EM_SETSEL = $00B1;
  EM_SCROLLCARET = $00B7;

procedure UpdateLogs();
var
  LogLines: TArrayOfString;
  I: Integer;
begin
  if FileExists(LogFilePath) then
  begin
    // Use LoadStringsFromFile but be aware it reads the whole file
    // For larger logs, this might need a TFileStream approach
    if LoadStringsFromFile(LogFilePath, LogLines) then
    begin
      if GetArrayLength(LogLines) > LastLogLines then
      begin
        for I := LastLogLines to GetArrayLength(LogLines) - 1 do
        begin
          LogMemo.Lines.Add(LogLines[I]);
        end;
        LastLogLines := GetArrayLength(LogLines);
        // Auto-scroll to bottom using SendMessage for smoothness
        SendMessage(LogMemo.Handle, EM_SETSEL, Length(LogMemo.Text), Length(LogMemo.Text));
        SendMessage(LogMemo.Handle, EM_SCROLLCARET, 0, 0);
      end;
    end;
  end;
end;

procedure TimerProc(Wnd: LongWord; Msg: LongWord; TimerID: LongWord; Time: LongWord);
begin
  UpdateLogs();
end;

function RunHidden(Command: String; StatusMsg: String; ProgressValue: Integer): Integer;
var
  ResultCode: Integer;
begin
  StatusLabel.Caption := StatusMsg;
  UpdateLogs();
  Exec('powershell.exe', '-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "' + Command + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  ProgressFill.Width := (ProgressBack.Width * ProgressValue) div 100;
  UpdateLogs();
  Result := ResultCode;
end;

procedure CreateCustomPages;
begin
  ModelPage := CreateInputOptionPage(wpSelectTasks,
    'AI Model Selection', 'Choose the AI model you want to install.',
    'Please select the model that best fits your system capabilities. The model will be downloaded during installation.',
    True, False);
  ModelPage.Add('Fast (Low RAM) -> phi3 (~2.3GB, fastest)');
  ModelPage.Add('Balanced -> mistral (~4.1GB, balanced)');
  ModelPage.Add('Smart -> llama3 (~4.7GB+, best reasoning)');
  ModelPage.Add('Skip model download');
  ModelPage.Values[0] := True;

  ConfigPage := CreateInputQueryPage(ModelPage.ID,
    'Lotus Configuration', 'Enter your Telegram Bot details.',
    'Please enter the required information to configure your bot. You can get a bot token from @BotFather on Telegram.');
  ConfigPage.Add('Telegram Bot Token:', False);
  ConfigPage.Add('Allowed User ID (Numeric):', False);
  ConfigPage.Add('Your Name:', False);

  CustomInstallPage := CreateCustomPage(wpInstalling, 'Installing Lotus AI Agent', 'Please wait while setup installs components');
  
  StatusLabel := TLabel.Create(CustomInstallPage);
  StatusLabel.Parent := CustomInstallPage.Surface;
  StatusLabel.Left := 0;
  StatusLabel.Top := 0;
  StatusLabel.Width := CustomInstallPage.SurfaceWidth;
  StatusLabel.Height := 20;
  StatusLabel.Caption := 'Preparing to install...';
  StatusLabel.Font.Style := [fsBold];

  ProgressBack := TLabel.Create(CustomInstallPage);
  ProgressBack.Parent := CustomInstallPage.Surface;
  ProgressBack.Left := 0;
  ProgressBack.Top := 25;
  ProgressBack.Width := CustomInstallPage.SurfaceWidth;
  ProgressBack.Height := 15;
  ProgressBack.Color := clSilver;
  ProgressBack.Transparent := False;
  ProgressBack.Caption := '';

  ProgressFill := TLabel.Create(CustomInstallPage);
  ProgressFill.Parent := CustomInstallPage.Surface;
  ProgressFill.Left := 0;
  ProgressFill.Top := 25;
  ProgressFill.Width := 0;
  ProgressFill.Height := 15;
  ProgressFill.Color := $00B469FF;
  ProgressFill.Transparent := False;
  ProgressFill.Caption := '';

  LogMemo := TMemo.Create(CustomInstallPage);
  LogMemo.Parent := CustomInstallPage.Surface;
  LogMemo.Left := 0;
  LogMemo.Top := 55;
  LogMemo.Width := CustomInstallPage.SurfaceWidth;
  LogMemo.Height := CustomInstallPage.SurfaceHeight - 55;
  LogMemo.ReadOnly := True;
  LogMemo.ScrollBars := ssVertical;
  LogMemo.Color := clBlack;
  LogMemo.Font.Color := clLime;
  LogMemo.Font.Name := 'Consolas';
  LogMemo.WordWrap := False;

  LogMemo.WordWrap := False;
end;

function GetSelectedModel(): string;
begin
  if ModelPage.Values[0] then Result := 'phi3'
  else if ModelPage.Values[1] then Result := 'mistral'
  else if ModelPage.Values[2] then Result := 'llama3'
  else Result := 'skip';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Token, UserID: String;
  I: Integer;
begin
  Result := True;
  if CurPageID = ConfigPage.ID then
  begin
    Token := Trim(ConfigPage.Values[0]);
    UserID := Trim(ConfigPage.Values[1]);
    
    if Length(Token) = 0 then
    begin
      MsgBox('Telegram Bot Token cannot be empty.', mbError, MB_OK);
      Result := False;
    end
    else if Length(UserID) > 0 then
    begin
      for I := 1 to Length(UserID) do
      begin
        if (UserID[I] < '0') or (UserID[I] > '9') then
        begin
          MsgBox('Allowed User ID must be numeric.', mbError, MB_OK);
          Result := False;
          Break;
        end;
      end;
    end;
  end;
end;

function StatusIcon(Code: Integer): String;
begin
  if Code = 0 then Result := '✅'
  else Result := '❌';
end;

procedure RunInstallSteps;
var
  ScriptsDir: String;
  EnvContent: TArrayOfString;
  Summary: String;
  ModelName: String;
  HasFailure: Boolean;
begin
  ScriptsDir := ExpandConstant('{app}\install_scripts');
  LogFilePath := ExpandConstant('{app}\logs\install.log');
  ForceDirectories(ExpandConstant('{app}\logs'));
  LastLogLines := 0;
  ResultConfig := False;

  TimerCallback := CreateCallback(@TimerProc);
  TimerId := SetTimer(0, 0, 1000, TimerCallback);

  try
    WizardForm.NextButton.Enabled := False;
    WizardForm.BackButton.Enabled := False;
    WizardForm.CancelButton.Enabled := True;

    ProgressFill.Width := (ProgressBack.Width * 10) div 100;
    UpdateLogs();

    RunHidden(ScriptsDir + '\system_check.ps1', '10% -> Checking system requirements...', 10);
    ResultPython := RunHidden(ScriptsDir + '\install_python.ps1', '20% -> Installing Python...', 20);
    ResultRequirements := RunHidden(ScriptsDir + '\install_requirements.ps1', '40% -> Installing dependencies...', 40);
    ResultFFmpeg := RunHidden(ScriptsDir + '\install_ffmpeg.ps1', '50% -> Installing FFmpeg...', 50);
    ResultTools := RunHidden(ScriptsDir + '\download_tools.ps1', '55% -> Downloading media tools (yt-dlp, mpv)...', 55);
    ResultOllama := RunHidden(ScriptsDir + '\install_ollama.ps1', '70% -> Installing Ollama...', 70);
    
    ModelName := GetSelectedModel();
    if ModelName = 'skip' then
    begin
      ResultModel := 0;
      Log('Model download skipped by user.');
    end
    else
    begin
      StatusLabel.Caption := '85% -> Downloading AI model (' + ModelName + ')...';
      UpdateLogs();
      ResultModel := RunHidden(ScriptsDir + '\download_model.ps1 -ModelName ' + ModelName, '85% -> Downloading AI model (' + ModelName + ')...', 85);
      
      if ResultModel <> 0 then 
      begin
        Log('Model download process returned error code: ' + IntToStr(ResultModel));
        // We continue anyway but mark as failed in summary if needed
      end;
    end;
    StatusLabel.Caption := '95% -> Creating configuration...';
    SetArrayLength(EnvContent, 7);
    EnvContent[0] := '{';
    EnvContent[1] := '  "bot_token": "' + Trim(ConfigPage.Values[0]) + '",';
    EnvContent[2] := '  "allowed_user_ids": "' + Trim(ConfigPage.Values[1]) + '",';
    EnvContent[3] := '  "user_name": "' + Trim(ConfigPage.Values[2]) + '",';
    EnvContent[4] := '  "model_name": "' + ModelName + '",';
    EnvContent[5] := '  "created_at": "Installer Setup"';
    EnvContent[6] := '}';
    ForceDirectories(ExpandConstant('{commonappdata}\Lotus\config'));
    ResultConfig := SaveStringsToFile(ExpandConstant('{commonappdata}\Lotus\config\config.json'), EnvContent, False);
    ProgressFill.Width := (ProgressBack.Width * 95) div 100;
    UpdateLogs();
    
    ResultPostInstall := RunHidden(ScriptsDir + '\post_install.ps1', '100% -> Finalizing setup...', 100);
    
    { Build dynamic summary based on actual results }
    HasFailure := False;
    Summary := 'Installation Summary:' + #13#10 + #13#10;
    
    Summary := Summary + StatusIcon(ResultPython) + ' Python installation';
    if ResultPython <> 0 then begin Summary := Summary + ' (FAILED)'; HasFailure := True; end;
    Summary := Summary + #13#10;
    
    Summary := Summary + StatusIcon(ResultRequirements) + ' Python dependencies';
    if ResultRequirements <> 0 then begin Summary := Summary + ' (FAILED)'; HasFailure := True; end;
    Summary := Summary + #13#10;
    
    Summary := Summary + StatusIcon(ResultFFmpeg) + ' FFmpeg installation';
    if ResultFFmpeg <> 0 then begin Summary := Summary + ' (FAILED)'; HasFailure := True; end;
    Summary := Summary + #13#10;
    
    Summary := Summary + StatusIcon(ResultTools) + ' Media tools (yt-dlp, mpv)';
    if ResultTools <> 0 then begin Summary := Summary + ' (FAILED)'; HasFailure := True; end;
    Summary := Summary + #13#10;
    
    Summary := Summary + StatusIcon(ResultOllama) + ' Ollama framework';
    if ResultOllama <> 0 then begin Summary := Summary + ' (FAILED)'; HasFailure := True; end;
    Summary := Summary + #13#10;
    
    if ModelName = 'skip' then
      Summary := Summary + '⏭ AI Model download (skipped)' + #13#10
    else if ResultModel = 0 then
      Summary := Summary + '✅ AI Model (' + ModelName + ') installed and verified' + #13#10
    else
      Summary := Summary + '❌ AI Model (' + ModelName + ') download failed' + #13#10;
    
    if ResultConfig then
      Summary := Summary + '✅ Configuration deployed' + #13#10
    else begin
      Summary := Summary + '❌ Configuration deployment (FAILED)' + #13#10;
      HasFailure := True;
    end;
    
    Summary := Summary + #13#10;
    if HasFailure then
      Summary := Summary + '⚠ Some components failed. Check the install log for details.'
    else
      Summary := Summary + 'Lotus is now fully integrated with your system!';
    
    if HasFailure then
      MsgBox(Summary, mbError, MB_OK)
    else
      MsgBox(Summary, mbInformation, MB_OK);
    
  finally
    KillTimer(0, TimerId);
    UpdateLogs();
    StatusLabel.Caption := 'Installation Complete!';
    WizardForm.NextButton.Enabled := True;
    WizardForm.CancelButton.Enabled := True;
    WizardForm.NextButton.OnClick(WizardForm.NextButton);
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = CustomInstallPage.ID then
  begin
    RunInstallSteps;
  end;
end;

procedure InitializeWizard;
begin
  CreateCustomPages;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
  begin
    Exec('taskkill.exe', '/F /IM Lotus.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;