from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING

from PIL import ImageDraw, ImageFont, Image

try:
    from pynput.keyboard import Controller as KeyboardController, Key
    from pynput.mouse import Controller as MouseController, Button
    _PYNPUT_AVAILABLE = True
except Exception:
    _PYNPUT_AVAILABLE = False
    Key = None
    Button = None

import mac_mcp.ax.core as ax_core
from mac_mcp.desktop import screenshot as screenshot_capture
from mac_mcp.desktop.views import Browser, DesktopState, Size, Status, Window
from mac_mcp.tree.views import BoundingBox

if TYPE_CHECKING:
    from mac_mcp.tree.service import Tree

logger = logging.getLogger(__name__)

MAX_IMAGE_WIDTH = 1920
MAX_IMAGE_HEIGHT = 1080

# Lazy singletons — created on first use after server starts
_keyboard: "KeyboardController | None" = None
_mouse: "MouseController | None" = None


def _get_keyboard() -> "KeyboardController":
    global _keyboard
    if _keyboard is None:
        if not _PYNPUT_AVAILABLE:
            raise RuntimeError("pynput not available — keyboard input disabled")
        _keyboard = KeyboardController()
    return _keyboard


def _get_mouse() -> "MouseController":
    global _mouse
    if _mouse is None:
        if not _PYNPUT_AVAILABLE:
            raise RuntimeError("pynput not available — mouse input disabled")
        _mouse = MouseController()
    return _mouse


# Key alias table: user-friendly name → pynput Key
def _build_key_aliases() -> dict:
    if not _PYNPUT_AVAILABLE:
        return {}
    return {
        "ctrl":       Key.ctrl,
        "control":    Key.ctrl,
        "shift":      Key.shift,
        "alt":        Key.alt,
        "option":     Key.alt,
        "cmd":        Key.cmd,
        "command":    Key.cmd,
        "windows":    Key.cmd,
        "meta":       Key.cmd,
        "super":      Key.cmd,
        "enter":      Key.enter,
        "return":     Key.enter,
        "tab":        Key.tab,
        "space":      Key.space,
        "backspace":  Key.backspace,
        "delete":     Key.delete,
        "escape":     Key.esc,
        "esc":        Key.esc,
        "up":         Key.up,
        "down":       Key.down,
        "left":       Key.left,
        "right":      Key.right,
        "home":       Key.home,
        "end":        Key.end,
        "pageup":     Key.page_up,
        "pagedown":   Key.page_down,
        "f1":  Key.f1,  "f2":  Key.f2,  "f3":  Key.f3,  "f4":  Key.f4,
        "f5":  Key.f5,  "f6":  Key.f6,  "f7":  Key.f7,  "f8":  Key.f8,
        "f9":  Key.f9,  "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
        "capslock":   Key.caps_lock,
    }


_KEY_ALIASES: dict = {}


def _get_key_aliases() -> dict:
    global _KEY_ALIASES
    if not _KEY_ALIASES and _PYNPUT_AVAILABLE:
        _KEY_ALIASES = _build_key_aliases()
    return _KEY_ALIASES


def _resolve_key(k: str):
    """Resolve a key string to a pynput Key or single char."""
    aliases = _get_key_aliases()
    lower = k.lower().strip()
    if lower in aliases:
        return aliases[lower]
    if len(k) == 1:
        return k
    raise ValueError(f"Unknown key: {k!r}")


# Label colours cycling through a palette
_LABEL_COLOURS = [
    "#FF3B30", "#FF9500", "#FFCC00", "#34C759", "#007AFF",
    "#5856D6", "#FF2D55", "#AF52DE", "#00C7BE", "#FF6B35",
]


def _screenshot_scale() -> float:
    try:
        val = float(os.getenv("MAC_MCP_SCREENSHOT_SCALE", "1.0"))
        return max(0.1, min(1.0, val))
    except ValueError:
        return 1.0


def _snapshot_profile_enabled() -> bool:
    return os.getenv("MAC_MCP_PROFILE_SNAPSHOT", "").strip().lower() in {"1", "true", "yes", "on"}


