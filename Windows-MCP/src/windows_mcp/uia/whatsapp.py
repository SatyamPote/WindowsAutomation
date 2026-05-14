import time
import logging
import subprocess
import os

logger = logging.getLogger("whatsapp_automation")

def focus_window_safe(title="WhatsApp"):
    import pygetwindow as gw
    import pyautogui
    
    # Retry loop
    for _ in range(3):
        windows = gw.getWindowsWithTitle(title)
        win = windows[0] if windows else None
        
        if win:
            logger.info(f"{title} found. Bringing to front...")
            try:
                if win.isMinimized:
                    win.restore()
                win.maximize()
                win.activate()
                time.sleep(1.5)
                # Verify it's actually focused
                active_win = gw.getActiveWindow()
                if active_win and title.lower() in active_win.title.lower():
                    return True
            except Exception as e:
                logger.warning(f"Failed to focus window: {e}")
                
        # Launch if not found
        logger.info(f"{title} not focused or not found. Launching/Switching...")
        subprocess.Popen(f'start {title.lower()}:', shell=True)
        time.sleep(4.0)
        
    return False

def send_message(contact_query: str, message_or_file: str, is_file: bool = False, file_path: str = "") -> dict:
    """
    Automates WhatsApp Desktop to send a message or file to a specific contact.
    """
    try:
        import pyautogui
    except ImportError:
        return {"success": False, "message": "PyAutoGUI is not installed.", "error": "Missing dependency"}

    logger.info(f"Starting WhatsApp automation for contact: {contact_query}")
    
    if not focus_window_safe("WhatsApp"):
        return {"success": False, "message": "Failed to focus WhatsApp.", "error": "Window focus failed"}
    
    screenWidth, screenHeight = pyautogui.size()
    
    # Safe click middle top to ensure focus inside app
    pyautogui.click(screenWidth // 2, 20) 
    time.sleep(0.5)
    
    # Search
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(1.5)
    
    # Type contact query cleanly
    pyautogui.write(contact_query.strip(), interval=0.05)
    time.sleep(2.0)
    
    # Open chat
    pyautogui.press('enter')
    time.sleep(2.0)
    
    # Click safe coordinate in message box area
    pyautogui.click(screenWidth // 2, screenHeight - 100)
    time.sleep(0.5)
    
    if is_file:
        real_path = file_path
        if not os.path.exists(real_path):
            found = False
            for base in [os.getcwd(), os.path.expanduser("~/Downloads"), os.path.expanduser("~/Documents")]:
                check_path = os.path.join(base, file_path)
                if os.path.exists(check_path):
                    real_path = check_path
                    found = True
                    break
            if not found:
                return {"success": False, "message": "File not found.", "error": f"Could not locate {file_path}"}
        
        try:
            script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $file = [System.Collections.Specialized.StringCollection]::new()
            $file.Add("{real_path}")
            [System.Windows.Forms.Clipboard]::SetFileDropList($file)
            '''
            subprocess.run(["powershell", "-command", script], check=True)
            time.sleep(1.0)
            
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(2.0)
            pyautogui.press('enter')
            time.sleep(1.0)
            return {"success": True, "message": f"File successfully sent to {contact_query}.", "error": None}
        except Exception as e:
            return {"success": False, "message": "Failed to attach file.", "error": str(e)}
    else:
        # Type message cleanly
        clean_message = message_or_file.strip()
        if clean_message:
            pyautogui.write(clean_message, interval=0.02)
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(1.0)
            
        return {"success": True, "message": f"WhatsApp message successfully sent to {contact_query}.", "error": None}
