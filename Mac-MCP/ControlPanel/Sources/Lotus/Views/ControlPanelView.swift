import SwiftUI

struct ControlPanelView: View {

    @EnvironmentObject private var state: AppState
    @State private var showSettings = false
    @State private var showResetConfirm = false

    private var isRunning: Bool { state.serviceStatus?.running == true }

    private var logoURL: URL? {
        for n in ["lotus_logo.png", "logo_white.png", "logo.png"] {
            let u = AppConfig.baseDir.appendingPathComponent("assets/\(n)")
            if FileManager.default.fileExists(atPath: u.path) { return u }
        }
        return nil
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                headerRow
                    .padding(.bottom, 20)

                statusCard
                    .padding(.bottom, 16)

                controlButtons
                    .padding(.bottom, 20)

                Divider()
                    .padding(.bottom, 16)

                optionsSection
                    .padding(.bottom, 16)

                Divider()
                    .padding(.bottom, 16)

                logSection

                if let err = state.lastError {
                    Label(err, systemImage: "exclamationmark.triangle.fill")
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.top, 8)
                }
            }
            .padding(20)
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { showSettings = true } label: {
                    Label("Settings", systemImage: "gear")
                }
                .help("Edit bot configuration")
            }
            ToolbarItem(placement: .destructiveAction) {
                Button(role: .destructive) {
                    guard !isRunning else {
                        state.appendLog("⚠ Stop the bot before resetting.")
                        return
                    }
                    showResetConfirm = true
                } label: {
                    Label("Reset Config", systemImage: "arrow.counterclockwise")
                }
                .help("Delete saved credentials")
            }
        }
        .sheet(isPresented: $showSettings) {
            SetupView(editing: true) { showSettings = false }
                .environmentObject(state)
        }
        .confirmationDialog(
            "Reset all configuration?",
            isPresented: $showResetConfirm,
            titleVisibility: .visible
        ) {
            Button("Reset", role: .destructive) {
                Task { await state.resetConfig() }
            }
        } message: {
            Text("This deletes your saved credentials. The running bot service is not affected until you stop it.")
        }
        .onAppear {
            state.startPolling()
            state.refreshStartupEnabled()
            if state.logLines.isEmpty { state.appendLog("Lotus ready.") }
        }
    }

    // MARK: - Header

    private var headerRow: some View {
        HStack(spacing: 14) {
            logoView
                .frame(width: 48, height: 48)
                .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))
                .shadow(color: .black.opacity(0.12), radius: 4, y: 2)

            VStack(alignment: .leading, spacing: 2) {
                Text("Lotus")
                    .font(.title2.bold())
                HStack(spacing: 4) {
                    Text("Hello \(state.config?.name ?? "there")")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    ollamaBadge
                }
            }
            Spacer()
        }
    }

    @ViewBuilder
    private var logoView: some View {
        if let url = logoURL {
            AsyncImage(url: url) { phase in
                if let img = phase.image {
                    img.resizable().interpolation(.high).scaledToFill()
                } else {
                    placeholderLogo
                }
            }
        } else {
            placeholderLogo
        }
    }

    private var placeholderLogo: some View {
        ZStack {
            Color.accentColor.opacity(0.15)
            Text("🌸").font(.system(size: 26))
        }
    }

    @ViewBuilder
    private var ollamaBadge: some View {
        let model     = state.serviceStatus?.ollama_model ?? state.config?.model_name ?? "—"
        let reachable = state.serviceStatus?.ollama_reachable ?? false
        Label(model, systemImage: "cpu")
            .font(.caption2.monospaced())
            .foregroundStyle(reachable ? .green : .secondary)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(Color.secondary.opacity(0.12), in: Capsule())
    }

    // MARK: - Status card

    private var statusCard: some View {
        GroupBox {
            HStack(spacing: 12) {
                statusDot
                VStack(alignment: .leading, spacing: 3) {
                    statusHeadline
                    if let st = state.serviceStatus, st.running {
                        Text("PID \(st.pid)  ·  up \(st.uptimeFormatted)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
            }
            .padding(.vertical, 4)
        } label: {
            Label("Bot Status", systemImage: "server.rack")
                .font(.headline)
        }
    }

    private var statusDot: some View {
        Circle()
            .fill(dotColor)
            .frame(width: 10, height: 10)
            .overlay(
                Circle()
                    .stroke(dotColor.opacity(0.35), lineWidth: 4)
            )
    }

    private var dotColor: Color {
        if state.isStarting || state.isStopping { return .orange }
        return isRunning ? .green : Color(nsColor: .tertiaryLabelColor)
    }

    @ViewBuilder
    private var statusHeadline: some View {
        if isRunning {
            Text("Running").font(.body.weight(.semibold)).foregroundStyle(.green)
        } else if state.isStarting {
            Text("Starting…").font(.body).foregroundStyle(.orange)
        } else if state.isStopping {
            Text("Stopping…").font(.body).foregroundStyle(.orange)
        } else {
            Text("Stopped").font(.body).foregroundStyle(.secondary)
        }
    }

    // MARK: - Controls

    private var controlButtons: some View {
        HStack(spacing: 10) {
            Button {
                Task { await state.startBot() }
            } label: {
                Label("Start Bot", systemImage: "play.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(isRunning || state.isStarting)

            Button {
                Task { await state.stopBot() }
            } label: {
                Label("Stop Bot", systemImage: "stop.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .controlSize(.large)
            .tint(.red)
            .disabled(!isRunning || state.isStopping)
        }
    }

    // MARK: - Options

    private var optionsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Toggle(isOn: Binding(
                get: { state.startupEnabled },
                set: { val in Task { await state.toggleStartup(val) } }
            )) {
                VStack(alignment: .leading, spacing: 2) {
                    Label("Start at Login", systemImage: "bolt.fill")
                        .font(.body.weight(.medium))
                    Text("Automatically launch the bot when you log in")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .toggleStyle(.switch)

            Label("Closing this window keeps the bot running in the menu bar.", systemImage: "lock.fill")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Log

    private var logSection: some View {
        GroupBox {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 1) {
                        ForEach(Array(state.logLines.enumerated()), id: \.offset) { idx, line in
                            Text(line)
                                .font(Theme.mono(11))
                                .foregroundStyle(.primary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .id(idx)
                        }
                    }
                    .padding(8)
                }
                .frame(minHeight: 120, maxHeight: .infinity)
                .onChange(of: state.logLines.count) { _ in
                    withAnimation {
                        proxy.scrollTo(state.logLines.count - 1, anchor: .bottom)
                    }
                }
            }
        } label: {
            HStack {
                Label("Console Output", systemImage: "terminal")
                    .font(.headline)
                Spacer()
                Button("Clear") {
                    state.logLines.removeAll()
                }
                .buttonStyle(.borderless)
                .font(.caption)
                .foregroundStyle(.secondary)
            }
        }
    }
}
