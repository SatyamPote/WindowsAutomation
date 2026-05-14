# Graph Report - /Volumes/1TB SSD/Github/Lotus/Mac-MCP  (2026-05-03)

## Corpus Check
- 142 files · ~160,011 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 815 nodes · 1172 edges · 69 communities detected
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 37 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Swift Service Layer|Swift Service Layer]]
- [[_COMMUNITY_AX Accessibility + macOS Permissions|AX Accessibility + macOS Permissions]]
- [[_COMMUNITY_Python Control Panel (app.py)|Python Control Panel (app.py)]]
- [[_COMMUNITY_Desktop State + Window Tools|Desktop State + Window Tools]]
- [[_COMMUNITY_Desktop Input + Interaction|Desktop Input + Interaction]]
- [[_COMMUNITY_Telegram Bot Handler|Telegram Bot Handler]]
- [[_COMMUNITY_Filesystem Tests|Filesystem Tests]]
- [[_COMMUNITY_AX Low-Level Primitives|AX Low-Level Primitives]]
- [[_COMMUNITY_Swift UI Views|Swift UI Views]]
- [[_COMMUNITY_Control API HTTP Server|Control API HTTP Server]]
- [[_COMMUNITY_Screenshot Backends|Screenshot Backends]]
- [[_COMMUNITY_Filesystem View Tests|Filesystem View Tests]]
- [[_COMMUNITY_AppState + Polling|AppState + Polling]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]

## God Nodes (most connected - your core abstractions)
1. `Desktop` - 30 edges
2. `LotusApp` - 22 edges
3. `AppState` - 17 edges
4. `Tree` - 16 edges
5. `AppDelegate` - 14 edges
6. `ServiceManager` - 14 edges
7. `parse_and_execute()` - 12 edges
8. `BoundingBox` - 11 edges
9. `TreeState` - 11 edges
10. `Mac-MCP Project` - 11 edges

## Surprising Connections (you probably didn't know these)
- `App Logo (logo.png) — click/cursor icon on cream background` --semantically_similar_to--> `16 MCP Desktop Control Tools`  [INFERRED] [semantically similar]
  Mac-MCP/assets/logo.png → Mac-MCP/IMPLEMENTATION.md
- `Screenshot 1 — Claude Desktop showing Windows-MCP tool list` --references--> `Windows-MCP Project`  [INFERRED]
  Mac-MCP/assets/screenshots/screenshot_1.png → Mac-MCP/IMPLEMENTATION.md
- `Screenshot 2 — Claude automating Notepad via Windows-MCP (type paragraph about LLMs)` --references--> `Input Tools (tools/input.py) — Click, Type, Scroll, Move, Shortcut, Wait`  [INFERRED]
  Mac-MCP/assets/screenshots/screenshot_2.png → Mac-MCP/IMPLEMENTATION.md
- `Screenshot 3 — Claude searching weather in Kochi via browser automation` --references--> `Browser Tool (tools/browser.py)`  [INFERRED]
  Mac-MCP/assets/screenshots/screenshot_3.png → Mac-MCP/IMPLEMENTATION.md
- `Lotus Banner Image (banner.png) — panoramic pink lotus pond painting` --conceptually_related_to--> `Lotus.app (Swift/SwiftUI Menu Bar App)`  [EXTRACTED]
  Mac-MCP/assets/banner.png → Mac-MCP/implementationmacosapp.md

## Hyperedges (group relationships)
- **macOS AX Accessibility Stack** — ax_core, ax_controls, ax_enums, ax_events, tree_service, watchdog_service [EXTRACTED 1.00]
- **Pluggable Screenshot Backend System** — desktop_screenshot, quartz_backend, mss_backend, pillow_backend [EXTRACTED 1.00]
- **Lotus Three-Layer Architecture (MCP + Telegram Bot + Control Panel)** — fastmcp_server, telegram_bot, lotus_swift_app [EXTRACTED 1.00]

## Communities

### Community 0 - "Swift Service Layer"
Cohesion: 0.06
Nodes (31): CaseIterable, Decodable, Equatable, LocalizedError, LogResponse, ServiceStatus, ObservableObject, Sendable (+23 more)

### Community 1 - "AX Accessibility + macOS Permissions"
Cohesion: 0.04
Nodes (55): macOS Accessibility Permission, Analytics Module (analytics.py / PostHog), App Logo (logo.png) — click/cursor icon on cream background, atomacos Library, AX Controls Module (ax/controls.py), AX Core Module (ax/core.py), AX Enums Module (ax/enums.py), AX Events / FocusObserver (ax/events.py) (+47 more)

