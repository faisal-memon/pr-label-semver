# pr-label-semver

Use pull request labels to update semantic version tags.

- Labels `semver:major`, `semver:minor`, or `semver:patch` update the corresponding part of semantic version
- Defaults to `patch` if no label is specified

## Quick Start

```yaml
name: Release Build

on:
  push:
    branches: [main]

concurrency:
  group: release-${{ github.repository }}
  cancel-in-progress: false

permissions:
  contents: write
  pull-requests: read

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Compute next version
        id: bump
        uses: faisal-memon/pr-label-semver@v0
        with:
          github-token: ${{ github.token }}

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v3
        with:
          tag_name: ${{ steps.bump.outputs.new-tag }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

> [!NOTE]
> - Ensure `actions/checkout` uses `fetch-depth: 0`
> - GitHub-hosted runners already include `python3`; self-hosted runners need Python 3 available on `PATH`
> - The action computes the tag only; the following release step should create it after publishing succeeds
> - Requires `pull-requests: read` when `version-bump` is empty (PR-label resolution path)
> - Must configure workflow `concurrency` with `cancel-in-progress: false` to avoid tag collisions

## Release workflow with an optional floating major tag

The action computes the next tag but does not write it. A release workflow can publish the exact tag first, then optionally move a floating major tag as a separate final step:

```yaml
- name: Compute next version
  id: bump
  uses: faisal-memon/pr-label-semver@v0
  with:
    tag-prefix: api-v
    github-token: ${{ github.token }}

- name: Build and push image
  uses: docker/build-push-action@v7
  with:
    context: .
    push: true
    tags: ghcr.io/${{ github.repository_owner }}/rag-agent-api:${{ steps.bump.outputs.new-tag }}

- name: Create exact GitHub release
  uses: softprops/action-gh-release@v3
  with:
    tag_name: ${{ steps.bump.outputs.new-tag }}
    generate_release_notes: true

# Optional and separate: this moves api-v0 to the exact release commit.
- name: Move floating major tag
  run: |
    git tag -f api-v0 ${{ steps.bump.outputs.new-tag }}
    git push --force origin refs/tags/api-v0
```

The exact release is valid if the optional floating-tag step fails. The operations are intentionally separate because GitHub does not provide a transaction covering the release and floating tag.

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `github-token` | `""` | Token used to query PR labels. Required when `version-bump` is empty (or provide `GITHUB_TOKEN` env). |
| `tag-prefix` | `v` | Prefix to apply to tags (for example `v1.2.3`). |
| `version-bump` | `""` | Explicit bump override: `major`, `minor`, or `patch`. Useful for `workflow_dispatch` or manual override. |

## Outputs

| Output | Description |
| --- | --- |
| `new-tag` | Computed next tag (for example `v1.4.2`). |
| `major-tag` | Computed floating major tag (for example `v1`). |
| `previous-tag` | Latest existing tag used as the bump source. |
| `version-bump-used` | Resolved bump type actually applied. |

## How it works

The version always follows `major`.`minor`.`patch` format. Each time this action is triggered:

- Fetches the latest semantic-version tag matching the prefix (`vX.Y.Z`). If none exist, starts from `v0.0.0`
- If `version-bump` is provided, it is used directly
- Otherwise, the action checks labels (`semver:major`, `semver:minor`, `semver:patch`) on the PR associated with the commit
- If no matching label is found, it defaults to `patch`
- Selected part of tag is bumped
