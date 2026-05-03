"""Defaults tool — read/write macOS user defaults (app preferences)."""

import subprocess
from typing import Literal

from mcp.types import ToolAnnotations
from mac_mcp.analytics import with_analytics
from fastmcp import Context


def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="Defaults",
        description=(
            "Read or write macOS user defaults (app preferences stored in ~/Library/Preferences/). "
            "Keywords: defaults, preferences, plist, settings, app config. "
            "Equivalent to the macOS 'defaults' CLI command. "
            "Use read to query a preference, write to set one, delete to remove one, "
            "read-all to dump all keys for a domain."
        ),
        annotations=ToolAnnotations(
            title="Defaults",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "Defaults-Tool")
    def defaults_tool(
        action: Literal["read", "write", "delete", "read-all"],
        domain: str,
        key: str | None = None,
        value: str | None = None,
        value_type: Literal["string", "int", "float", "bool", "array", "dict"] = "string",
        ctx: Context = None,
    ) -> str:
        try:
            match action:
                case "read":
                    cmd = ["defaults", "read", domain] + ([key] if key else [])
                case "read-all":
                    cmd = ["defaults", "read", domain]
                case "write":
                    if key is None or value is None:
                        return "Error: key and value are required for write action."
                    type_flag = {
                        "string": "-string", "int": "-integer", "float": "-float",
                        "bool": "-bool", "array": "-array", "dict": "-dict",
                    }.get(value_type, "-string")
                    cmd = ["defaults", "write", domain, key, type_flag, value]
                case "delete":
                    cmd = ["defaults", "delete", domain] + ([key] if key else [])
                case _:
                    return f"Unknown action: {action!r}. Use: read, write, delete, read-all."

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output = (result.stdout + result.stderr).strip()
            return f"{output}\nExit code: {result.returncode}" if output else f"Exit code: {result.returncode}"
        except subprocess.TimeoutExpired:
            return "Error: defaults command timed out."
        except Exception as e:
            return f"Error running defaults: {e}"
