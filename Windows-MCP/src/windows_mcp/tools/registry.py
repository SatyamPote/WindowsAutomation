"""Registry tool — Windows Registry operations."""

from typing import Literal

from mcp.types import ToolAnnotations
from windows_mcp.analytics import with_analytics
from fastmcp import Context


def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="Registry",
        description='Read and write the Windows Registry. Keywords: regedit, registry key, HKEY, HKCU, HKLM, Windows settings, registry value. Use mode="get" to read a value, mode="set" to create/update a value, mode="delete" to remove a value or key, mode="list" to list values and sub-keys under a path. Paths use PowerShell format (e.g. "HKCU:\\Software\\MyApp", "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion").',
        annotations=ToolAnnotations(
            title="Registry",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "Registry-Tool")
    def registry_tool(
        mode: Literal["get", "set", "delete", "list"],
        path: str,
        name: str | None = None,
        value: str | None = None,
        type: Literal[
            "String", "DWord", "QWord", "Binary", "MultiString", "ExpandString"
        ] = "String",
        ctx: Context = None,
    ) -> str:
        desktop = get_desktop()
        try:
            if mode == "get":
                if name is None:
                    return "Error: name parameter is required for get mode."
                return desktop.registry_get(path=path, name=name)
            elif mode == "set":
                if name is None:
                    return "Error: name parameter is required for set mode."
                if value is None:
                    return "Error: value parameter is required for set mode."
                return desktop.registry_set(path=path, name=name, value=value, reg_type=type)
            elif mode == "delete":
                return desktop.registry_delete(path=path, name=name)
            elif mode == "list":
                return desktop.registry_list(path=path)
            else:
                return 'Error: mode must be "get", "set", "delete", or "list".'
        except Exception as e:
            return f"Error accessing registry: {str(e)}"
