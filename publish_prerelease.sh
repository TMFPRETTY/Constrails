#!/usr/bin/env bash
set -euo pipefail

TAG="v0.1.0-alpha"
TITLE="Constrails 0.1.0-alpha"
NOTES_FILE=".github/release-notes/0.1.0-alpha.md"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install GitHub CLI first: https://cli.github.com/"
  exit 1
fi

gh release view "$TAG" >/dev/null 2>&1 && \
  gh release edit "$TAG" --title "$TITLE" --notes-file "$NOTES_FILE" --prerelease || \
  gh release create "$TAG" --title "$TITLE" --notes-file "$NOTES_FILE" --prerelease

echo "Pre-release published/refreshed for $TAG"
