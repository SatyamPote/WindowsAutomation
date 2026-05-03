from contextlib import asynccontextmanager
from mac_mcp.config import enable_debug
from fastmcp import FastMCP
from textwrap import dedent
from typing import Any
import logging
import asyncio
import click
import os

logger = logging.getLogger(__name__)

desktop: Any | None = None
analytics: Any | None = None
_mcp: FastMCP | None = None

instructions = dedent("""
mac-mcp provides tools to interact directly with the macOS desktop,
enabling AI agents to operate the desktop on the user's behalf.
""")


def _get_desktop():
    return desktop


def _get_analytics():
    return analytics


def _build_mcp() -> FastMCP:
    global _mcp
    if _mcp is not None:
        return _mcp

    from mac_mcp.analytics import PostHogAnalytics
    from mac_mcp.desktop.service import Desktop
    from mac_mcp.tools import register_all
    from mac_mcp.watchdog.service import WatchDog
    from mac_mcp import permissions

    @asynccontextmanager
    async def lifespan(app: FastMCP):
        global desktop, analytics

        permissions.check_and_warn()

        if os.getenv("ANONYMIZED_TELEMETRY", "true").lower() != "false":
            analytics = PostHogAnalytics()

        desktop = Desktop()
        watchdog = WatchDog()
        watchdog.set_focus_callback(desktop.tree.on_focus_change)

        try:
            watchdog.start()
            await asyncio.sleep(0.5)
            logger.debug("mac-mcp server started")
            yield
        finally:
            logger.debug("mac-mcp shutting down")
            watchdog.stop()
            if analytics:
                await analytics.close()

    _mcp = FastMCP(name="mac-mcp", instructions=instructions, lifespan=lifespan)
    register_all(_mcp, get_desktop=_get_desktop, get_analytics=_get_analytics)
    return _mcp


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--transport",
    help="Transport layer for the MCP server.",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    show_default=True,
)
@click.option("--host", default="localhost", show_default=True)
@click.option("--port", default=8000, type=int, show_default=True)
@click.option("--debug", is_flag=True, default=False)
def main(ctx: click.Context, transport: str, host: str, port: int, debug: bool) -> None:
    if ctx.invoked_subcommand is not None:
        return

    if debug:
        enable_debug()
        logging.getLogger().setLevel(logging.DEBUG)
        for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastmcp"]:
            logging.getLogger(name).setLevel(logging.DEBUG)

    logger.debug("Starting mac-mcp (transport=%s)", transport)

    mcp = _build_mcp()
    try:
        mcp.run(transport=transport, show_banner=False)
        logger.debug("Server shut down normally")
    except Exception:
        logger.error("Server exiting due to unhandled exception", exc_info=True)
        raise


@main.command("telegram")
@click.option("--token", default=None, help="Telegram bot token (overrides env/config).")
def telegram_cmd(token: str | None) -> None:
    """Run the Lotus Telegram bot."""
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        level=logging.INFO,
    )
    from mac_mcp.telegram_bot import run_bot
    run_bot(token=token)


if __name__ == "__main__":
    main()
