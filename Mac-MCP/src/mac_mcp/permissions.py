import logging

logger = logging.getLogger(__name__)


def check_and_warn() -> None:
    missing = []

    try:
        import ApplicationServices
        if not ApplicationServices.AXIsProcessTrusted():
            missing.append(
                "Accessibility — System Settings > Privacy & Security > Accessibility"
            )
    except Exception as e:
        logger.warning("Could not check Accessibility permission: %s", e)

    try:
        import Quartz
        test = Quartz.CGWindowListCreateImage(
            Quartz.CGRectMake(0, 0, 1, 1),
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID,
            Quartz.kCGWindowImageDefault,
        )
        if test is None:
            missing.append(
                "Screen Recording — System Settings > Privacy & Security > Screen Recording"
            )
    except Exception as e:
        logger.warning("Could not check Screen Recording permission: %s", e)

    if missing:
        logger.warning("=" * 60)
        logger.warning("mac-mcp: missing macOS permissions:")
        for m in missing:
            logger.warning("  • %s", m)
        logger.warning("Restart mac-mcp after granting permissions.")
        logger.warning("=" * 60)
