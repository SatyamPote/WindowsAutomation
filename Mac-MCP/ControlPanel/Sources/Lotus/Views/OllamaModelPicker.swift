import SwiftUI

struct OllamaModelPicker: View {

    @Binding var selected: String
    @State private var models: [String] = []
    @State private var isLoading = false
    @State private var isOffline = false

    var body: some View {
        HStack(spacing: 6) {
            Picker("", selection: $selected) {
                if models.isEmpty {
                    Text(isLoading ? "Loading…" : "No models found")
                        .tag(selected)
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(models, id: \.self) { model in
                        Text(model).tag(model)
                    }
                }
            }
            .labelsHidden()
            .frame(maxWidth: .infinity)

            Button {
                refresh()
            } label: {
                Image(systemName: "arrow.clockwise")
                    .rotationEffect(.degrees(isLoading ? 360 : 0))
                    .animation(isLoading ? .linear(duration: 0.8).repeatForever(autoreverses: false) : .default, value: isLoading)
            }
            .buttonStyle(.borderless)
            .disabled(isLoading)
            .help("Refresh available Ollama models")

            if isOffline {
                Image(systemName: "wifi.slash")
                    .foregroundStyle(.orange)
                    .font(.caption)
                    .help("Ollama is not reachable")
            }
        }
        .onAppear { refresh() }
    }

    private func refresh() {
        isLoading = true
        isOffline = false
        Task {
            let fetched = await OllamaClient.shared.fetchModels()
            models = fetched
            isOffline = fetched.isEmpty
            if !fetched.isEmpty && !fetched.contains(selected) {
                selected = fetched[0]
            }
            isLoading = false
        }
    }
}
