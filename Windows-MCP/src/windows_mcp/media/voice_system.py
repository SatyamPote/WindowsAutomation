import os
import time
import logging
import threading
import json
import subprocess
import pyttsx3
import pythoncom
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER

logger = logging.getLogger(__name__)

class VoiceSystem:
    def __init__(self, storage_dir, config_path):
        self.storage_dir = storage_dir
        self.config_path = config_path
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.current_proc = None
        self.lock = threading.Lock()
        
        # Default Config
        self.config = {
            "voice_enabled": True,
            "volume_level": 100,
            "auto_voice": False,
            "style": "female",
            "speed": 1.0
        }
        self.load_config()
        
        # Setup Logger
        log_dir = os.path.join(os.path.dirname(os.path.dirname(self.storage_dir)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.voice_logger = logging.getLogger("voice_system")
        handler = logging.FileHandler(os.path.join(log_dir, "voice.log"))
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.voice_logger.addHandler(handler)
        self.voice_logger.setLevel(logging.INFO)

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config.update(json.load(f))
        except Exception as e:
            logger.error(f"Failed to load voice config: {e}")

    def save_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save voice config: {e}")

    def set_max_volume(self):
        if self.config.get("volume_level", 100) == 0: return
        try:
            pythoncom.CoInitialize()
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            # If the direct Activate fails, we try to find it in the list
            try:
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            except:
                from pycaw.pycaw import CLSID_MMDeviceEnumerator, IMMDeviceEnumerator
                import comtypes
                enumerator = comtypes.CoCreateInstance(CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_INPROC_SERVER)
                endpoint = enumerator.GetDefaultAudioEndpoint(0, 1) # eRender, eMultimedia
                interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(1.0, None)
        except Exception as e:
            self.voice_logger.error(f"Failed to set max volume: {e}")

    def _get_voice_id(self, engine):
        voices = engine.getProperty('voices')
        style = self.config.get("style", "female")
        
        # Prioritize "Zira" or "Hazel" for "sweet" female voice
        if style == "female":
            for voice in voices:
                if any(n in voice.name.lower() for n in ["zira", "hazel", "female"]):
                    return voice.id
        elif style == "male":
            for voice in voices:
                if any(n in voice.name.lower() for n in ["david", "male"]):
                    return voice.id
        
        return voices[0].id if voices else None

    def generate_audio(self, text):
        """Generates WAV file and returns path."""
        filename = f"tts_{int(time.time())}.wav"
        save_path = os.path.join(self.storage_dir, filename)
        
        try:
            pythoncom.CoInitialize()
            temp_engine = pyttsx3.init()
            
            # Set Voice
            voice_id = self._get_voice_id(temp_engine)
            if voice_id:
                temp_engine.setProperty('voice', voice_id)
            
            # Set Rate (Sweetness)
            speed = self.config.get("speed", 0.9)
            temp_engine.setProperty('rate', int(200 * speed))
            
            temp_engine.save_to_file(text, save_path)
            temp_engine.runAndWait()
            
            # Cleanup old files (Keep last 20)
            self.cleanup_storage()
            
            return save_path
        except Exception as e:
            self.voice_logger.error(f"Audio generation failed for text '{text}': {e}")
            return None

    def play_audio(self, path):
        """Plays audio file locally at max volume in a non-blocking way."""
        if not self.config.get("voice_enabled"): return
        
        def _play():
            with self.lock:
                self.stop_voice()
                self.set_max_volume()
                try:
                    # Use powershell to play wav silently so we can kill it
                    # (No extra libraries needed for playing WAV)
                    cmd = f'powershell -c "(New-Object Media.SoundPlayer \'{path}\').PlaySync()"'
                    self.current_proc = subprocess.Popen(cmd, shell=True)
                    self.current_proc.wait()
                except Exception as e:
                    self.voice_logger.error(f"Playback failed for {path}: {e}")

        threading.Thread(target=_play, daemon=True).start()

    def stop_voice(self):
        """Instantly stops any playing voice audio."""
        if self.current_proc:
            try:
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.current_proc.pid)], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.current_proc = None
            except: pass

    def speak(self, text, send_to_tg_callback=None):
        """High level: generate, play locally, and trigger TG delivery."""
        if not self.config.get("voice_enabled"): return
        
        def _task():
            path = self.generate_audio(text)
            if path:
                self.play_audio(path)
                if send_to_tg_callback:
                    send_to_tg_callback(path)
                self.voice_logger.info(f"Spoke: {text}")

        threading.Thread(target=_task, daemon=True).start()

    def cleanup_storage(self):
        """Keep only last 20 files in storage/audio."""
        try:
            files = [os.path.join(self.storage_dir, f) for f in os.listdir(self.storage_dir) if f.endswith(".wav")]
            files.sort(key=os.path.getmtime)
            if len(files) > 20:
                for f in files[:-20]:
                    try: os.remove(f)
                    except: pass
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def toggle_voice(self, enabled):
        self.config["voice_enabled"] = enabled
        self.save_config()
        return f"🎙️ Voice Feedback: {'ON' if enabled else 'OFF'}"

    @property
    def auto_voice(self):
        return self.config.get("auto_voice", False)

    @auto_voice.setter
    def auto_voice(self, value):
        self.config["auto_voice"] = value
        self.save_config()

    def generate(self, text):
        """Alias for generate_audio for backward compatibility."""
        return self.generate_audio(text)

    def toggle_auto(self, status):
        """Backward compatibility for toggle_auto."""
        self.auto_voice = status
        return True
