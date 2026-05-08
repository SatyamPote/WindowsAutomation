# Releasing Lotus.app

This repo ships **Lotus.app** as a macOS DMG built by the
[`swift.yml`](workflows/swift.yml) GitHub Actions workflow.

This document explains:

1. What the workflow does and when it runs
2. How to cut an official release
3. How to test the same build locally
4. Troubleshooting common failures

---

## 1. Workflow overview

File: `.github/workflows/swift.yml`
Runner: `macos-15` (Apple Silicon, Xcode 16 / Swift 6)

> **Why macos-15?** `Package.swift` declares `swift-tools-version: 6.0`,
> which requires Xcode 16+. The older `macos-14` runner ships Xcode 15 /
> Swift 5.10 and fails with `package is using Swift tools version 6.0.0
> but the installed version is 5.10.0`. The workflow also pins Xcode 16
> explicitly via `maxim-lobanov/setup-xcode` so the build doesn't break
> if GitHub changes the default image toolchain.

### Triggers

| Event | What runs | What ships |
|---|---|---|
| `push` to `main` (paths under `Mac-MCP/**`) | Build app + DMG | Workflow artifact only |
| `pull_request` (paths under `Mac-MCP/**`) | Build app + DMG | Workflow artifact only |
| `push` of tag `v*` (e.g. `v1.0.0`) | Build + publish GitHub Release | DMG attached to the Release |
| `workflow_dispatch` (manual, `publish=false`) | Build app + DMG | Workflow artifact only |
| `workflow_dispatch` (manual, `publish=true` + `version`) | Build + publish GitHub Release (creates tag) | DMG attached to the Release |

### Jobs

