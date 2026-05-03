import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        Group {
            if !state.envReady {
                InstallerView()
            } else if state.config == nil {
                SetupView()
            } else {
                ControlPanelView()
            }
        }
        .frame(minWidth: 400, idealWidth: 460, maxWidth: .infinity,
               minHeight: 500, idealHeight: 640, maxHeight: .infinity)
    }
}
