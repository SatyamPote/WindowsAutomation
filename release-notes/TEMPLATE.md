<!--
  Release notes template. To use:
    cp release-notes/TEMPLATE.md release-notes/vX.Y.Z.md
    # edit, fill in highlights, remove unused sections
    git add release-notes/vX.Y.Z.md
    git commit -m "release notes: vX.Y.Z"

  When the workflow publishes vX.Y.Z, this file becomes the curated
  top section of the GitHub Release body. GitHub appends its own
  auto-generated "## What's Changed" PR list and Full Changelog link
  below this content.
-->

## What's Changed

- _Headline change in plain language — what users will notice first._
- _Second highlight, ideally one bullet per shipped PR/feature._
- _Third highlight._

## ✨ New

- _New feature or capability._

## 🐛 Fixes

- _Bug fix users will care about._

## 🔧 Internals

- _Refactor / dependency bump / build-system change worth mentioning._

## ⚠️ Breaking changes

- _If none, delete this section._
- _Otherwise, describe the break and the migration path._

## Install

1. Download `Lotus-<version>.dmg` below and drag **Lotus.app** to **Applications**.
2. Inside the `Mac-MCP/` folder, run `uv sync` to populate the Python venv.
3. Launch Lotus from `/Applications` (the 🌸 icon appears in your menu bar).

> The DMG is ad-hoc signed (not notarized). On first launch, right-click → **Open**, or run:
> ```bash
> xattr -d com.apple.quarantine /Applications/Lotus.app
> ```

See [SETUP.md](https://github.com/SatyamPote/Lotus/blob/main/Mac-MCP/SETUP.md) for the full guide.
