---
allowed-tools: Bash, Read, Glob, Grep, TodoWrite
description: Review and publish the Release Please release PR, then verify every registry
---

# Release

Releases are managed by Release Please. Do not edit the version, create a tag, or create a GitHub Release by hand during the normal release path.

## How it works

1. Conventional commits merged to `main` update the open `release: vX.Y.Z` PR.
2. The release PR updates `pyproject.toml`, `.release-please-manifest.json`, and `RELEASE_NOTES.md`.
3. Merging that PR makes Release Please create the matching tag and GitHub Release.
4. The resulting `release.published` event runs the existing trusted-publisher workflow, which publishes PyPI, Docker Hub, GHCR, and FlakeHub artifacts from that exact tag.
5. `ci.yml` only validates builds; it does not publish rolling container images.

Version rules:

- `fix:` produces a patch release.
- `feat:` produces a minor release.
- `fix!:`, `feat!:`, or a `BREAKING CHANGE:` footer produces a major release.
- Non-user-facing `ci:`, `docs:`, `test:`, `refactor:`, `build:`, and `chore:` commits are hidden and do not cause a release by themselves.

## Release checklist

### 1. Review the release PR

```bash
gh pr list --search 'release: in:title is:open' --json number,title,url,headRefName
gh pr view <PR_NUMBER> --json files,commits,reviews,statusCheckRollup
git log "$(git describe --tags --abbrev=0)..origin/main" --oneline
```

Confirm that:

- the proposed SemVer bump matches every included change;
- `RELEASE_NOTES.md` is complete and calls out breaking changes;
- `pyproject.toml` and `.release-please-manifest.json` contain the same version;
- CI and review are green.

For the first automated release, verify that the migration merge commit's one-time `Release-As: 3.0.0` footer was honored. This major bump is required because Intel macOS flake outputs were removed.

### 2. Merge the release PR

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

The `Release Please` workflow owns tag creation and the GitHub Release. Its authenticated release event starts the `Publish Package` workflow, which owns every publication job. Never create or move the release tag manually.

### 3. Watch publication

```bash
gh run list --workflow release-please.yml --limit 3
gh run list --workflow publish.yml --limit 3
gh run watch <RELEASE_PLEASE_RUN_ID>
gh run watch <PUBLISH_RUN_ID>
gh run view <RUN_ID> --log-failed
```

If PyPI/Docker or FlakeHub fails after the tag exists, fix the cause and rerun only the relevant recovery workflow with the immutable release tag:

```bash
gh workflow run publish.yml -f tag=vX.Y.Z -f docker_only=true
gh workflow run deploy-flakehub.yml -f tag=vX.Y.Z
```

The manual package workflow intentionally cannot publish PyPI. A failed PyPI upload must be retried from the failed job in the original `Publish Package` run after confirming that no partial version exists.

### 4. Independently verify public artifacts

```bash
VERSION=X.Y.Z

gh release view "v$VERSION" --json tagName,isDraft,isPrerelease,publishedAt,url,targetCommitish
curl --fail --silent "https://pypi.org/pypi/mcp-nixos/$VERSION/json" | jq -r .info.version
uvx "mcp-nixos@$VERSION" --help

docker buildx imagetools inspect "utensils/mcp-nixos:$VERSION"
docker buildx imagetools inspect "ghcr.io/utensils/mcp-nixos:$VERSION"
docker run --rm "utensils/mcp-nixos:$VERSION" --help

curl --fail --silent https://api.flakehub.com/f/utensils/mcp-nixos \
  | jq -r .version
nix flake metadata "https://flakehub.com/f/utensils/mcp-nixos/$VERSION"
```

Verify that the tag and GitHub Release target the release PR merge commit, PyPI reports the exact version, both container manifests contain `linux/amd64` and `linux/arm64`, the container starts, and FlakeHub reports the exact version.

## Guardrails

- Treat published tags and package versions as immutable; do not delete or retarget them to repair a release.
- Do not publish from an unmerged branch or a dirty worktree.
- Do not merge a release PR with incomplete notes or a mismatched version.
- Do not assume a green workflow means propagation succeeded; verify each public registry independently.
