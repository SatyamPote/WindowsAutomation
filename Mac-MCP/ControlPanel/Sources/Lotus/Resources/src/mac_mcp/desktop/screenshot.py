import logging
import os
from dataclasses import dataclass

from PIL import Image, ImageGrab

try:
    import mss
except ImportError:
    mss = None

try:
    import Quartz
except ImportError:
    Quartz = None

logger = logging.getLogger(__name__)


@dataclass
class Rect:
    left: int
    top: int
    right: int
    bottom: int


def get_screenshot_backend() -> str:
    value = os.getenv("MAC_MCP_SCREENSHOT_BACKEND", "auto")
    normalized = value.strip().lower()
    valid = _ScreenshotBackend.registry.keys() | {"auto"}
    if normalized in valid:
        return normalized
    logger.warning("Unknown screenshot backend %r; falling back to auto", value)
    return "auto"


class _ScreenshotBackend:
    name: str
    priority: int
    registry: dict[str, type["_ScreenshotBackend"]] = {}

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "name" in cls.__dict__ and "priority" in cls.__dict__:
            existing = _ScreenshotBackend.registry.get(cls.name)
            if existing is not None and existing is not cls:
                raise ValueError(f"Duplicate screenshot backend name: {cls.name!r}")
            _ScreenshotBackend.registry[cls.name] = cls

    def is_available(self, capture_rect: Rect | None) -> bool:
        return True

    def capture(self, capture_rect: Rect | None) -> Image.Image:
        raise NotImplementedError


class _QuartzBackend(_ScreenshotBackend):
    name = "quartz"
    priority = 10

    def is_available(self, capture_rect: Rect | None) -> bool:
        return Quartz is not None

    def capture(self, capture_rect: Rect | None) -> Image.Image:
        if Quartz is None:
            raise RuntimeError("Quartz framework not available")

        import AppKit
        import io

        if capture_rect is None:
            region = Quartz.CGRectInfinite
        else:
            region = Quartz.CGRectMake(
                capture_rect.left,
                capture_rect.top,
                capture_rect.right - capture_rect.left,
                capture_rect.bottom - capture_rect.top,
            )

        image_ref = Quartz.CGWindowListCreateImage(
            region,
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID,
            Quartz.kCGWindowImageDefault,
        )
        if image_ref is None:
            raise RuntimeError(
                "Quartz capture returned nil — Screen Recording permission may be missing. "
                "Grant it in System Settings > Privacy & Security > Screen Recording."
            )

        # Convert CGImageRef → PIL via NSImage → TIFF (avoids ctypes buffer issues)
        ns_image = AppKit.NSImage.alloc().initWithCGImage_size_(
            image_ref, AppKit.NSZeroSize
        )
        tiff_data = ns_image.TIFFRepresentation()
        if tiff_data is None:
            raise RuntimeError("Could not convert CGImage to TIFF")
        return Image.open(io.BytesIO(bytes(tiff_data)))


class _MssBackend(_ScreenshotBackend):
    name = "mss"
    priority = 20

    def is_available(self, capture_rect: Rect | None) -> bool:
        return mss is not None

    def capture(self, capture_rect: Rect | None) -> Image.Image:
        if mss is None:
            raise RuntimeError("mss is not available")
        with mss.mss() as sct:
            if capture_rect is None:
                monitor = sct.monitors[0]
            else:
                monitor = {
                    "left": capture_rect.left,
                    "top": capture_rect.top,
                    "width": capture_rect.right - capture_rect.left,
                    "height": capture_rect.bottom - capture_rect.top,
                }
            raw = sct.grab(monitor)
            return Image.frombytes("RGB", raw.size, raw.rgb)


class _PillowBackend(_ScreenshotBackend):
    name = "pillow"
    priority = 100

    def capture(self, capture_rect: Rect | None) -> Image.Image:
        grab_kwargs: dict = {"all_screens": True}
        if capture_rect is not None:
            grab_kwargs["bbox"] = (
                capture_rect.left,
                capture_rect.top,
                capture_rect.right,
                capture_rect.bottom,
            )
        try:
            return ImageGrab.grab(**grab_kwargs)
        except (OSError, RuntimeError, ValueError):
            logger.warning("Pillow grab failed, trying primary screen only")
            return ImageGrab.grab()


_backend_instances: dict[str, _ScreenshotBackend] = {}


def _get_backend(name: str) -> _ScreenshotBackend:
    if name not in _backend_instances:
        cls = _ScreenshotBackend.registry.get(name)
        if cls is None:
            raise ValueError(f"Unknown screenshot backend: {name!r}")
        _backend_instances[name] = cls()
    return _backend_instances[name]


def capture(
    capture_rect: Rect | None,
    backend: str | None = None,
) -> tuple[Image.Image, str]:
    """Capture a screenshot. Returns (image, backend_name_used)."""
    selected = backend or get_screenshot_backend()

    if selected == "auto":
        chain = sorted(_ScreenshotBackend.registry.values(), key=lambda c: c.priority)
    else:
        cls = _ScreenshotBackend.registry.get(selected)
        if cls is None:
            raise ValueError(f"Unknown screenshot backend: {selected!r}")
        chain = [cls]

    for backend_cls in chain:
        inst = _get_backend(backend_cls.name)
        if not inst.is_available(capture_rect):
            continue
        try:
            return inst.capture(capture_rect), inst.name
        except (OSError, RuntimeError, ValueError):
            logger.warning(
                "Screenshot backend %r failed; trying next",
                inst.name,
                exc_info=(selected != "auto"),
            )

    return _get_backend("pillow").capture(capture_rect), "pillow"
