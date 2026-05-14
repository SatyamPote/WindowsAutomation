"""AX focus monitoring via polling — replaces UIAutomation event handler."""

import logging
import threading
import time

logger = logging.getLogger(__name__)


class FocusObserver:
    """Polls for frontmost application changes and fires a callback on change."""

    POLL_INTERVAL = 0.5

    def __init__(self, callback):
        self._callback = callback
        self._thread: threading.Thread | None = None
        self._running = False
        self._current_pid: int | None = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="ax-focus-observer"
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _run(self) -> None:
        try:
            import AppKit
        except ImportError:
            logger.warning("AppKit not available — focus observer disabled")
            return

        workspace = AppKit.NSWorkspace.sharedWorkspace()
        while self._running:
            try:
                app = workspace.frontmostApplication()
                pid = int(app.processIdentifier()) if app else None
                if pid != self._current_pid:
                    self._current_pid = pid
                    try:
                        self._callback(pid)
                    except Exception:
                        logger.exception("Error in focus callback")
            except Exception:
                pass
            time.sleep(self.POLL_INTERVAL)
