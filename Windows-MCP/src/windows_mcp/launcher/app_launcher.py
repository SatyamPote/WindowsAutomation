import os
import time
import psutil
import logging
import subprocess
from .detection import find_executable

# Setup dedicated launcher logging
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("app_launcher")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("logs/launcher.log", encoding="utf-8")
formatter = logging.Formatter('%(asctime)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

def verify_process_started(target_name: str, pid: int = None, method: str = "") -> bool:
    if pid and psutil.pid_exists(pid):
        try:
            p = psutil.Process(pid)
            if p.name().lower() not in ["cmd.exe", "powershell.exe", "conhost.exe"]:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    target = target_name.lower()
    if not target.endswith(".exe"):
        target += ".exe"
        
    for p in psutil.process_iter(['name']):
        try:
            if p.info['name'] and p.info['name'].lower() == target:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    return False

def _execute_powershell(cmd: str):
    try:
        from windows_mcp.desktop.powershell import PowerShellExecutor
        out, code = PowerShellExecutor.execute_command(cmd, timeout=10)
        return code == 0, out
    except ImportError:
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
        return res.returncode == 0, res.stdout

def launch_app(app_name: str, extra_args: str = "") -> dict:
    start_time = time.time()
    
    result = {
        "success": False,
        "app": app_name,
        "method": None,
        "message": "",
        "pid": None,
        "error": None
    }
    
    args_str = f" {extra_args}" if extra_args else ""
    success = False

    # 1. Try direct executable: subprocess.Popen(app_name)
    try:
        proc = subprocess.Popen(app_name + args_str, shell=True)
        time.sleep(1.0)
        success = verify_process_started(app_name, proc.pid)
    except Exception as e:
        pass

    # 2. If fails: use Windows shell: os.system("start " + app_name)
    if not success:
        try:
            # os.system("start " + app_name)
            cmd_app = f'"{app_name}"' if " " in app_name and not app_name.startswith('"') else app_name
            os.system(f'start "" {cmd_app}')
            time.sleep(1.0)
            success = verify_process_started(app_name)
        except Exception as e:
            pass

    # 3. If still fails: search in installed apps cache and run full path
    if not success:
        found_path = find_executable(app_name)
        if found_path:
            try:
                proc = subprocess.Popen(f'"{found_path}"{args_str}', shell=True)
                time.sleep(1.0)
                success = verify_process_started(os.path.basename(found_path), proc.pid)
            except Exception as e:
                pass

    if success:
        result["success"] = True
        result["message"] = "Opened successfully"
    else:
        result["success"] = False
        result["message"] = "Failed to open"
        
    logger.info(f"Requested: {app_name} | Success: {success} | Time: {int((time.time() - start_time)*1000)}ms")
    return result
