import sys
import os
import traceback
import logging
import platform
import json
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

def get_log_dir():
    program_data = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
    log_dir = os.path.join(program_data, "Lotus", "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def show_crash_dialog(error_msg):
    try:
        root = tk.Tk()
        root.withdraw()
        # Keep dialog simple and informative
        clean_msg = str(error_msg).split('\n')[0]
        messagebox.showerror("Lotus Startup Error", 
            f"Lotus encountered a critical error during startup:\n\n{clean_msg}\n\n"
            f"A detailed log has been saved to:\n{get_log_dir()}\\crash.log\n\n"
            "Please send this log to the developer.")
        root.destroy()
    except:
        print(f"CRITICAL ERROR: {error_msg}")

def global_exception_handler(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logging.critical(f"Uncaught Exception:\n{error_msg}")
    
    # Write to a dedicated crash log
    crash_log = os.path.join(get_log_dir(), "crash.log")
    try:
        with open(crash_log, "a") as f:
            f.write(f"\n--- CRASH AT {datetime.now()} ---\n")
            f.write(error_msg)
            f.write("-" * 30 + "\n")
    except:
        pass
    
    show_crash_dialog(value)
    sys.exit(1)

def init_diagnostics():
    """Initialize startup logging and crash handling."""
    # Set up global logging
    log_file = os.path.join(get_log_dir(), "startup.log")
    
    # Clean old startup log
    if os.path.exists(log_file):
        try: os.remove(log_file)
        except: pass

    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    # Set exception hook
    sys.excepthook = global_exception_handler
    
    # Log environment dump
    logging.info("=== Lotus Production Diagnostics ===")
    logging.info(f"Time: {datetime.now()}")
    logging.info(f"OS: {platform.platform()}")
    logging.info(f"Arch: {platform.machine()}")
    logging.info(f"Python: {sys.version}")
    logging.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    logging.info(f"Executable: {sys.executable}")
    logging.info(f"MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
    logging.info(f"CWD: {os.getcwd()}")
    
    # Check for critical assets
    try:
        from windows_mcp.assets import verify_asset_integrity
        missing = verify_asset_integrity()
        if missing:
            logging.error(f"Missing Assets: {', '.join(missing)}")
        else:
            logging.info("All critical assets verified.")
    except Exception as e:
        logging.error(f"Asset verification failed: {e}")
    
    logging.info("=== Diagnostics Initialized ===")
