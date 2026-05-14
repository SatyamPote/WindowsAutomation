"""Scrape tool — fetch web page content."""

from mcp.types import ToolAnnotations
from mac_mcp.analytics import with_analytics
from fastmcp import Context


def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="Scrape",
        description=(
            "Fetch/scrape web page content from a URL. Keywords: scrape, fetch, browse, web, URL, extract, download, read webpage. "
            "By default (use_dom=False), performs a lightweight HTTP request and returns a clean Markdown summary. "
            "Provide query to focus extraction on specific information. "
            "Set use_dom=True to extract from the active browser tab's DOM instead (required when site blocks HTTP requests). "
            "Set use_sampling=False to get raw content without LLM processing."
        ),
        annotations=ToolAnnotations(
            title="Scrape",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    @with_analytics(get_analytics(), "Scrape-Tool")
    async def scrape_tool(
        url: str,
        query: str | None = None,
        use_dom: bool | str = False,
        use_sampling: bool | str = True,
        ctx: Context = None,
    ) -> str:
        desktop = get_desktop()
        use_dom = use_dom is True or (isinstance(use_dom, str) and use_dom.lower() == "true")
        use_sampling = use_sampling is True or (isinstance(use_sampling, str) and use_sampling.lower() == "true")

        if not use_dom:
            content = desktop.scrape(url)
        else:
            desktop_state = desktop.get_state(use_vision=False, use_dom=True)
            tree_state = desktop_state.tree_state
            if not tree_state or not getattr(tree_state, "dom_node", None):
                return f"No DOM information found. Please open {url} in a browser first."
            dom_node = tree_state.dom_node
            vertical_scroll_percent = getattr(dom_node, "vertical_scroll_percent", 0)
            content = "\n".join([node.text for node in getattr(tree_state, "dom_informative_nodes", [])])
            header = "Reached top" if vertical_scroll_percent <= 0 else "Scroll up to see more"
            footer = "Reached bottom" if vertical_scroll_percent >= 100 else "Scroll down to see more"
            content = f"{header}\n{content}\n{footer}"

        if use_sampling and ctx is not None:
            try:
                focus = f" Focus specifically on: {query}." if query else ""
                result = await ctx.sample(
                    messages=f"Raw scraped content from {url}:\n\n{content}",
                    system_prompt=(
                        "You are a web content extractor. Given raw webpage content, extract and present "
                        "only the meaningful information in clean, concise prose or structured format. "
                        "Strip out navigation menus, cookie banners, ads, footer links, and all other "
                        f"boilerplate. Preserve important data, facts, and structure.{focus}"
                    ),
                    max_tokens=2048,
                )
                return f"URL: {url}\nContent:\n{result.text}"
            except Exception:
                pass

        return f"URL: {url}\nContent:\n{content}"
