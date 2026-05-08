# Release Notes

Curated release notes for **Lotus.app**, picked up by the
[`swift.yml`](../.github/workflows/swift.yml) workflow when publishing a
GitHub Release.

## Convention

- One file per release, named `v<MAJOR>.<MINOR>.<PATCH>.md`
  (e.g. `v1.0.0.md`, `v1.1.0-rc1.md`).
- The **filename's tag must match the git tag exactly** — the workflow
  reads `release-notes/${TAG}.md` where `TAG` is `v<version>`.
- Content is plain Markdown. It becomes the top section of the
  published GitHub Release body, **above** GitHub's auto-generated PR
  list and Full Changelog link.

## Adding notes for a new release

```bash
# 1. Copy the template
cp release-notes/TEMPLATE.md release-notes/v1.1.0.md

# 2. Edit — keep the curated highlights tight (3–8 bullets)
$EDITOR release-notes/v1.1.0.md

# 3. Commit and push
git add release-notes/v1.1.0.md
git commit -m "release notes: v1.1.0"
git push origin main

# 4. Tag and publish (or use the workflow_dispatch UI)
git tag -a v1.1.0 -m "Lotus v1.1.0"
git push origin v1.1.0
```

## Override at publish time

If you want to ship a release without committing a notes file (e.g. a
hotfix), use the workflow's manual `notes` input instead — see
[`.github/RELEASING.md`](../.github/RELEASING.md). The input value
overrides the file if both are present.

## Files

| File | Purpose |
|---|---|
| `TEMPLATE.md` | Starting point — copy and rename for each release. |
| `v1.0.0.md` | First public release. |
| `v<X.Y.Z>.md` | One per shipped release. |