### Community 2 - "Python Control Panel (app.py)"
Cohesion: 0.09
Nodes (23): _assets(), _bot_service_cmd(), disable_startup(), enable_startup(), fetch_ollama_models(), _get_bot_pid(), _is_bot_alive(), is_startup_enabled() (+15 more)

### Community 3 - "Desktop State + Window Tools"
Cohesion: 0.08
Nodes (21): Browser, DesktopState, has_process(), Size, Status, Window, Enum, AX accessibility tree traversal — replaces Windows UIA TreeWalker. (+13 more)

### Community 4 - "Desktop Input + Interaction"
Cohesion: 0.09
Nodes (18): _build_key_aliases(), Desktop, _get_key_aliases(), _get_keyboard(), _get_mouse(), parse_display_selection(), Resolve a key string to a pynput Key or single char., Return (active_window, all_windows) from NSWorkspace + AX. (+10 more)

### Community 5 - "Telegram Bot Handler"
Cohesion: 0.16
Nodes (35): battery_alert_check_loop(), _chat_reply(), cleanup_storage(), clipboard_tracker_loop(), cmd_callback(), cmd_help(), cmd_logs(), cmd_screenshot() (+27 more)

### Community 6 - "Filesystem Tests"
Cohesion: 0.06
Nodes (3): Tests for mac_mcp.filesystem.service — uses real /tmp, no macOS permissions need, A temp dir with some files for testing., tmp()

### Community 7 - "AX Low-Level Primitives"
Cohesion: 0.14
Nodes (27): ax_get_attribute(), ax_get_children(), ax_get_position(), ax_get_rect(), ax_get_size(), ax_get_windows(), ax_perform_action(), get_all_running_apps() (+19 more)

### Community 8 - "Swift UI Views"
Cohesion: 0.09
Nodes (8): Codable, ContentView, AppConfig, View, ControlPanelView, InstallerView, OllamaModelPicker, SetupView

### Community 9 - "Control API HTTP Server"
Cohesion: 0.16
Nodes (15): BaseHTTPRequestHandler, _Handler, _load_config(), _ollama_reachable(), Lotus Control API ================= Lightweight HTTP control server that runs in, Start the control server in a background daemon thread.      Tries ``port`` firs, Shut down the HTTP server and remove the port file., Called by bot_service.py to update the Telegram connection state. (+7 more)

### Community 10 - "Screenshot Backends"
Cohesion: 0.18
Nodes (9): capture(), _get_backend(), get_screenshot_backend(), _MssBackend, _PillowBackend, _QuartzBackend, Capture a screenshot. Returns (image, backend_name_used)., Rect (+1 more)

### Community 11 - "Filesystem View Tests"
Cohesion: 0.14
Nodes (8): _make_file(), Tests for mac_mcp.filesystem.views data models., test_file_to_string_contains_extension(), test_file_to_string_contains_path(), test_file_to_string_contains_read_only(), test_file_to_string_contains_size(), test_file_to_string_with_contents(), test_file_to_string_with_link_target()

### Community 12 - "AppState + Polling"
Cohesion: 0.2
Nodes (1): AppState

### Community 13 - "Community 13"
Cohesion: 0.15
Nodes (5): Analytics, PostHogAnalytics, user_id(), with_analytics(), Protocol

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (4): FocusObserver, AX focus monitoring via polling — replaces UIAutomation event handler., Polls for frontmost application changes and fires a callback on change., WatchDog

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (4): _make_window(), Tests for mac_mcp.desktop.views data models., test_desktop_state_windows_to_string_with_windows(), test_window_to_row()

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (16): AppState.swift (@Observable shared state, polling), Lotus Banner Image (banner.png) — panoramic pink lotus pond painting, Lotus Logo (lotus_logo.png) — hot pink geometric lotus mandala, Mac App Icon (mac_app_icon.png) — Lotus logo on rounded white square (macOS app icon style), Bot Service Process Manager (bot_service.py), Control API (control_api.py / HTTP on localhost:40510), ControlPanelView.swift (Main dashboard), Install Scripts (install.sh / uninstall.sh) (+8 more)

### Community 17 - "Community 17"
Cohesion: 0.16
Nodes (4): AppDelegate, NSApplicationDelegate, NSObject, NSWindowDelegate

### Community 18 - "Community 18"
Cohesion: 0.26
Nodes (12): bulk_delete_by_extension(), copy_path(), delete_path(), get_file_info(), get_latest_file(), list_directory(), move_path(), organize_folder() (+4 more)

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (1): Tests for mac_mcp.analytics — mocks PostHog, no network calls.

