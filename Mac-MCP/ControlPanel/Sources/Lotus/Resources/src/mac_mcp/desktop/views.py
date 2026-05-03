from mac_mcp.tree.views import TreeState, BoundingBox
from dataclasses import dataclass
from tabulate import tabulate
from PIL.Image import Image
from enum import Enum


class Browser(Enum):
    CHROME = "Google Chrome"
    EDGE = "Microsoft Edge"
    FIREFOX = "firefox"
    SAFARI = "Safari"
    ARC = "Arc"
    BRAVE = "Brave Browser"

    @classmethod
    def has_process(cls, process_name: str) -> bool:
        return any(process_name.lower() in b.value.lower() for b in cls)


class Status(Enum):
    MAXIMIZED = "Maximized"
    MINIMIZED = "Minimized"
    NORMAL = "Normal"
    HIDDEN = "Hidden"


@dataclass
class Window:
    name: str
    is_browser: bool
    depth: int
    status: Status
    bounding_box: BoundingBox
    handle: int      # process ID on macOS
    process_id: int

    def to_row(self):
        return [
            self.name,
            self.depth,
            self.status.value,
            self.bounding_box.width,
            self.bounding_box.height,
            self.process_id,
        ]


@dataclass
class Size:
    width: int
    height: int

    def to_string(self):
        return f"({self.width},{self.height})"


@dataclass
class DesktopState:
    active_desktop: dict
    all_desktops: list[dict]
    active_window: Window | None
    windows: list[Window]
    screenshot: Image | None = None
    cursor_position: tuple[int, int] | None = None
    screenshot_original_size: Size | None = None
    screenshot_region: BoundingBox | None = None
    screenshot_displays: list[int] | None = None
    screenshot_backend: str | None = None
    tree_state: TreeState | None = None
    capture_sec: float = 0.0

    def active_desktop_to_string(self):
        desktop_name = self.active_desktop.get("name")
        return tabulate([[desktop_name]], headers=["Name"], tablefmt="simple")

    def desktops_to_string(self):
        rows = [[d.get("name")] for d in self.all_desktops]
        return tabulate(rows, headers=["Name"], tablefmt="simple")

    def active_window_to_string(self):
        if not self.active_window:
            return "No active window found"
        headers = ["Name", "Depth", "Status", "Width", "Height", "PID"]
        return tabulate([self.active_window.to_row()], headers=headers, tablefmt="simple")

    def windows_to_string(self):
        if not self.windows:
            return "No windows found"
        headers = ["Name", "Depth", "Status", "Width", "Height", "PID"]
        rows = [w.to_row() for w in self.windows]
        return tabulate(rows, headers=headers, tablefmt="simple")
