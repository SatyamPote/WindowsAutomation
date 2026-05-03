import SwiftUI

struct InstallerView: View {

    @StateObject private var installer = InstallManager.shared
    @EnvironmentObject private var state: AppState

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            stepsList
            Divider()
            logConsole
            Divider()
            footer
        }
        .onAppear {
            // Auto-start installation as soon as the view appears
            if !installer.isRunning && !installer.isComplete {
                Task { await installer.runInstall() }
            }
        }
    }

    // MARK: - Header

    private var header: some View {
        VStack(spacing: 8) {
            Text("🌸")
                .font(.system(size: 48))
                .padding(.top, 4)

            Text("Setting up Lotus")
                .font(.title2.bold())

            Text(installer.isComplete
                 ? "All set! Lotus is ready to use."
                 : installer.hasFailed
                     ? "Something went wrong — see log below."
                     : installer.isRunning
                         ? "Installing required components…"
                         : "Lotus needs a few things before it can run.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)
        }
        .padding(.vertical, 20)
        .frame(maxWidth: .infinity)
    }

    // MARK: - Steps list

    private var stepsList: some View {
        VStack(spacing: 0) {
            ForEach(InstallStep.allCases, id: \.self) { step in
                stepRow(step)
                if step != InstallStep.allCases.last {
                    Divider().padding(.leading, 54)
                }
            }
        }
        .padding(.vertical, 4)
    }

    private func stepRow(_ step: InstallStep) -> some View {
        let status = installer.statuses[step] ?? .pending
        return HStack(spacing: 14) {
            stepIcon(status)
                .frame(width: 26, height: 26)

            VStack(alignment: .leading, spacing: 3) {
                Text(step.rawValue)
                    .font(.body.weight(.medium))
                if case .failed(let msg) = status {
                    Text(msg.prefix(120))
                        .font(.caption)
                        .foregroundStyle(.red)
                        .lineLimit(3)
                } else {
                    Text(step.description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()

            statusBadge(status)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
    }

    @ViewBuilder
    private func stepIcon(_ status: StepStatus) -> some View {
        switch status {
        case .pending:
            Image(systemName: "circle")
                .font(.title3)
                .foregroundStyle(.quaternary)
        case .running:
            ProgressView()
                .controlSize(.small)
        case .done:
            Image(systemName: "checkmark.circle.fill")
                .font(.title3)
                .foregroundStyle(.green)
        case .skipped:
            Image(systemName: "checkmark.circle.fill")
                .font(.title3)
                .foregroundStyle(Color.secondary.opacity(0.7))
        case .failed:
            Image(systemName: "xmark.circle.fill")
                .font(.title3)
                .foregroundStyle(.red)
        }
    }

    @ViewBuilder
    private func statusBadge(_ status: StepStatus) -> some View {
        Group {
            switch status {
            case .pending:
                Text("Pending").foregroundStyle(.tertiary)
            case .running:
                Text("Working…").foregroundStyle(.orange)
            case .done:
                Text("Installed").foregroundStyle(.green)
            case .skipped:
                Text("Ready").foregroundStyle(.secondary)
            case .failed:
                Text("Failed").foregroundStyle(.red)
            }
        }
        .font(.caption.weight(.medium))
    }

    // MARK: - Log console

    private var logConsole: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 1) {
                    ForEach(Array(installer.logLines.enumerated()), id: \.offset) { idx, line in
                        Text(line)
                            .font(Theme.mono(11))
                            .foregroundStyle(.primary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .id(idx)
                    }
                }
                .padding(8)
            }
            .frame(height: 110)
            .background(Color(nsColor: .controlBackgroundColor))
            .onChange(of: installer.logLines.count) { _ in
                if let last = installer.logLines.indices.last {
                    proxy.scrollTo(last, anchor: .bottom)
                }
            }
        }
    }

    // MARK: - Footer

    private var footer: some View {
        HStack(spacing: 10) {
            if installer.hasFailed {
                Button("Retry") {
                    Task { await installer.runInstall() }
                }
                .buttonStyle(.bordered)
                .controlSize(.large)
            }

            if installer.isComplete {
                Button {
                    state.markEnvReady()
                } label: {
                    Label("Continue", systemImage: "arrow.right")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .keyboardShortcut(.defaultAction)

            } else if installer.isRunning {
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Installing…")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
            } else {
                Button {
                    Task { await installer.runInstall() }
                } label: {
                    Label("Install", systemImage: "arrow.down.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
    }
}