### Community 20 - "Community 20"
Cohesion: 0.17
Nodes (1): Tests for mac_mcp.desktop.shell executors.

### Community 21 - "Community 21"
Cohesion: 0.29
Nodes (3): Encodable, EmptyBody, LotusServiceClient

### Community 22 - "Community 22"
Cohesion: 0.33
Nodes (8): get_action_for_role(), get_element_label(), is_interactive(), is_scrollable(), is_structural(), is_visible(), AX role classification and label extraction., Best human-readable label for an element, trying attributes in priority order.

### Community 23 - "Community 23"
Cohesion: 0.2
Nodes (9): mock_ax(), mock_nsworkspace(), mock_pynput(), mock_quartz(), Shared pytest fixtures for mac-mcp tests., Mock ApplicationServices AX calls so tests run without Accessibility permission., Mock NSWorkspace so tests run without a running macOS session., Mock pynput keyboard/mouse controllers. (+1 more)

### Community 24 - "Community 24"
Cohesion: 0.22
Nodes (1): Tests for mac_mcp.desktop.utils — pure string helpers, no permissions needed.

### Community 25 - "Community 25"
Cohesion: 0.43
Nodes (6): _build_mcp(), _get_analytics(), _get_desktop(), main(), Run the Lotus Telegram bot., telegram_cmd()

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (6): _as_bool(), build_snapshot_response(), capture_desktop_state(), Snapshot / Screenshot shared helpers., _screenshot_scale(), _snapshot_profile_enabled()

### Community 27 - "Community 27"
Cohesion: 0.43
Nodes (4): Directory, File, format_size(), Data models and constants for filesystem operations.

### Community 28 - "Community 28"
Cohesion: 0.29
Nodes (8): AppleScript Executor (AppleScriptExecutor), AppleScript Executor (desktop/applescript.py), PowerShell Executor (Windows, replaced), Shell Executor (ShellExecutor), Defaults Tool (tools/defaults.py), Notification Tool (tools/notification.py), Registry Tool (Windows, replaced), Shell Tool (tools/shell.py)

### Community 29 - "Community 29"
Cohesion: 0.52
Nodes (6): is_already_running(), load_config(), Lotus Bot Service — macOS Background Process ===================================, remove_pid(), run_service(), write_pid()

### Community 30 - "Community 30"
Cohesion: 0.29
Nodes (1): Tests for mac_mcp.paths — just verifies the path constants make sense.

### Community 31 - "Community 31"
Cohesion: 0.52
Nodes (6): is_already_running(), load_config(), Lotus Bot Service — macOS Background Process ===================================, remove_pid(), run_service(), write_pid()

### Community 32 - "Community 32"
Cohesion: 0.53
Nodes (4): AppleScriptExecutor, execute(), notify(), ShellExecutor

### Community 33 - "Community 33"
Cohesion: 0.53
Nodes (4): AXAction, AXAttr, AXNotification, AXRole

### Community 34 - "Community 34"
Cohesion: 0.53
Nodes (4): get_all_desktops(), get_current_desktop(), is_window_on_current_desktop(), macOS Spaces (Virtual Desktop) awareness.  Phase 5 implementation: Option A — no

### Community 35 - "Community 35"
Cohesion: 0.33
Nodes (1): Tests for mac_mcp.permissions — mocks system calls.

### Community 36 - "Community 36"
Cohesion: 0.53
Nodes (4): launch(), Launch, switch, and resize macOS applications., resize(), switch()

### Community 37 - "Community 37"
Cohesion: 0.47
Nodes (4): get_all_apps(), invalidate_cache(), Discover installed .app bundles via Spotlight., Return {app_name_lower: .app bundle path} for all installed apps.

### Community 38 - "Community 38"
Cohesion: 0.6
Nodes (3): Input tools — Click, Type, Scroll, Move, Shortcut, Wait., register(), _resolve_label()

### Community 39 - "Community 39"
Cohesion: 0.6
Nodes (3): _esc(), Notification tool — macOS notifications and dialogs via osascript., register()

### Community 40 - "Community 40"
Cohesion: 0.5
Nodes (3): find_app(), Fuzzy app name resolution., Fuzzy-match an app name. Returns (matched_name, path) or None.

### Community 41 - "Community 41"
Cohesion: 0.4
Nodes (1): Tests for mac_mcp.spaces.core stub.

### Community 42 - "Community 42"
Cohesion: 0.4
Nodes (1): Theme

