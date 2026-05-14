"""Shell tool — bash/zsh command execution."""

from mcp.types import ToolAnnotations
from mac_mcp.analytics import with_analytics
from mac_mcp.desktop.shell import ShellExecutor
from fastmcp import Context


def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="Shell",
        description=(
            "Execute shell commands via bash. Keywords: shell, run, execute, terminal, "
            "command line, script, bash, zsh. Full access to the macOS shell — filesystem, "
            "processes, network, scripting. Use for any system operation not covered by "
            "dedicated tools."
        ),
        annotations=ToolAnnotations(
            title="Shell",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    @with_analytics(get_analytics(), "Shell-Tool")
    def shell_tool(command: str, timeout: int = 30, ctx: Context = None) -> str:
        output, code = ShellExecutor.execute(command, timeout)
        return f"Output: {output}\nExit code: {code}"
