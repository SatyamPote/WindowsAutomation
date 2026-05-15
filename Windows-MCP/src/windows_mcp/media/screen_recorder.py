import cv2
import mss
import numpy as np
import time
import os
import threading
from datetime import datetime
from windows_mcp.paths import get_lotus_storage_dir

class ScreenRecorder:
    def __init__(self):
        self.recording = False
        self.output_path = None

    def record(self, seconds=10):
        if self.recording:
            return False, "Already recording!"
        
        self.recording = True
        thread = threading.Thread(target=self._record_loop, args=(seconds,))
        thread.start()
        return True, f"🎥 Recording screen for {seconds} seconds..."

    def _record_loop(self, seconds):
        try:
            with mss.mss() as sct:
                # Use the primary monitor
                monitor = sct.monitors[1]
                width = monitor["width"]
                height = monitor["height"]
                
                # Setup output
                storage_dir = os.path.join(get_lotus_storage_dir(), "recordings")
                os.makedirs(storage_dir, exist_ok=True)
                
                filename = f"record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                self.output_path = os.path.join(storage_dir, filename)
                
                # Define codec and create VideoWriter object
                # Use 'avc1' or 'mp4v'
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(self.output_path, fourcc, 10.0, (width, height))
                
                start_time = time.time()
                while (time.time() - start_time) < seconds and self.recording:
                    # Capture screen
                    img = sct.grab(monitor)
                    # Convert to numpy array
                    frame = np.array(img)
                    # Convert from BGRA to BGR
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    # Write frame
                    out.write(frame)
                    # Small sleep to aim for ~10 FPS
                    time.sleep(0.1)
                
                out.release()
                self.recording = False
        except Exception as e:
            self.recording = False
            print(f"Recording error: {e}")

    def get_last_recording(self):
        if self.recording:
            return None
        return self.output_path

screen_recorder = ScreenRecorder()
