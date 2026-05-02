# Lotus Installer System

This directory contains the necessary scripts and configurations to build a fully automated, production-ready Windows installer for the **Lotus Agent**.

## Overview

The setup system is powered by **Inno Setup** and includes a set of modular PowerShell scripts that automatically configure the environment on a fresh Windows PC. 

The installer handles the following tasks automatically:
1. **Python 3.11+** installation (with PATH configuration).
2. **Pip dependencies** installation from `requirements.txt`.
3. **Ollama** local AI runtime installation.
4. **Media Binaries**: Automatic download and extraction of `FFmpeg`, `yt-dlp`, and `mpv` to the `bin/` directory.
5. **AI Model Setup**: A custom UI page during setup lets the user choose between `phi3` (Fast), `mistral` (Balanced), or `llama3` (Smart). The installer pulls the selected model in the background.
6. **Post-Install**: Automatically generates a `config.json` file at `%ProgramData%\Lotus\config\`, ensures Ollama is running, and adds Lotus to the Windows Startup registry for silent background execution.

## Folder Structure

```
Lotus/
│
├── build.bat                   # PyInstaller build script
├── installer.iss               # Inno Setup configuration file
├── requirements.txt            # Python dependencies
│
├── install_scripts/            # Modular PowerShell installer scripts
│   ├── install_python.ps1      # Downloads and installs Python quietly
│   ├── install_requirements.ps1# Installs PyPI dependencies
│   ├── install_ollama.ps1      # Downloads and installs Ollama
│   ├── install_ffmpeg.ps1      # Downloads FFmpeg and places in bin/
│   ├── download_tools.ps1      # Downloads yt-dlp & mpv to bin/
│   ├── download_model.ps1      # Pulls selected Ollama model
│   └── post_install.ps1        # Generates .env and verifies services
│
├── bin/                        # (Created during install) Media tools
└── logs/                       # (Created during install) Installation & runtime logs
```

## Build Instructions

To generate the final `LotusSetup.exe` installer from scratch:

### Prerequisites (For the Developer)
- **Python 3.11+** installed on your build machine.
- **Inno Setup 6+** installed on your build machine.

### Step 1: Build the Executable
1. Open a command prompt or PowerShell in the `Lotus/` root folder.
2. Run the build script:
   ```cmd
   build.bat
   ```
3. This will compile `app.py` using PyInstaller into a standalone executable at `dist/Lotus.exe`.

### Step 2: Generate the Installer
1. Open the `installer.iss` file using **Inno Setup Compiler**.
2. Click **Compile** (or press `Ctrl+F9`).
3. Inno Setup will package `Lotus.exe`, the `assets/` folder, `requirements.txt`, and the `install_scripts/` into a single standalone executable.
4. The generated installer will be located in the `Output/` folder as `LotusSetup.exe`.

## Testing the Installer
Run `Output/LotusSetup.exe` on a fresh Windows machine (or VM). The installer will run with full administrative privileges to install everything automatically, show the model selection UI, execute all PowerShell scripts hidden from the user, and finally launch the Lotus Control Panel while adding it to system startup.

## Troubleshooting
If the installation fails at any point, check the detailed logs generated at:
`C:\ProgramData\Lotus\logs\install.log` (or within the extracted application directory).
Each PowerShell script strictly logs its operations, making it easy to identify which download or installation step failed.
