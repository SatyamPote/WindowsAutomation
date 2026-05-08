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
Runner: `macos-14` (Apple Silicon)

### Triggers

| Event | What runs | What ships |
|---|---|---|
| `push` to `main` (paths under `Mac-MCP/**`) | Build app + DMG | Workflow artifact only |
| `pull_request` (paths under `Mac-MCP/**`) | Build app + DMG | Workflow artifact only |
| `push` of tag `v*` (e.g. `v1.0.0`) | Build + publish GitHub Release | DMG attached to the Release |
| `workflow_dispatch` (manual button) | Build app + DMG | Workflow artifact only |

### Jobs

**`build`** — runs on every trigger
1. Checks out the repo
2. Prints macOS / Xcode / Swift versions for the build log
3. Installs [`uv`](https://docs.astral.sh/uv/) and runs `uv sync` to populate `Mac-MCP/.venv`
4. Resolves a version string:
   - On a `v*` tag → strips the `v` (e.g. `v1.2.3` → `1.2.3`)
   - Otherwise → `0.0.0-<short-sha>` (so dev DMGs are clearly marked)
5. Patches the resolved version into both `make_app.sh` and `make_dmg.sh`
   (their `VERSION="1.0.0"` lines)
6. Runs `ControlPanel/make_app.sh` → produces `Mac-MCP/Lotus.app`
7. Runs `ControlPanel/make_dmg.sh` → produces `Mac-MCP/dist/Lotus-<version>.dmg`
8. Uploads the DMG as a workflow artifact (retained 30 days)

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

### `swift build` fails with "command not found"
The runner needs Xcode CLT. `macos-14` images ship Xcode pre-installed —
the workflow logs the version with `xcodebuild -version`. If it changes
unexpectedly, pin the Xcode version with:

```yaml
- uses: maxim-lobanov/setup-xcode@v1
  with:
    xcode-version: '15.4'
```

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

### DMG build fails at the AppleScript styling step
The styling step is wrapped in `|| true` and is non-fatal — the DMG is
still produced, just without the custom window layout. CI runners run
headless and Finder may not respond to AppleScript reliably. To
investigate, download the workflow artifact and open the DMG locally to
confirm the icons are present.

### Release job says "Resource not accessible by integration"
The workflow declares `permissions: contents: write` at the top level.
If a fork or org policy strips that, re-add it explicitly to the
`release` job.

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