class Desktop:
    def __init__(self):
        self.desktop_state: DesktopState | None = None
        self._tree: "Tree | None" = None

    @property
    def tree(self) -> "Tree":
        if self._tree is None:
            from mac_mcp.tree.service import Tree
            self._tree = Tree(self)
        return self._tree

    # ------------------------------------------------------------------
    # Screen geometry
    # ------------------------------------------------------------------

    def get_screen_size(self) -> Size:
        try:
            import AppKit
            frame = AppKit.NSScreen.mainScreen().frame()
            return Size(width=int(frame.size.width), height=int(frame.size.height))
        except Exception:
            try:
                import mss
                with mss.mss() as sct:
                    m = sct.monitors[1]
                    return Size(width=m["width"], height=m["height"])
            except Exception:
                return Size(width=1920, height=1080)

    @staticmethod
    def parse_display_selection(display: list[int] | None) -> list[int] | None:
        return display

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def screenshot(self, scale: float | None = None) -> tuple:
        if scale is None:
            scale = _screenshot_scale()
        image, backend = screenshot_capture.capture(capture_rect=None)
        orig_size = Size(width=image.width, height=image.height)

        # Cap to max dimensions
        if image.width > MAX_IMAGE_WIDTH or image.height > MAX_IMAGE_HEIGHT:
            ratio = min(MAX_IMAGE_WIDTH / image.width, MAX_IMAGE_HEIGHT / image.height)
            scale = min(scale, ratio)

        if scale != 1.0:
            image = image.resize(
                (int(image.width * scale), int(image.height * scale)),
                Image.LANCZOS,
            )

        return image, backend, orig_size

    # ------------------------------------------------------------------
    # Window enumeration
    # ------------------------------------------------------------------

    def _get_windows(self) -> tuple[Window | None, list[Window]]:
        """Return (active_window, all_windows) from NSWorkspace + AX."""
        try:
            import AppKit
        except ImportError:
            return None, []

        workspace = AppKit.NSWorkspace.sharedWorkspace()
        running_apps = workspace.runningApplications()
        frontmost = workspace.frontmostApplication()
        frontmost_pid = frontmost.processIdentifier() if frontmost else -1

        windows: list[Window] = []
        active_window: Window | None = None

        for app in running_apps:
            try:
                if app.activationPolicy() != AppKit.NSApplicationActivationPolicyRegular:
                    continue

                pid = app.processIdentifier()
                app_name = app.localizedName() or ""
                app_elem = ax_core.get_frontmost_app() if pid == frontmost_pid else \
                    __import__("ApplicationServices").AXUIElementCreateApplication(pid)

                app_windows = ax_core.ax_get_windows(app_elem)
                for win in app_windows:
                    title = ax_core.ax_get_attribute(win, "AXTitle") or app_name
                    rect = ax_core.ax_get_rect(win)
                    minimized = ax_core.ax_get_attribute(win, "AXMinimized") or False
                    hidden = ax_core.ax_get_attribute(win, "AXHidden") or False

                    if minimized:
                        status = Status.MINIMIZED
                    elif hidden:
                        status = Status.HIDDEN
                    else:
                        status = Status.NORMAL

                    bb = BoundingBox(
                        left=rect.left if rect else 0,
                        top=rect.top if rect else 0,
                        right=rect.right if rect else 0,
                        bottom=rect.bottom if rect else 0,
                        width=rect.width if rect else 0,
                        height=rect.height if rect else 0,
                    )

                    is_browser = Browser.has_process(app_name)
                    window = Window(
                        name=title,
                        is_browser=is_browser,
                        depth=0,
                        status=status,
                        bounding_box=bb,
                        handle=pid,
                        process_id=pid,
                    )
                    windows.append(window)
                    if pid == frontmost_pid and active_window is None:
                        active_window = window

            except Exception:
                continue

        return active_window, windows

    # ------------------------------------------------------------------
    # Annotation
    # ------------------------------------------------------------------

    def _annotate(self, image: Image.Image, nodes, scale_x: float, scale_y: float) -> Image.Image:
        """Draw numbered bounding boxes on screenshot for each interactive element."""
        draw = ImageDraw.Draw(image, "RGBA")
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except Exception:
            font = ImageFont.load_default()

        for i, node in enumerate(nodes, start=1):
            bb = node.bounding_box
            x1 = int(bb.left * scale_x)
            y1 = int(bb.top * scale_y)
            x2 = int(bb.right * scale_x)
            y2 = int(bb.bottom * scale_y)

            colour = _LABEL_COLOURS[i % len(_LABEL_COLOURS)]

            # Draw semi-transparent fill
            draw.rectangle([x1, y1, x2, y2], fill=colour + "40", outline=colour, width=1)

            # Draw label badge
            label_text = str(i)
            draw.rectangle([x1, y1, x1 + 18, y1 + 14], fill=colour)
            draw.text((x1 + 2, y1 + 1), label_text, fill="white", font=font)

        return image

    # ------------------------------------------------------------------
    # get_state — main entry point for Snapshot tool
    # ------------------------------------------------------------------

    def get_state(
        self,
        use_vision: bool = False,
        use_dom: bool = False,
        use_annotation: bool = True,
        use_ui_tree: bool = True,
        as_bytes: bool = False,
        scale: float = 1.0,
        grid_lines: tuple[int, int] | None = None,
        display_indices: list[int] | None = None,
        max_image_size: Size | None = None,
    ) -> DesktopState:
        profile = _snapshot_profile_enabled()
        t0 = time.perf_counter()

        # Screenshot
        image, backend, orig_size = self.screenshot(scale=scale)

        # Scale factors (AX coords are logical; screenshot may be scaled)
        scale_x = image.width / orig_size.width
        scale_y = image.height / orig_size.height

        # AX tree
        tree_state = None
        if use_ui_tree:
            tree_state = self.tree.capture()
            if use_annotation and use_vision and tree_state.interactive_nodes:
                image = self._annotate(image, tree_state.interactive_nodes, scale_x, scale_y)

        if profile:
            logger.info("get_state: %.1fms", (time.perf_counter() - t0) * 1000)

        # Windows
        active_window, windows = self._get_windows()

        # Cursor
        cursor = ax_core.get_cursor_position()

        self.desktop_state = DesktopState(
            active_desktop={"name": "Main"},
            all_desktops=[{"name": "Main"}],
            active_window=active_window,
            windows=windows,
            screenshot=image if use_vision else None,
            cursor_position=cursor,
            screenshot_original_size=orig_size,
            screenshot_backend=backend,
            tree_state=tree_state,
            capture_sec=time.perf_counter() - t0,
        )
        return self.desktop_state

    # ------------------------------------------------------------------
    # Coordinate lookup
    # ------------------------------------------------------------------

    def get_coordinates_from_label(self, label: int) -> tuple[int, int]:
        """Resolve a 1-based element label to screen coordinates."""
        if self.desktop_state is None or self.desktop_state.tree_state is None:
            raise ValueError("No desktop state. Call Snapshot first.")
        nodes = self.desktop_state.tree_state.interactive_nodes
        if label < 1 or label > len(nodes):
            raise ValueError(f"Label {label} out of range (1–{len(nodes)})")
        node = nodes[label - 1]
        return node.center.x, node.center.y

    # ------------------------------------------------------------------
    # Mouse input
    # ------------------------------------------------------------------

    def click(
        self,
        loc: list[int],
        button: str = "left",
        clicks: int = 1,
        modifier: str | None = None,
    ) -> None:
        mouse = _get_mouse()
        x, y = int(loc[0]), int(loc[1])
        mouse.position = (x, y)
        time.sleep(0.05)

        if clicks == 0:
            return  # hover only

        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(
            button, Button.left
        )

        def _do_click():
            for i in range(clicks):
                mouse.press(btn)
                time.sleep(0.02)
                mouse.release(btn)
                if i < clicks - 1:
                    time.sleep(0.08)

        if modifier:
            key = _resolve_key(modifier)
            kb = _get_keyboard()
            with kb.pressed(key):
                _do_click()
        else:
            _do_click()

    def move(self, loc: list[int]) -> None:
        _get_mouse().position = (int(loc[0]), int(loc[1]))

    def drag(self, loc: list[int]) -> None:
        mouse = _get_mouse()
        mouse.press(Button.left)
        time.sleep(0.05)
        mouse.position = (int(loc[0]), int(loc[1]))
        time.sleep(0.1)
        mouse.release(Button.left)

    def scroll(
        self,
        loc: list[int] | None,
        scroll_type: str = "vertical",
        direction: str = "down",
        wheel_times: int = 1,
    ) -> str | None:
        mouse = _get_mouse()
        if loc:
            mouse.position = (int(loc[0]), int(loc[1]))
            time.sleep(0.05)

        amount = wheel_times * 3
        dx, dy = 0, 0
        match direction:
            case "up":
                dy = amount
            case "down":
                dy = -amount
            case "left":
                dx = -amount
            case "right":
                dx = amount

        mouse.scroll(dx, dy)
        return None

    # ------------------------------------------------------------------
    # Keyboard input
    # ------------------------------------------------------------------

    def type_text(
        self,
        loc: list[int] | None = None,
        text: str = "",
        clear: bool | str = False,
        press_enter: bool | str = False,
        caret_position: str = "idle",
    ) -> None:
        kb = _get_keyboard()
        if loc:
            self.click(loc=loc)
            time.sleep(0.15)

        if clear is True or (isinstance(clear, str) and clear.lower() == "true"):
            with kb.pressed(Key.cmd):
                kb.press('a')
                kb.release('a')
            time.sleep(0.05)
            kb.press(Key.backspace)
            kb.release(Key.backspace)
            time.sleep(0.05)

        if caret_position == "start":
            with kb.pressed(Key.cmd):
                kb.press(Key.up)
                kb.release(Key.up)
        elif caret_position == "end":
            with kb.pressed(Key.cmd):
                kb.press(Key.down)
                kb.release(Key.down)

        kb.type(text)

        if press_enter is True or (isinstance(press_enter, str) and press_enter.lower() == "true"):
            kb.press(Key.enter)
            kb.release(Key.enter)

    # mirrors Windows-MCP method name used by input tool
    def type(self, loc, text, caret_position="idle", clear=False, press_enter=False) -> None:
        self.type_text(loc=loc, text=text, clear=clear, press_enter=press_enter,
                       caret_position=caret_position)

    def shortcut(self, shortcut_str: str) -> None:
        """Execute a keyboard shortcut like 'cmd+c' or 'cmd+shift+s'."""
        kb = _get_keyboard()
        parts = [p.strip() for p in shortcut_str.replace(" ", "").split("+")]
        keys = [_resolve_key(p) for p in parts]

        for key in keys:
            kb.press(key)
            time.sleep(0.02)
        time.sleep(0.05)
        for key in reversed(keys):
            kb.release(key)

    # ------------------------------------------------------------------
    # App management
    # ------------------------------------------------------------------

    def app(
        self,
        mode: str = "launch",
        name: str | None = None,
        window_loc: list[int] | None = None,
        window_size: list[int] | None = None,
    ) -> str:
        from mac_mcp.launcher import app_launcher
        match mode:
            case "launch":
                return app_launcher.launch(name or "")
            case "switch":
                return app_launcher.switch(name or "")
            case "resize":
                return app_launcher.resize(name, window_loc, window_size)
            case _:
                return f"Unknown mode: {mode!r}. Use launch, switch, or resize."

    # ------------------------------------------------------------------
    # Multi-element operations
    # ------------------------------------------------------------------

    def get_coordinates_from_labels(self, labels: list[int]) -> list[tuple[int, int]]:
        """Resolve multiple UI element labels to screen coordinates."""
        if self.desktop_state is None or self.desktop_state.tree_state is None:
            raise ValueError("No desktop state. Call Snapshot first.")
        nodes = self.desktop_state.tree_state.interactive_nodes
        results = []
        for label in labels:
            if label < 1 or label > len(nodes):
                raise ValueError(f"Label {label} out of range (1–{len(nodes)})")
            node = nodes[label - 1]
            results.append((node.center.x, node.center.y))
        return results

    def multi_select(self, press_cmd: bool = True, locs: list[tuple[int, int]] | None = None) -> None:
        """Click multiple locations, holding Cmd for multi-selection."""
        kb = _get_keyboard()
        mouse = _get_mouse()
        if locs is None:
            return
        if press_cmd:
            kb.press(Key.cmd)
            time.sleep(0.05)
        try:
            for loc in locs:
                x, y = int(loc[0]), int(loc[1])
                mouse.position = (x, y)
                time.sleep(0.05)
                mouse.press(Button.left)
                time.sleep(0.02)
                mouse.release(Button.left)
                time.sleep(0.2)
        finally:
            if press_cmd:
                kb.release(Key.cmd)

    def multi_edit(self, locs: list[tuple]) -> None:
        """Type text into multiple fields sequentially. Each entry is [x, y, text]."""
        for loc in locs:
            x, y, text = loc[0], loc[1], loc[2]
            self.type_text(loc=[x, y], text=text, clear=True)
            time.sleep(0.1)

    # ------------------------------------------------------------------
    # Web scraping
    # ------------------------------------------------------------------

    def scrape(self, url: str) -> str:
        import requests
        from markdownify import markdownify
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"HTTP error for {url}: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to {url}: {e}") from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Request timed out for {url}: {e}") from e
        return markdownify(html=response.text)

    # ------------------------------------------------------------------
    # Process management
    # ------------------------------------------------------------------

    def list_processes(
        self,
        name: str | None = None,
        sort_by: str = "memory",
        limit: int = 20,
    ) -> str:
        import psutil
        from tabulate import tabulate

        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = p.info
                mem_mb = info["memory_info"].rss / (1024 * 1024) if info["memory_info"] else 0
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"] or "Unknown",
                    "cpu": info["cpu_percent"] or 0,
                    "mem_mb": round(mem_mb, 1),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if name:
            from thefuzz import fuzz
            procs = [p for p in procs if fuzz.partial_ratio(name.lower(), p["name"].lower()) > 60]

        sort_key = {
            "memory": lambda x: x["mem_mb"],
            "cpu": lambda x: x["cpu"],
            "name": lambda x: x["name"].lower(),
        }
        procs.sort(key=sort_key.get(sort_by, sort_key["memory"]), reverse=(sort_by != "name"))
        procs = procs[:limit]

        if not procs:
            return f"No processes found{f' matching {name!r}' if name else ''}."

        table = tabulate(
            [[p["pid"], p["name"], f"{p['cpu']:.1f}%", f"{p['mem_mb']:.1f} MB"] for p in procs],
            headers=["PID", "Name", "CPU%", "Memory"],
            tablefmt="simple",
        )
        return f"Processes ({len(procs)} shown):\n{table}"

    def kill_process(self, name: str | None = None, pid: int | None = None, force: bool = False) -> str:
        import psutil

        if pid is None and name is None:
            return "Error: Provide either pid or name parameter."
        killed = []
        if pid is not None:
            try:
                p = psutil.Process(pid)
                pname = p.name()
                p.kill() if force else p.terminate()
                killed.append(f"{pname} (PID {pid})")
            except psutil.NoSuchProcess:
                return f"No process with PID {pid} found."
            except psutil.AccessDenied:
                return f"Access denied to kill PID {pid}."
        else:
            for p in psutil.process_iter(["pid", "name"]):
                try:
                    if p.info["name"] and p.info["name"].lower() == name.lower():
                        p.kill() if force else p.terminate()
                        killed.append(f"{p.info['name']} (PID {p.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if not killed:
            return f'No process matching "{name}" found or access denied.'
        return f"Killed: {', '.join(killed)}"
