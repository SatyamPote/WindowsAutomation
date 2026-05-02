import logging
import subprocess

logger = logging.getLogger(__name__)


class ShellExecutor:
    @staticmethod
    def execute(command: str, timeout: int = 30) -> tuple[str, int]:
        try:
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = (result.stdout + result.stderr).strip()
            return output, result.returncode
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s", 1
        except Exception as e:
            return f"Error: {e}", 1


class AppleScriptExecutor:
    @staticmethod
    def execute(script: str, timeout: int = 10) -> tuple[str, int]:
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = (result.stdout + result.stderr).strip()
            return output, result.returncode
        except subprocess.TimeoutExpired:
            return f"AppleScript timed out after {timeout}s", 1
        except Exception as e:
            return f"Error: {e}", 1

    @staticmethod
    def notify(title: str, message: str) -> None:
        script = f'display notification "{message}" with title "{title}"'
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
        except Exception as e:
            logger.warning("Notification failed: %s", e)
