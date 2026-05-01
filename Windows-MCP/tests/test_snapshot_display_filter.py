import asyncio
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from windows_mcp.desktop.screenshot import _crop_screenshot  # noqa
from windows_mcp.desktop.service import Desktop
from windows_mcp.desktop.views import DesktopState, Size, Status, Window
from windows_mcp.tree.views import (
    BoundingBox,
    Center,
    ScrollElementNode,
    TreeElementNode,
    TreeState,
)
from windows_mcp.uia import Rect
import windows_mcp.__main__ as main_module


def make_box(left: int, top: int, right: int, bottom: int) -> BoundingBox:
    return BoundingBox(
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        width=right - left,
        height=bottom - top,
    )


class TestParseDisplaySelection:
    def test_none_keeps_default_behavior(self):
        assert Desktop.parse_display_selection(None) is None
        assert Desktop.parse_display_selection("") is None

    def test_supports_single_and_multiple_displays(self):
        assert Desktop.parse_display_selection([0]) == [0]
        assert Desktop.parse_display_selection([0, 1]) == [0, 1]
        assert Desktop.parse_display_selection([0, 1, 0]) == [0, 1]
        assert Desktop.parse_display_selection(2) == [2]

    def test_rejects_invalid_display_values(self):
        with pytest.raises(ValueError):
            Desktop.parse_display_selection("0")
        with pytest.raises(ValueError):
            Desktop.parse_display_selection([-1])
        with pytest.raises(ValueError):
            Desktop.parse_display_selection(["a"])


