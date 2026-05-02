"""AX role classification and label extraction."""

from mac_mcp.ax.enums import AXRole
from mac_mcp.ax.core import ax_get_attribute

INTERACTIVE_ROLES = {
    AXRole.BUTTON,
    AXRole.CHECK_BOX,
    AXRole.RADIO_BUTTON,
    AXRole.TEXT_FIELD,
    AXRole.TEXT_AREA,
    AXRole.COMBO_BOX,
    AXRole.POP_UP_BUTTON,
    AXRole.MENU_ITEM,
    AXRole.MENU_BAR_ITEM,
    AXRole.CELL,
    AXRole.SLIDER,
    AXRole.LINK,
    AXRole.DISCLOSURE,
    AXRole.STEPPER,
    AXRole.SEARCH_FIELD,
    AXRole.TOOLBAR_BUTTON,
}

SCROLLABLE_ROLES = {
    AXRole.SCROLL_AREA,
    AXRole.LIST,
    AXRole.TABLE,
    AXRole.TEXT_AREA,
    AXRole.OUTLINE,
    AXRole.WEB_AREA,
}

STRUCTURAL_ROLES = {
    AXRole.GROUP,
    AXRole.TOOL_BAR,
    AXRole.TAB_GROUP,
    AXRole.SPLIT_GROUP,
    AXRole.MENU_BAR,
    AXRole.WINDOW,
    AXRole.APPLICATION,
}

_ACTION_MAP = {
    AXRole.TEXT_FIELD:    "fill",
    AXRole.TEXT_AREA:     "fill",
    AXRole.SEARCH_FIELD:  "fill",
    AXRole.CHECK_BOX:     "toggle",
    AXRole.RADIO_BUTTON:  "select",
    AXRole.COMBO_BOX:     "select",
    AXRole.POP_UP_BUTTON: "select",
    AXRole.SLIDER:        "slide",
    AXRole.DISCLOSURE:    "toggle",
    AXRole.SCROLL_AREA:   "scroll",
    AXRole.LIST:          "scroll",
    AXRole.TABLE:         "scroll",
    AXRole.OUTLINE:       "scroll",
}


def get_action_for_role(role: str) -> str:
    return _ACTION_MAP.get(role, "click")


def get_element_label(element) -> str:
    """Best human-readable label for an element, trying attributes in priority order."""
    for attr in ("AXTitle", "AXDescription", "AXValue", "AXPlaceholderValue", "AXHelp"):
        val = ax_get_attribute(element, attr)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def is_interactive(role: str) -> bool:
    return role in INTERACTIVE_ROLES


def is_scrollable(role: str) -> bool:
    return role in SCROLLABLE_ROLES


def is_structural(role: str) -> bool:
    return role in STRUCTURAL_ROLES


def is_visible(element) -> bool:
    hidden = ax_get_attribute(element, "AXHidden")
    return not hidden
