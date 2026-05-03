import SwiftUI

struct SetupView: View {

    @EnvironmentObject private var state: AppState
    var editing = false
    var onDismiss: (() -> Void)? = nil

    @State private var token    = ""
    @State private var userIDs  = ""
    @State private var name     = ""
    @State private var model    = "phi3"
    @State private var errorMsg = ""

    private var logoURL: URL? {
        for n in ["lotus_logo.png", "logo_white.png", "logo.png"] {
            let u = AppConfig.baseDir.appendingPathComponent("assets/\(n)")
            if FileManager.default.fileExists(atPath: u.path) { return u }
        }
        return nil
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            VStack(spacing: 8) {
                logoView
                    .frame(width: 64, height: 64)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    .shadow(color: .black.opacity(0.12), radius: 6, y: 3)

                Text("Lotus")
                    .font(.title.bold())

                Text(editing ? "Update your settings below." : "Connect your Telegram bot to get started.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 28)
            .padding(.horizontal, 32)

            Divider()

            // Form
            Form {
                Section {
                    LabeledContent("Bot Token") {
                        TextField("123456:ABC-DEF…", text: $token)
                            .textFieldStyle(.plain)
                            .multilineTextAlignment(.trailing)
                            .font(Theme.mono(12))
                    }
                    LabeledContent("Allowed User IDs") {
                        TextField("123456789, 987654321", text: $userIDs)
                            .textFieldStyle(.plain)
                            .multilineTextAlignment(.trailing)
                    }
                    LabeledContent("Your Name") {
                        TextField("e.g. Jayash", text: $name)
                            .textFieldStyle(.plain)
                            .multilineTextAlignment(.trailing)
                    }
                } header: {
                    Label("Telegram Credentials", systemImage: "message.fill")
                } footer: {
                    Text("Get a bot token from @BotFather on Telegram. Find your user ID with @userinfobot.")
                }

                Section {
                    LabeledContent("AI Model") {
                        OllamaModelPicker(selected: $model)
                    }
                } header: {
                    Label("Ollama (AI Chat Fallback)", systemImage: "cpu")
                } footer: {
                    Text("Install Ollama via Homebrew, then run: ollama pull phi3")
                }
            }
            .formStyle(.grouped)
            .scrollDisabled(false)

            Divider()

            // Error
            if !errorMsg.isEmpty {
                Label(errorMsg, systemImage: "exclamationmark.triangle.fill")
                    .font(.callout)
                    .foregroundStyle(.red)
                    .padding(.horizontal, 24)
                    .padding(.top, 12)
            }

            // Actions
            HStack(spacing: 12) {
                if editing {
                    Button("Cancel") { onDismiss?() }
                        .buttonStyle(.bordered)
                        .controlSize(.large)
                        .keyboardShortcut(.cancelAction)
                }

                Button(action: save) {
                    Label(
                        editing ? "Save Settings" : "Save & Launch Bot",
                        systemImage: editing ? "checkmark" : "play.fill"
                    )
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .keyboardShortcut(.defaultAction)
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 16)
        }
        .frame(minWidth: 400, idealWidth: 460, maxWidth: .infinity,
               minHeight: 500, idealHeight: 600, maxHeight: .infinity)
        .onAppear {
            if let cfg = state.config {
                token   = cfg.telegram_token
                userIDs = cfg.allowed_user_id
                name    = cfg.name
                model   = cfg.model_name
            }
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
            Text("🌸").font(.system(size: 32))
        }
    }

    private func save() {
        let t   = token.trimmingCharacters(in: .whitespaces)
        let n   = name.trimmingCharacters(in: .whitespaces)
        let ids = userIDs.trimmingCharacters(in: .whitespaces)
        let m   = model.trimmingCharacters(in: .whitespaces)

        guard !t.isEmpty else { errorMsg = "Bot Token is required.";  return }
        guard !n.isEmpty else { errorMsg = "Your Name is required.";  return }
        guard t.contains(":") else {
            errorMsg = "Invalid token format — expected 123456:ABC…"
            return
        }
        errorMsg = ""

        let ts: String = {
            let f = DateFormatter()
            f.dateFormat = "yyyy-MM-dd HH:mm:ss"
            return f.string(from: Date())
        }()
        let cfg = AppConfig(
            name: n,
            telegram_token: t,
            allowed_user_id: ids,
            model_name: m.isEmpty ? "phi3" : m,
            created_at: ts
        )
        Task {
            await state.saveConfig(cfg)
            if !editing { await state.startBot() }
            onDismiss?()
        }
    }
}
