import AppKit
import SwiftUI

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {

    static private(set) var shared: AppDelegate!

    private var statusItem: NSStatusItem?

    override init() {
        super.init()
        AppDelegate.shared = self
    }

    // MARK: - NSApplicationDelegate

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        setupMenuBar()

        // Assign self as the window delegate once SwiftUI creates the window.
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(windowBecameKey(_:)),
            name: NSWindow.didBecomeKeyNotification,
            object: nil
        )
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false
    }

    // MARK: - NSWindowDelegate

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        sender.orderOut(nil)
        // Restore accessory policy so the app disappears from the Dock when hidden.
        NSApp.setActivationPolicy(.accessory)
        return false
    }

    // MARK: - Window management

    func showWindow() {
        // Accessory-policy apps need .regular to accept focus and bring a window to front.
        NSApp.setActivationPolicy(.regular)
        if let window = NSApp.windows.first(where: { !($0 is NSPanel) }) {
            window.makeKeyAndOrderFront(nil)
        }
        NSApp.activate(ignoringOtherApps: true)
    }

    // MARK: - Menu bar

    private func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        guard let button = statusItem?.button else { return }
        button.title = "🌸"
        button.toolTip = "Lotus — macOS Remote Control"

        let menu = NSMenu()

        let show = NSMenuItem(title: "Show Lotus", action: #selector(showWindowAction), keyEquivalent: "")
        show.target = self
        menu.addItem(show)

        let toggle = NSMenuItem(title: "Toggle Agent", action: #selector(toggleAgentAction), keyEquivalent: "")
        toggle.target = self
        menu.addItem(toggle)

        menu.addItem(.separator())

        let quit = NSMenuItem(title: "Quit Lotus", action: #selector(quitAction), keyEquivalent: "q")
        quit.target = self
        menu.addItem(quit)

        statusItem?.menu = menu
    }

    @objc private func windowBecameKey(_ notification: Notification) {
        guard let window = notification.object as? NSWindow, window.delegate == nil else { return }
        window.delegate = self
    }

    @objc private func showWindowAction() { showWindow() }

    @objc private func toggleAgentAction() {
        Task {
            let state = AppState.shared
            // serviceStatus is nil until polling starts (window hasn't been shown yet).
            // Fall back to the PID file so the toggle works from the menu bar too.
            let isRunning: Bool
            if let cached = state.serviceStatus {
                isRunning = cached.running
            } else {
                isRunning = await Task.detached { ServiceManager.shared.isProcessAlive() }.value
            }
            if isRunning {
                await state.stopAgent()
            } else {
                await state.startAgent()
            }
        }
    }

    @objc private func quitAction() {
        NSApp.terminate(nil)
    }
}