### Community 43 - "Community 43"
Cohesion: 0.5
Nodes (2): Strip Unicode Private Use Area characters that can cause display issues., remove_private_use_chars()

### Community 44 - "Community 44"
Cohesion: 0.67
Nodes (2): tools subpackage — registers all MCP tool definitions on a FastMCP instance., register_all()

### Community 45 - "Community 45"
Cohesion: 0.67
Nodes (2): Shell tool — bash/zsh command execution., register()

### Community 46 - "Community 46"
Cohesion: 0.67
Nodes (2): Snapshot and Screenshot tools — desktop state capture., register()

### Community 47 - "Community 47"
Cohesion: 0.67
Nodes (2): App tool — launch, resize, switch applications., register()

### Community 48 - "Community 48"
Cohesion: 0.67
Nodes (2): FileSystem tool — file and directory operations., register()

### Community 49 - "Community 49"
Cohesion: 0.67
Nodes (2): Clipboard tool — macOS pbcopy/pbpaste clipboard operations., register()

### Community 50 - "Community 50"
Cohesion: 0.67
Nodes (2): Process tool — list and kill running processes., register()

### Community 51 - "Community 51"
Cohesion: 0.67
Nodes (2): Defaults tool — read/write macOS user defaults (app preferences)., register()

### Community 52 - "Community 52"
Cohesion: 0.67
Nodes (2): enable_debug(), is_debug()

### Community 53 - "Community 53"
Cohesion: 0.67
Nodes (2): MultiSelect and MultiEdit tools — batch element interaction., register()

### Community 54 - "Community 54"
Cohesion: 0.67
Nodes (2): Scrape tool — fetch web page content., register()

### Community 55 - "Community 55"
Cohesion: 0.67
Nodes (1): check_and_warn()

### Community 56 - "Community 56"
Cohesion: 0.67
Nodes (2): App, LotusApp

### Community 57 - "Community 57"
Cohesion: 0.67
Nodes (3): Safari Playwright Limitation, Screenshot 3 — Claude searching weather in Kochi via browser automation, Browser Tool (tools/browser.py)

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (2): Spaces Core (spaces/core.py), Virtual Desktop Manager (Windows, vdm/)

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (2): Filesystem Service (filesystem/service.py), Filesystem Tool (tools/filesystem.py)

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (1): Config Module (config.py)

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (1): Paths Module (paths.py)

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (1): Clipboard Tool (tools/clipboard.py)

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (1): Process Tool (tools/process.py)

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (1): Scrape Tool (tools/scrape.py)

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (1): File Manager Tool (tools/fm.py)

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (1): macOS Automation Permission (per-app AppleScript)

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (1): Background Pond Image (bg_pond.png) — tall vertical lotus pond oil painting

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (1): Logo White (logo_white.png) — white/transparent variant

