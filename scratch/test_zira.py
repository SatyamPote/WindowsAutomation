import pyttsx3
import os
import time

def test_zira():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    zira = None
    for v in voices:
        if "zira" in v.name.lower():
            zira = v.id
            break
    
    if not zira:
        print("Zira not found!")
        return

    print(f"Testing Zira: {zira}")
    engine.setProperty('voice', zira)
    path = os.path.abspath("zira_test.wav")
    if os.path.exists(path): os.remove(path)
    
    engine.save_to_file("This is a test of the sweet female voice.", path)
    engine.runAndWait()
    
    if os.path.exists(path):
        print(f"Success! File created at {path}")
        print(f"Size: {os.path.getsize(path)} bytes")
    else:
        print("Failed to create file.")

if __name__ == "__main__":
    test_zira()
