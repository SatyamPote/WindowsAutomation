import SwiftUI
import UniformTypeIdentifiers

struct BaseDirPickerView: View {

    @EnvironmentObject private var state: AppState
    @State private var errorMessage = ""
    @State private var showPicker = false

    var body: some View {
        VStack(spacing: 20) {
            Spacer()

            Image(systemName: "folder.badge.questionmark")
                .font(.system(size: 52))
                .foregroundStyle(.secondary)
                .symbolRenderingMode(.hierarchical)

            VStack(spacing: 6) {
                Text("Locate Mac-MCP Folder")
                    .font(.title2.bold())

                Text("Lotus couldn't find the Mac-MCP project folder automatically.\nSelect the folder that contains bot_service.py.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }

            Button {
                showPicker = true
            } label: {
                Label("Choose Folder…", systemImage: "folder")
                    .frame(minWidth: 180)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .keyboardShortcut(.defaultAction)

            if !errorMessage.isEmpty {
                Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                    .font(.callout)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
            }

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .fileImporter(
            isPresented: $showPicker,
            allowedContentTypes: [.folder],
            allowsMultipleSelection: false,
            onCompletion: handlePickerResult
        )
    }

    private func handlePickerResult(_ result: Result<[URL], Error>) {
        switch result {
        case .success(let urls):
            guard let url = urls.first else { return }
            let accessed = url.startAccessingSecurityScopedResource()
            defer { if accessed { url.stopAccessingSecurityScopedResource() } }

            guard FileManager.default.fileExists(atPath: url.appendingPathComponent("bot_service.py").path) else {
                errorMessage = "bot_service.py not found in that folder — please select the Mac-MCP directory."
                return
            }
            UserDefaults.standard.set(url.path, forKey: "com.lotus.basedir")
            state.reloadConfig()
            state.appendLog("📁 Mac-MCP folder set: \(url.path)")
            state.objectWillChange.send()

        case .failure(let error):
            errorMessage = error.localizedDescription
        }
    }
}