**`build`** — runs on every trigger
1. Checks out the repo
2. Pins Xcode 16 via `maxim-lobanov/setup-xcode@v1` (Swift 6 support)
3. Prints macOS / Xcode / Swift versions for the build log
4. Installs [`uv`](https://docs.astral.sh/uv/) and runs `uv sync` to populate `Mac-MCP/.venv`
5. Resolves a version string:
   - On a `v*` tag → strips the `v` (e.g. `v1.2.3` → `1.2.3`)
   - Otherwise → `0.0.0-<short-sha>` (so dev DMGs are clearly marked)
6. Patches the resolved version into both `make_app.sh` and `make_dmg.sh`
   (their `VERSION="1.0.0"` lines)
7. Runs `ControlPanel/make_app.sh` → produces `Mac-MCP/Lotus.app`
8. **Verify Lotus.app** — checks the bundle exists, the binary is
   executable, and ad-hoc code signature is valid
9. Runs `ControlPanel/make_dmg.sh` → produces `Mac-MCP/dist/Lotus-<version>.dmg`
10. **Verify DMG** — mounts the DMG to a temp dir and confirms
    `Lotus.app` and the `Applications` symlink are inside, then prints
    the SHA-256
11. Uploads the DMG as a workflow artifact (retained 30 days)

> **Note on DMG window styling:** `make_dmg.sh` detects `$CI` /
> `$GITHUB_ACTIONS` and skips the AppleScript Finder-styling step on
> headless runners (it requires an interactive Finder session and is
> unreliable in CI). The DMG is still produced with the background
> image staged in `.background/`, the `Applications` symlink, and the
> bundled app — only the custom icon positions are missing. For a
> fully styled DMG, build locally via `bash ControlPanel/make_dmg.sh`,
> or pre-bake a `.DS_Store` and copy it in (see Future improvements).

**`release`** — runs only on `v*` tag pushes
1. Downloads the DMG built by the `build` job
2. Computes `SHA256SUMS.txt`
3. Creates a GitHub Release named `Lotus v<version>` with:
   - The DMG attached
   - The SHA256 checksums file attached
   - Auto-generated release notes (PRs + commits since previous tag)
   - `prerelease: true` if the tag contains `-` (e.g. `v1.0.0-rc1`)

### Required permissions

The workflow requests `contents: write` so it can create releases. No other
secrets are required for the current ad-hoc-signed build. If/when we add
notarization, additional secrets (`APPLE_ID`, `APPLE_TEAM_ID`,
`APPLE_APP_PASSWORD`, signing certs) will need to be added under
**Settings → Secrets and variables → Actions**.

---

## 2. Cutting a release

You have two options.

### Option A — From the GitHub UI (recommended for most cases)

1. Go to **Actions → Build & Release Lotus.app → Run workflow**
2. Set **Publish a GitHub Release with the built DMG** to `true`
3. Enter **Release version** (e.g. `1.0.0` — `v` prefix optional)
4. Optionally paste curated **Release notes** (Markdown) into the
   `notes` field — these become the "What's Changed" section
5. Click **Run workflow**

The workflow:
- Builds `Lotus.app` and the DMG with that version stamped in
- Creates a tag `v<version>` automatically
- Publishes a GitHub Release with the DMG + checksums + your curated
  notes, followed by the auto-generated PR/commit list

> If `publish=true` is set without a version, the run fails fast in the
> **Validate publish input** step.

### Option B — From the CLI (push a tag)

```bash
# 1. Make sure main is green and you're on it
git checkout main
git pull --ff-only

# 2. Tag the release (semver, prefixed with v)
git tag -a v1.0.0 -m "Lotus v1.0.0"

# 3. Push the tag — this triggers the release job
git push origin v1.0.0
```

What happens next:

1. `swift.yml` fires on the tag push
2. `build` job assembles `Lotus.app` and `Lotus-1.0.0.dmg`
3. `release` job creates a GitHub Release at
   `https://github.com/<owner>/<repo>/releases/tag/v1.0.0`
4. The DMG and `SHA256SUMS.txt` are attached
5. Release notes are auto-generated from PRs/commits since the previous tag

### Curated "What's Changed" notes

The Release body is composed in this order:

1. **Curated section** (your hand-written highlights) — sourced from
   one of:
   - The `notes` input on `workflow_dispatch` (Option A), **or**
   - A checked-in file `release-notes/v<version>.md` (Option B or A
     when no `notes` input is given)
   - If neither is provided, this section is empty.
2. **Auto-generated section** (PR list + Full Changelog link) —
   appended by GitHub when `generate_release_notes: true`.

To match the [Ollama](https://github.com/ollama/ollama/releases) style
where the top of the release page is a curated bullet list under
"What's Changed", commit a file before tagging:

```bash
# Write the highlights for the next release
cat > release-notes/v1.1.0.md <<'EOF'
## What's Changed

- New `Toggle Bot` keyboard shortcut (⌘⇧L) from the menu bar.
- Bot service now retries Ollama connectivity every 30s instead of bailing.
- DMG installer compressed ~40% smaller via `zlib-level=9`.
EOF

git add release-notes/v1.1.0.md
git commit -m "release notes: v1.1.0"
git push

# Then either push the tag (Option B) or run the workflow (Option A)
git tag -a v1.1.0 -m "Lotus v1.1.0"
git push origin v1.1.0
```

The release body will be that curated section, followed by GitHub's
auto-generated "## What's Changed" PR list and `**Full Changelog**` diff
link.

### Pre-releases

Tag with a hyphenated suffix to mark it as a pre-release in GitHub's UI:

```bash
git tag -a v1.1.0-rc1 -m "Lotus v1.1.0 release candidate 1"
git push origin v1.1.0-rc1
```

### Re-running a failed release

If the `release` job fails (e.g. permissions or network), re-run it from
the **Actions** tab. The `build` job's artifact is still available for
24 hours, but it's safer to delete the tag and re-push:

```bash
git tag -d v1.0.0
git push --delete origin v1.0.0
git tag -a v1.0.0 -m "Lotus v1.0.0"
git push origin v1.0.0
```

---

## 3. Local equivalents

The CI build is intentionally a thin wrapper around the same scripts you
run locally — there is no CI-only build path.

```bash
cd Mac-MCP

# 1. Python deps (creates .venv used by the bundled bot service)
uv sync

# 2. Build the app
bash ControlPanel/make_app.sh
# → Mac-MCP/Lotus.app

# 3. Build the DMG (uses existing Lotus.app)
bash ControlPanel/make_dmg.sh
# → Mac-MCP/dist/Lotus-1.0.0.dmg

# Or build app + DMG in one go
bash ControlPanel/make_dmg.sh --build
```

To match what CI does on a tag, edit the `VERSION="1.0.0"` line in both
`make_app.sh` and `make_dmg.sh` before running them, or `sed` it inline:

```bash
VERSION=1.2.3
sed -i '' "s/^VERSION=\"1.0.0\"/VERSION=\"$VERSION\"/" \
  ControlPanel/make_app.sh ControlPanel/make_dmg.sh
```

---

## 4. Artifacts

| Artifact | Path in repo | Path in workflow |
|---|---|---|
| Built app bundle | `Mac-MCP/Lotus.app` | n/a (used by next step) |
| DMG installer | `Mac-MCP/dist/Lotus-<version>.dmg` | `artifacts/Lotus-<version>.dmg` |
| Checksums | n/a | `artifacts/SHA256SUMS.txt` |

---

## 5. Troubleshooting

### `swift build` fails with "Swift tools version" mismatch
`Package.swift` requires Swift 6 (Xcode 16+). The workflow pins Xcode 16
explicitly:

```yaml
- uses: maxim-lobanov/setup-xcode@v1
  with:
    xcode-version: '16.0'
```

If a future Swift bump is needed, update both `Package.swift` and the
`xcode-version` here. To see what Xcode versions are available on the
runner image, check the
[macos-15 image manifest](https://github.com/actions/runner-images/blob/main/images/macos/macos-15-Readme.md).

### `uv sync` is slow / flaky
Add a cache step before `uv sync`:

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/uv
      Mac-MCP/.venv
    key: uv-${{ hashFiles('Mac-MCP/uv.lock') }}
```

### DMG window has no custom layout / background
Expected on CI. `make_dmg.sh` detects `$CI` / `$GITHUB_ACTIONS` and
skips the AppleScript Finder-styling step because headless runners
don't have an interactive Finder. The DMG itself is functional — the
bundled `Lotus.app`, the `Applications` symlink, and the background
image (`.background/background.png`) are all present.

To get a styled DMG for an actual release, either:
- Build locally with `bash ControlPanel/make_dmg.sh` and upload the DMG
  manually to the GitHub Release, **or**
- Pre-bake a `.DS_Store` once locally and commit it. Then have
  `make_dmg.sh` copy it into the staging dir on CI:
  ```bash
  # One-time, locally:
  bash ControlPanel/make_dmg.sh             # produces a styled DMG
  hdiutil attach dist/Lotus-1.0.0.dmg -nobrowse
  cp "/Volumes/Lotus 1.0.0/.DS_Store" ControlPanel/dmg-template.DS_Store
  hdiutil detach "/Volumes/Lotus 1.0.0"
  git add ControlPanel/dmg-template.DS_Store
  ```
  Then in `make_dmg.sh`, replace the AppleScript block with
  `cp ControlPanel/dmg-template.DS_Store "$STAGING/.DS_Store"` before
  the `hdiutil convert` step.

### DMG fails to mount in the "Verify DMG" step
The verify step mounts the freshly-built DMG and asserts that
`Lotus.app` and the `Applications` symlink are inside. If this fails,
the DMG itself is broken — common causes:
- `make_app.sh` produced an empty/incomplete `Lotus.app` (Swift compile
  error masked because the script doesn't `set -e` carefully)
- The staging dir got polluted by a previous failed run (rare on
  ephemeral CI runners, but worth a `rm -rf` if reproducing locally)

### Release job says "Resource not accessible by integration"
The workflow declares `permissions: contents: write` at the top level.
If a fork or org policy strips that, re-add it explicitly to the
`release` job.

### "Publish GitHub Release" job shows "skipped"
This is expected on every push that isn't a release. The job is gated:

```yaml
if: |
  startsWith(github.ref, 'refs/tags/v') ||
  (github.event_name == 'workflow_dispatch' && inputs.publish == true)
```

It only runs when:
- A tag matching `v*` is pushed (Option B above), **or**
- The workflow is dispatched manually with `publish=true` (Option A)

If you want a release, use one of those two paths. Pushes to `main`
intentionally don't publish.

### Tag was pushed but no release appeared
Check the **Actions** tab for the run. Common causes:
- Tag pushed to a branch other than `main` (the `paths:` filter on
  `push` is for branches, not tags — tag triggers ignore `paths`, so
  this is rarely the issue, but worth sanity-checking)
- A previous release with the same tag exists — delete it from the
  Releases page and re-run

---

## 6. Future improvements

These aren't blockers for the current release, but worth tracking:

- [ ] **Apple notarization** — sign with a Developer ID cert, run
  `xcrun notarytool submit`, staple. Removes the Gatekeeper warning on
  first launch.
- [ ] **Universal binary** — explicit `swift build -c release --arch arm64 --arch x86_64`
  and `lipo` if we want Intel support.
- [ ] **Cache `uv` and `swift build`** — currently rebuilds from scratch
  every run (~3–5 min). Caching cuts this to under a minute.
- [ ] **Sparkle auto-updates** — generate appcast.xml in the same
  workflow, host the DMGs on Releases, point the app at the appcast.
