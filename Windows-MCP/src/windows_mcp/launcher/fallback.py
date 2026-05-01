def get_fallback_action(app_name: str) -> dict:
    """
    Returns an alternative launch action if the primary one fails.
    Returns None if no fallback is configured.
    """
    app_lower = app_name.lower()
    
    if "chrome" in app_lower:
        return {
            "app": "Edge",
            "cmd": "msedge.exe",
            "message": "Chrome failed. Falling back to Microsoft Edge."
        }
    if "whatsapp" in app_lower:
        return {
            "app": "WhatsApp Web",
            "cmd": "Start-Process https://web.whatsapp.com",
            "message": "Desktop WhatsApp failed. Falling back to WhatsApp Web."
        }
    if "word" in app_lower:
        # User requested to suggest opening .docx, but as a fallback action we can't do much natively.
        return {
            "app": "WordPad",
            "cmd": "write.exe",
            "message": "Microsoft Word failed. Falling back to WordPad."
        }
        
    return None
