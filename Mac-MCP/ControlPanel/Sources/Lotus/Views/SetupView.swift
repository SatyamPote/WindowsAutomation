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
        guard let assets = AppConfig.assetsDir else { return nil }
        for n in ["lotus_logo.png", "logo_white.png", "logo.png"] {
            let u = assets.appendingPathComponent(n)
            if FileManager.default.fileExists(atPath: u.path) { return u }
        }
        return nil
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            ScrollView {
                fields
                    .padding(.horizontal, 28)
                    .padding(.vertical, 20)
            }
            Divider()
            actionBar
        }
        .frame(minWidth: 420, idealWidth: 460,
               minHeight: 540, idealHeight: 600)
        .onAppear(perform: populate)
    }

    // MARK: - Header

    private var header: some View {
        VStack(spacing: 6) {
            logoView
                .frame(width: 56, height: 56)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .shadow(color: .black.opacity(0.1), radius: 4, y: 2)

            Text(editing ? "Settings" : "Lotus Setup")
                .font(.title2.bold())

            Text(editing
                 ? "Edit your bot configuration below."
                 : "Enter your Telegram credentials to get started.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 22)
        .padding(.horizontal, 32)
    }

    // MARK: - Fields

    private var fields: some View {
        VStack(alignment: .leading, spacing: 20) {

            // ── Telegram credentials ──────────────────────────────────────
            sectionHeader("Telegram Credentials", icon: "paperplane.fill")

            field(
                label: "Bot Token",
                hint: "Get yours from @BotFather on Telegram",
                placeholder: "123456789:AABBccDD…",
                text: $token,
                isMonospaced: true,
                isSecure: false
            )

            field(
                label: "Allowed User IDs",
                hint: "Comma-separated — find your ID with @userinfobot",
                placeholder: "123456789, 987654321",
                text: $userIDs
            )

            field(
                label: "Your Name",
                hint: "Used in bot greeting messages",
                placeholder: "e.g. Jayash",
                text: $name
            )

            Divider()

            // ── AI model ──────────────────────────────────────────────────
            sectionHeader("Ollama AI Model", icon: "cpu")

            VStack(alignment: .leading, spacing: 6) {
                Text("Model")
                    .font(.callout.weight(.medium))
                OllamaModelPicker(selected: $model)
                Text("Install Ollama, then run: ollama pull phi3")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder
    private func sectionHeader(_ title: String, icon: String) -> some View {
        Label(title, systemImage: icon)
            .font(.footnote.weight(.semibold))
            .foregroundStyle(.secondary)
            .textCase(.uppercase)
    }

    @ViewBuilder
    private func field(
        label: String,
        hint: String,
        placeholder: String,
        text: Binding<String>,
        isMonospaced: Bool = false,
        isSecure: Bool = false
    ) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(label)
                .font(.callout.weight(.medium))
            TextField(placeholder, text: text)
                .textFieldStyle(.roundedBorder)
                .font(isMonospaced ? Theme.mono(13) : .body)
            Text(hint)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Action bar

    private var actionBar: some View {
        VStack(spacing: 0) {
            if !errorMsg.isEmpty {
                Label(errorMsg, systemImage: "exclamationmark.triangle.fill")
                    .font(.callout)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 24)
                    .padding(.top, 12)
            }

            HStack(spacing: 10) {
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
    }

    // MARK: - Logo

    @ViewBuilder
    private var logoView: some View {
        if let url = logoURL {
            AsyncImage(url: url) { phase in
                if let img = phase.image {
                    img.resizable().interpolation(.high).scaledToFill()
                } else { placeholder }
            }
        } else {
            placeholder
        }
    }

    private var placeholder: some View {
        ZStack {
            Color.accentColor.opacity(0.15)
            Text("🌸").font(.system(size: 28))
        }
    }

    // MARK: - Logic

    private func populate() {
        guard let cfg = state.config else { return }
        token   = cfg.telegram_token
        userIDs = cfg.allowed_user_id
        name    = cfg.name
        model   = cfg.model_name
    }

    private func save() {
        let t   = token.trimmingCharacters(in: .whitespaces)
        let n   = name.trimmingCharacters(in: .whitespaces)
        let ids = userIDs.trimmingCharacters(in: .whitespaces)
        let m   = model.trimmingCharacters(in: .whitespaces)

        guard !t.isEmpty        else { errorMsg = "Bot Token is required."; return }
        guard !n.isEmpty        else { errorMsg = "Your Name is required."; return }
        guard t.contains(":")   else { errorMsg = "Invalid token — expected 123456:ABC…"; return }
        errorMsg = ""

        let ts: String = {
            let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd HH:mm:ss"
            return f.string(from: Date())
        }()

        let cfg = AppConfig(
            name:            n,
            telegram_token:  t,
            allowed_user_id: ids,
            model_name:      m.isEmpty ? "phi3" : m,
            created_at:      ts
        )
        Task {
            await state.saveConfig(cfg)
            if !editing { await state.startBot() }
            onDismiss?()
        }
    }
}
