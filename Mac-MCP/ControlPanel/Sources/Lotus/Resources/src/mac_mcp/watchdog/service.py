import logging
from mac_mcp.ax.events import FocusObserver

logger = logging.getLogger(__name__)


class WatchDog:
    def __init__(self):
        self._observer: FocusObserver | None = None
        self._focus_callback = None

    def set_focus_callback(self, callback) -> None:
        self._focus_callback = callback

    def start(self) -> None:
        cb = self._focus_callback or (lambda pid: None)
        self._observer = FocusObserver(callback=cb)
        self._observer.start()
        logger.debug("WatchDog started")

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
        logger.debug("WatchDog stopped")
