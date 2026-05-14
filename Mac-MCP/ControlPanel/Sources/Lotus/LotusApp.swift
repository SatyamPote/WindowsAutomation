import SwiftUI

@main
struct LotusApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup("Lotus") {
            ContentView()
                .environmentObject(AppState.shared)
        }
        .defaultSize(width: 460, height: 640)
        .commands {
            CommandGroup(replacing: .newItem) {}
            CommandGroup(replacing: .help) {}
        }
    }
}
