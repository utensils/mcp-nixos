# Release Workflow Guide for MCP-NixOS

## Overview

This guide explains how to properly release a new version without triggering duplicate CI/CD runs.

## Improved CI/CD Features

1. **Documentation-only changes skip tests**: The workflow now detects if only docs (*.md, LICENSE, etc.) were changed and skips the test suite entirely.

2. **Smart change detection**: Uses `paths-filter` to categorize changes into:
   - `code`: Actual code changes that require testing
   - `docs`: Documentation changes that don't need tests
   - `website`: Website changes that only trigger deployment

3. **Release via commit message**: Instead of manually tagging after merge (which causes duplicate runs), you can now trigger a release by including `release: v1.0.0` in your merge commit message.

## Release Process

### Option 1: Automatic Release (Recommended)

1. **Update version in code**:
   ```bash
   # Update version in pyproject.toml
   # Update __init__.py fallback version if needed
   ```

2. **Update RELEASE_NOTES.md**:
   - Add release notes for the new version at the top
   - Follow the existing format

3. **Create PR as normal**:
   ```bash
   gh pr create --title "Release version 1.0.0"
   ```

4. **Merge with release trigger**:
   When merging the PR, edit the merge commit message to include:
   ```
   Merge pull request #28 from utensils/refactor
   
   release: v1.0.0
   ```

5. **Automatic steps**:
   - CI detects the `release:` keyword
   - Creates and pushes the git tag
   - Creates GitHub release with notes from RELEASE_NOTES.md
   - Triggers PyPI publishing

### Option 2: Manual Release (Traditional)

1. **Merge PR normally**
2. **Wait for CI to complete**
3. **Create and push tag manually**:
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

## Benefits of the New Workflow

- **No duplicate runs**: The release process happens in the merge commit workflow
- **Skip unnecessary tests**: Documentation changes don't trigger full test suite
- **Atomic releases**: Tag, GitHub release, and PyPI publish happen together
- **Clear audit trail**: Release intention is documented in the merge commit

## Testing the Workflow

To test documentation-only changes:
```bash
# Make changes only to *.md files
git add README.md
git commit -m "docs: update README"
git push
# CI will skip tests!
```

To test the release process without actually releasing:
1. Create a test branch
2. Make a small change
3. Use the commit message pattern but with a test version
4. Verify the workflow runs correctly
5. Delete the test tag and release afterward

## Troubleshooting

- If the release job fails, you can manually create the tag and it will trigger the publish job
- The `paths-filter` action requires the full git history, so it uses `checkout@v4` without depth limits
- The release extraction uses `awk` to parse RELEASE_NOTES.md, so maintain the heading format

## Example PR Description for Releases

When creating a release PR, use this template:
```markdown
## Release v1.0.0

This PR prepares the v1.0.0 release.

### Checklist
- [ ] Version bumped in pyproject.toml
- [ ] RELEASE_NOTES.md updated
- [ ] All tests passing
- [ ] Documentation updated

### Release Instructions
When merging, use commit message:
```
Merge pull request #XX from utensils/branch-name

release: v1.0.0
```
```