class TestDisplayFiltering:
    @pytest.fixture
    def desktop(self):
        with patch.object(Desktop, "__init__", lambda self: None):
            desktop = Desktop()
            return desktop

    def test_get_display_union_rect(self, desktop):
        with patch("windows_mcp.desktop.service.uia.GetMonitorsRect") as mock_get_monitors:
            mock_get_monitors.return_value = [
                Rect(0, 0, 1920, 1080),
                Rect(1920, 0, 3840, 1080),
            ]

            result = desktop.get_display_union_rect([1])
            assert result == Rect(1920, 0, 3840, 1080)

            combined = desktop.get_display_union_rect([0, 1])
            assert combined == Rect(0, 0, 3840, 1080)

    def test_get_display_union_rect_rejects_missing_display(self, desktop):
        with patch("windows_mcp.desktop.service.uia.GetMonitorsRect") as mock_get_monitors:
            mock_get_monitors.return_value = [Rect(0, 0, 1920, 1080)]
            with pytest.raises(ValueError):
                desktop.get_display_union_rect([1])

    def test_filter_state_to_selected_display(self, desktop):
        region = make_box(1920, 0, 3840, 1080)
        kept_window = Window(
            name="Browser",
            is_browser=True,
            depth=0,
            status=Status.NORMAL,
            bounding_box=make_box(1800, 100, 2200, 500),
            handle=1,
            process_id=11,
        )
        dropped_window = Window(
            name="Editor",
            is_browser=False,
            depth=0,
            status=Status.NORMAL,
            bounding_box=make_box(100, 100, 600, 600),
            handle=2,
            process_id=22,
        )
        tree_state = TreeState(
            interactive_nodes=[
                TreeElementNode(
                    name="Visible",
                    control_type="Button",
                    window_name="Browser",
                    bounding_box=make_box(2000, 200, 2100, 260),
                    center=Center(x=2050, y=230),
                    metadata={},
                ),
                TreeElementNode(
                    name="Hidden",
                    control_type="Button",
                    window_name="Editor",
                    bounding_box=make_box(200, 200, 260, 260),
                    center=Center(x=230, y=230),
                    metadata={},
                ),
            ],
            scrollable_nodes=[
                ScrollElementNode(
                    name="Pane",
                    control_type="Pane",
                    window_name="Browser",
                    bounding_box=make_box(1900, 0, 2500, 900),
                    center=Center(x=2200, y=450),
                    metadata={"vertical_scrollable": True},
                )
            ],
        )

        filtered_tree = desktop._filter_tree_state_to_region(tree_state, region)
        filtered_window = desktop._filter_window_to_region(kept_window, region)
        filtered_windows = desktop._filter_windows_to_region([kept_window, dropped_window], region)

        assert filtered_window is not None
        assert filtered_window.bounding_box.left == 1920
        assert filtered_window.bounding_box.right == 2200
        assert [window.name for window in filtered_windows] == ["Browser"]
        assert [node.name for node in filtered_tree.interactive_nodes] == ["Visible"]
        assert filtered_tree.scrollable_nodes[0].bounding_box.left == 1920
        assert filtered_tree.root_node.bounding_box == region

    def test_crop_screenshot_to_display_region(self, desktop):
        screenshot = Image.new("RGB", (3840, 1080), "white")
        with patch("windows_mcp.desktop.screenshot.uia.GetVirtualScreenRect") as mock_virtual_rect:
            mock_virtual_rect.return_value = (0, 0, 3840, 1080)
            cropped = _crop_screenshot(screenshot, Rect(1920, 0, 3840, 1080))
        assert cropped.size == (1920, 1080)

    def test_get_screenshot_uses_display_bbox_for_direct_capture(self, desktop):
        capture_rect = Rect(1920, 0, 3840, 1080)
        with patch("windows_mcp.desktop.screenshot.dxcam", None):
            with patch("windows_mcp.desktop.screenshot.ImageGrab.grab") as mock_grab:
                with patch(
                    "windows_mcp.desktop.screenshot.get_screenshot_backend"
                ) as mock_screenshot_backend:
                    mock_grab.return_value = Image.new("RGB", (1920, 1080), "white")
                    mock_screenshot_backend.return_value = (
                        "pillow"  # Ensure we test the Pillow path
                    )
                    screenshot = desktop.get_screenshot(capture_rect=capture_rect)

        assert screenshot.size == (1920, 1080)
        assert mock_grab.call_args.kwargs == {
            "bbox": (1920, 0, 3840, 1080),
            "all_screens": True,
        }

    def test_get_screenshot_uses_dxcam_for_single_display_capture(self, desktop, monkeypatch):
        capture_rect = Rect(1920, 0, 3840, 1080)
        fake_camera = MagicMock()
        fake_camera.grab.return_value = [[[255, 255, 255]]]
        fake_dxcam = MagicMock()
        fake_dxcam.create.return_value = fake_camera

        monkeypatch.setenv("WINDOWS_MCP_SCREENSHOT_BACKEND", "dxcam")
        monkeypatch.setattr("windows_mcp.desktop.screenshot.dxcam", fake_dxcam)
        monkeypatch.setattr("windows_mcp.desktop.screenshot._backend_instances", {})
        monkeypatch.setattr(
            "windows_mcp.desktop.screenshot.uia.GetMonitorsRect",
            lambda: [Rect(0, 0, 1920, 1080), Rect(1920, 0, 3840, 1080)],
        )
        with patch(
            "windows_mcp.desktop.screenshot.Image.fromarray",
            return_value=Image.new("RGB", (1, 1), "white"),
        ) as mock_fromarray:
            screenshot = desktop.get_screenshot(capture_rect=capture_rect)

        assert screenshot.size == (1, 1)
        fake_dxcam.create.assert_called_once_with(output_idx=1, processor_backend="numpy")
        fake_camera.grab.assert_called_once_with(region=None, copy=True, new_frame_only=False)
        mock_fromarray.assert_called_once()

    def test_get_screenshot_falls_back_to_pillow_when_dxcam_region_is_unsupported(
        self, desktop, monkeypatch
    ):
        capture_rect = Rect(0, 0, 3840, 1080)
        fake_dxcam = MagicMock()

        monkeypatch.setenv("WINDOWS_MCP_SCREENSHOT_BACKEND", "dxcam")
        monkeypatch.setattr("windows_mcp.desktop.screenshot.dxcam", fake_dxcam)
        monkeypatch.setattr(
            "windows_mcp.desktop.screenshot.uia.GetMonitorsRect",
            lambda: [Rect(0, 0, 1920, 1080), Rect(1920, 0, 3840, 1080)],
        )
        with patch("windows_mcp.desktop.screenshot.ImageGrab.grab") as mock_grab:
            mock_grab.return_value = Image.new("RGB", (3840, 1080), "white")
            screenshot = desktop.get_screenshot(capture_rect=capture_rect)

        assert screenshot.size == (3840, 1080)
        assert fake_dxcam.create.call_count == 0
        assert mock_grab.call_args.kwargs == {
            "bbox": (0, 0, 3840, 1080),
            "all_screens": True,
        }

    def test_get_screenshot_auto_uses_mss_when_dxcam_is_unavailable(self, desktop, monkeypatch):
        capture_rect = Rect(1920, 0, 3840, 1080)
        fake_shot = MagicMock()
        fake_shot.size = (1920, 1080)
        fake_shot.rgb = b"\xff\xff\xff" * (1920 * 1080)
        fake_mss_ctx = MagicMock()
        fake_mss_ctx.__enter__.return_value = MagicMock(
            grab=MagicMock(return_value=fake_shot),
            monitors=[{}, {"left": 0, "top": 0, "width": 1920, "height": 1080}],
        )
        fake_mss_module = MagicMock(mss=MagicMock(return_value=fake_mss_ctx))

        monkeypatch.setenv("WINDOWS_MCP_SCREENSHOT_BACKEND", "auto")
        monkeypatch.setattr("windows_mcp.desktop.screenshot.dxcam", None)
        monkeypatch.setattr("windows_mcp.desktop.screenshot.mss", fake_mss_module)
        screenshot = desktop.get_screenshot(capture_rect=capture_rect)

        assert screenshot.size == (1920, 1080)
        assert getattr(desktop, "_last_screenshot_backend") == "mss"

    def test_grid_lines_use_selected_display_region(self, desktop):
        screenshot = Image.new("RGB", (1920, 1080), "white")
        with patch.object(
            desktop, "get_screenshot", return_value=screenshot
        ) as mock_get_screenshot:
            with patch("windows_mcp.desktop.service.uia.GetVirtualScreenRect") as mock_virtual_rect:
                mock_virtual_rect.return_value = (0, 0, 3840, 1080)
                annotated = desktop.get_annotated_screenshot(
                    nodes=[],
                    grid_lines=(2, 2),
                    capture_rect=Rect(1920, 0, 3840, 1080),
                )

        assert annotated.size == (1920, 1080)
        mock_get_screenshot.assert_called_once_with(capture_rect=Rect(1920, 0, 3840, 1080))
        assert annotated.getpixel((960, 100)) != (255, 255, 255)
        assert annotated.getpixel((100, 540)) != (255, 255, 255)

    def test_desktop_state_tracks_selected_displays(self):
        state = DesktopState(
            active_desktop={"name": "Desktop 1"},
            all_desktops=[{"name": "Desktop 1"}],
            active_window=None,
            windows=[],
            screenshot_original_size=Size(width=1920, height=1080),
            screenshot_region=make_box(1920, 0, 3840, 1080),
            screenshot_displays=[1],
        )
        assert state.screenshot_original_size.to_string() == "(1920,1080)"
        assert state.screenshot_region.xyxy_to_string() == "(1920,0,3840,1080)"
        assert state.screenshot_displays == [1]

    def test_get_state_skips_tree_capture_when_use_ui_tree_false(self, desktop):
        desktop.tree = MagicMock()
        desktop.tree.screen_box = make_box(0, 0, 1920, 1080)
        desktop.get_controls_handles = MagicMock(return_value={1})
        active_window = Window(
            name="Browser",
            is_browser=True,
            depth=0,
            status=Status.NORMAL,
            bounding_box=make_box(100, 100, 700, 500),
            handle=1,
            process_id=11,
        )
        desktop.get_windows = MagicMock(return_value=([active_window], {1}))
        desktop.get_active_window = MagicMock(return_value=active_window)
        desktop.get_cursor_location = MagicMock(return_value=(250, 180))
        desktop.get_screenshot = MagicMock(return_value=Image.new("RGB", (800, 600), "white"))

        with patch(
            "windows_mcp.desktop.service.get_current_desktop", return_value={"name": "Desktop 1"}
        ):
            with patch(
                "windows_mcp.desktop.service.get_all_desktops", return_value=[{"name": "Desktop 1"}]
            ):
                state = desktop.get_state(
                    use_vision=True,
                    use_annotation=False,
                    use_ui_tree=False,
                )

        desktop.tree.get_state.assert_not_called()
        assert state.tree_state.root_node.bounding_box == desktop.tree.screen_box
        assert state.tree_state.interactive_nodes == []
        assert state.tree_state.scrollable_nodes == []
        assert state.screenshot_original_size.to_string() == "(800,600)"

    def test_get_state_rejects_dom_without_ui_tree(self, desktop):
        desktop.tree = MagicMock()

        with pytest.raises(ValueError, match="use_dom=True requires use_ui_tree=True"):
            desktop.get_state(use_dom=True, use_ui_tree=False)

    def test_get_state_logs_snapshot_profile_when_enabled(self, desktop, monkeypatch):
        desktop.tree = MagicMock()
        desktop.tree.screen_box = make_box(0, 0, 1920, 1080)
        desktop.get_controls_handles = MagicMock(return_value={1})
        active_window = Window(
            name="Browser",
            is_browser=True,
            depth=0,
            status=Status.NORMAL,
            bounding_box=make_box(100, 100, 700, 500),
            handle=1,
            process_id=11,
        )
        desktop.get_windows = MagicMock(return_value=([active_window], {1}))
        desktop.get_active_window = MagicMock(return_value=active_window)
        desktop.get_cursor_location = MagicMock(return_value=(250, 180))
        logged: list[str] = []

        monkeypatch.setenv("WINDOWS_MCP_PROFILE_SNAPSHOT", "1")
        monkeypatch.setattr(
            "windows_mcp.desktop.service.logger.info",
            lambda message, *args: logged.append(message % args if args else message),
        )

        with patch(
            "windows_mcp.desktop.service.get_current_desktop", return_value={"name": "Desktop 1"}
        ):
            with patch(
                "windows_mcp.desktop.service.get_all_desktops", return_value=[{"name": "Desktop 1"}]
            ):
                desktop.get_state(
                    use_vision=False,
                    use_annotation=False,
                    use_ui_tree=False,
                )

        assert any("Snapshot profile:" in message for message in logged)