## Knowledge Gaps
- **106 isolated node(s):** `Lotus Bot Service — macOS Background Process ===================================`, `Lotus — macOS Control Panel ============================ CustomTkinter GUI for c`, `Return models available on the local Ollama server, or [] on failure.`, `Install a macOS menu bar status item using PyObjC.`, `Entry + refresh button that auto-populates a dropdown from Ollama.` (+101 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `AppState + Polling`** (17 nodes): `AppState.swift`, `AppState`, `.appendLog()`, `.fetchOllamaModels()`, `.init()`, `.markEnvReady()`, `.pollLogs()`, `.pollStatus()`, `.refreshStartupEnabled()`, `.reloadConfig()`, `.resetConfig()`, `.saveConfig()`, `.startBot()`, `.startPolling()`, `.stopBot()`, `.stopPolling()`, `.toggleStartup()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (12 nodes): `analytics()`, `test_analytics.py`, `Tests for mac_mcp.analytics — mocks PostHog, no network calls.`, `test_close_no_client()`, `test_close_shuts_down_client()`, `test_track_error_calls_capture()`, `test_track_tool_calls_capture()`, `test_track_tool_no_client()`, `test_user_id_is_string()`, `test_with_analytics_none_instance()`, `test_with_analytics_propagates_exception()`, `test_with_analytics_success()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (12 nodes): `test_shell_executor.py`, `Tests for mac_mcp.desktop.shell executors.`, `test_applescript_execute_exception()`, `test_applescript_execute_mocked_success()`, `test_applescript_execute_timeout()`, `test_applescript_notify_does_not_raise()`, `test_shell_execute_exception()`, `test_shell_execute_exit_code()`, `test_shell_execute_multiline()`, `test_shell_execute_stderr_captured()`, `test_shell_execute_success()`, `test_shell_execute_timeout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (9 nodes): `test_desktop_utils.py`, `Tests for mac_mcp.desktop.utils — pure string helpers, no permissions needed.`, `test_remove_private_use_chars_clean_string()`, `test_remove_private_use_chars_empty_string()`, `test_remove_private_use_chars_mixed()`, `test_remove_private_use_chars_only_private_use()`, `test_remove_private_use_chars_preserves_unicode()`, `test_remove_private_use_chars_removes_private_use()`, `test_remove_private_use_chars_removes_supplementary_private_use()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (7 nodes): `test_paths.py`, `Tests for mac_mcp.paths — just verifies the path constants make sense.`, `test_app_name()`, `test_cache_dir_is_path()`, `test_cache_dir_under_home_or_library()`, `test_data_dir_is_path()`, `test_data_dir_under_home_or_library()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (6 nodes): `test_permissions.py`, `Tests for mac_mcp.permissions — mocks system calls.`, `test_check_and_warn_import_errors()`, `test_check_and_warn_missing_accessibility()`, `test_check_and_warn_missing_screen_recording()`, `test_check_and_warn_with_full_permissions()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (5 nodes): `test_spaces.py`, `Tests for mac_mcp.spaces.core stub.`, `test_get_all_desktops()`, `test_get_current_desktop()`, `test_is_window_on_current_desktop_always_true()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (5 nodes): `Theme.swift`, `Theme`, `.body()`, `.display()`, `.mono()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (4 nodes): `utils.py`, `Strip Unicode Private Use Area characters that can cause display issues.`, `remove_private_use_chars()`, `utils.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (4 nodes): `__init__.py`, `__init__.py`, `tools subpackage — registers all MCP tool definitions on a FastMCP instance.`, `register_all()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (4 nodes): `shell.py`, `shell.py`, `Shell tool — bash/zsh command execution.`, `register()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (4 nodes): `snapshot.py`, `snapshot.py`, `Snapshot and Screenshot tools — desktop state capture.`, `register()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (4 nodes): `app.py`, `app.py`, `App tool — launch, resize, switch applications.`, `register()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (4 nodes): `filesystem.py`, `filesystem.py`, `FileSystem tool — file and directory operations.`, `register()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (4 nodes): `clipboard.py`, `clipboard.py`, `Clipboard tool — macOS pbcopy/pbpaste clipboard operations.`, `register()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (4 nodes): `process.py`, `process.py`, `Process tool — list and kill running processes.`, `register()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (4 nodes): `defaults.py`, `defaults.py`, `Defaults tool — read/write macOS user defaults (app preferences).`, `register()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (4 nodes): `config.py`, `enable_debug()`, `is_debug()`, `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (4 nodes): `multi.py`, `multi.py`, `MultiSelect and MultiEdit tools — batch element interaction.`, `register()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (4 nodes): `scrape.py`, `scrape.py`, `Scrape tool — fetch web page content.`, `register()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (3 nodes): `permissions.py`, `check_and_warn()`, `permissions.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (3 nodes): `App`, `LotusApp.swift`, `LotusApp`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (2 nodes): `Spaces Core (spaces/core.py)`, `Virtual Desktop Manager (Windows, vdm/)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (2 nodes): `Filesystem Service (filesystem/service.py)`, `Filesystem Tool (tools/filesystem.py)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `Config Module (config.py)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `Paths Module (paths.py)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `Clipboard Tool (tools/clipboard.py)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `Process Tool (tools/process.py)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `Scrape Tool (tools/scrape.py)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `File Manager Tool (tools/fm.py)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (1 nodes): `macOS Automation Permission (per-app AppleScript)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (1 nodes): `Background Pond Image (bg_pond.png) — tall vertical lotus pond oil painting`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (1 nodes): `Logo White (logo_white.png) — white/transparent variant`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Desktop` connect `Desktop Input + Interaction` to `Desktop State + Window Tools`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Why does `find_file()` connect `Telegram Bot Handler` to `Python Control Panel (app.py)`?**
  _High betweenness centrality (0.007) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `Swift UI Views` to `Swift Service Layer`?**
  _High betweenness centrality (0.007) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `Desktop` (e.g. with `Browser` and `DesktopState`) actually correct?**
  _`Desktop` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `Tree` (e.g. with `Desktop` and `AXAttr`) actually correct?**
  _`Tree` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Lotus Bot Service — macOS Background Process ===================================`, `Lotus — macOS Control Panel ============================ CustomTkinter GUI for c`, `Return models available on the local Ollama server, or [] on failure.` to the rest of the system?**
  _106 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Swift Service Layer` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._