class TestSnapshotTools:
    @pytest.fixture
    def desktop_state(self):
        return DesktopState(
            active_desktop={"name": "Desktop 1"},
            all_desktops=[{"name": "Desktop 1"}],
            active_window=None,
            windows=[],
            screenshot=Image.new("RGB", (640, 480), "white"),
            cursor_position=(25, 30),
            screenshot_original_size=Size(width=640, height=480),
            screenshot_region=make_box(0, 0, 640, 480),
            screenshot_displays=[0],
            tree_state=TreeState(),
        )

    def test_snapshot_tool_keeps_ui_tree_enabled_by_default(self, desktop_state, monkeypatch):
        fake_desktop = MagicMock()
        fake_desktop.get_state.return_value = desktop_state
        monkeypatch.setattr(main_module, "desktop", fake_desktop)

        result = asyncio.run(main_module.state_tool(use_vision=True, display=[0]))

        assert len(result) == 2
        call = fake_desktop.get_state.call_args.kwargs
        assert call["use_vision"] is True
        assert call["use_ui_tree"] is True
        assert call["use_annotation"] is True

    def test_screenshot_tool_uses_fast_path_without_ui_tree(self, desktop_state, monkeypatch):
        fake_desktop = MagicMock()
        fake_desktop.get_state.return_value = desktop_state
        monkeypatch.setattr(main_module, "desktop", fake_desktop)

        result = asyncio.run(main_module.screenshot_tool(display=[0]))

        assert len(result) == 2
        assert "UI Tree: Skipped for fast screenshot-only capture." in result[0]
        call = fake_desktop.get_state.call_args.kwargs
        assert call["use_vision"] is True
        assert call["use_ui_tree"] is False
        assert call["use_dom"] is False
        assert call["use_annotation"] is False
