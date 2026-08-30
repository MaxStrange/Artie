#!/usr/bin/env bash
#
# One-time migration: split this monorepo into the separate component repositories.
#
# Each component is extracted with `git filter-repo`, preserving the history of its
# files. That history reaches back through two earlier restructures, so each component
# lists the paths its files lived at before those moves as well as their current ones:
#
#   55b9c8b (2025-11-26) "Move folders around"  - everything moved under framework/ and
#                                                 artie-common/ from the repository root
#   b16acd9 (2026-01-14) "WIP: Refactor repo structure"
#                                               - framework/libraries and
#                                                 framework/misc-micro-services became
#                                                 framework/ardk/*, and the firmware
#                                                 libraries moved out of artie-common
#
# Task-definition history begins at the commit that federated them; the substantial
# history (libraries, services, base image, firmware, charts) reaches back to 2022-2023.
#
# By default this only writes to $WORKSPACE: it sets each repository's 'origin' remote
# but does NOT push. Pushing is opt-in with --push, because it publishes.
#
# IMPORTANT: this is a one-time migration. filter-repo rewrites history, so every run
# produces a fresh history with different commit ids, unrelated to any previous run. A
# plain --push therefore fails once the component repositories have been published, and
# re-publishing means discarding what is already there (--force-push).
#
# Once the components are published, change them in their own repositories. Re-running
# this script is only appropriate while the split is still being shaken out and nobody
# has pulled the results.
#
# Usage:
#   ./split-repos.sh [workspace-directory] [--push | --force-push]
#
# Examples:
#   ./split-repos.sh                      # extract into ~/artie-workspace, no push
#   ./split-repos.sh ~/tmp/ws             # extract elsewhere, no push
#   ./split-repos.sh ~/artie-workspace --push
#   ./split-repos.sh ~/artie-workspace --force-push   # discards published history
#
set -euo pipefail

WORKSPACE="$HOME/artie-workspace"
PUSH=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --push)       PUSH=1 ;;
    --force-push) PUSH=1; FORCE=1 ;;
    *)            WORKSPACE="$arg" ;;
  esac
done

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRANCH="$(git -C "$SRC" rev-parse --abbrev-ref HEAD)"

# The GitHub organisation the component repositories live in. Keep in sync with
# GITHUB_ORG in artietool/workspace.py.
ORG="https://github.com/ArtieBots"

command -v git-filter-repo >/dev/null 2>&1 || {
  echo "git-filter-repo is required: pip install git-filter-repo" >&2
  exit 1
}

mkdir -p "$WORKSPACE"

extract() {
  local name="$1"; shift
  local dest="${WORKSPACE:?}/$name"
  echo "==> $name"
  # Clear any previous extraction. On Windows a directory can be un-removable while
  # something still holds a handle on it, even when it is otherwise idle, so fall back to
  # emptying it in place - git clone is happy to write into an existing empty directory.
  if ! rm -rf "$dest" 2>/dev/null; then
    find "$dest" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
  fi
  git clone -q --no-local "$SRC" "$dest" --branch "$BRANCH"
  # On Git Bash, MSYS rewrites arguments that look like paths, which mangles the
  # 'old:new' form of --path-rename. Disable it for this call only - setting it for the
  # whole script would stop git clone above from seeing a usable source path.
  ( cd "$dest" && MSYS2_ARG_CONV_EXCL="*" git-filter-repo --force "$@" >/dev/null )
  echo "    $(git -C "$dest" rev-list --count HEAD) commits, back to $(git -C "$dest" log --format=%ad --date=short | tail -1)"
}

extract ArDK \
  --path framework/ardk/ --path framework/libraries/ --path framework/misc-micro-services/ \
  --path libraries/ --path misc-micro-services/ \
  --path artie-common/firmware/libraries/ --path firmware/libraries/ \
  --path framework/artietool/deploy-files/artie-base/ --path artietool/deploy-files/artie-base/ \
  --path docs/specifications/ --path docs/sdk/ --path docs/contributing/library-contributions.md \
  --path-rename 'framework/ardk/:' \
  --path-rename 'framework/libraries/:libraries/' \
  --path-rename 'framework/misc-micro-services/:services/' \
  --path-rename 'misc-micro-services/:services/' \
  --path-rename 'artie-common/firmware/libraries/:firmware/libraries/' \
  --path-rename 'framework/artietool/deploy-files/artie-base/:deploy/artie-base/' \
  --path-rename 'artietool/deploy-files/artie-base/:deploy/artie-base/' \
  --path-rename 'docs/sdk/:docs/specifications/'

# The artietool package keeps its own directory so that it stays importable as
# `artietool`, but the task definitions have to sit at the repository root, because that
# is where Artie Tool looks for every component's tasks. The more specific rename has to
# come first - filter-repo applies the first one that matches.
extract ArtieTool \
  --path framework/artietool/ --path framework/artie-tool.py --path framework/pyproject.toml \
  --path framework/requirements.txt --path artietool/ --path artie-tool.py --path requirements.txt \
  --path docs/contributing/artie-tool-contributions.md \
  --path docs/contributing/chart-contributions.md \
  --path docs/contributing/release-process.md \
  --path-rename 'framework/artietool/.artie/:.artie/' \
  --path-rename 'framework/artietool/VERSION:VERSION' \
  --path-rename 'framework/artietool/:artietool/' \
  --path-rename 'framework/artie-tool.py:artie-tool.py' \
  --path-rename 'framework/pyproject.toml:pyproject.toml' \
  --path-rename 'framework/requirements.txt:requirements.txt'

extract ArtieCLI \
  --path framework/cli/ --path cli/ --path docs/contributing/artie-cli-contributions.md \
  --path-rename 'framework/cli/:' --path-rename 'cli/:'

extract ArtieWorkbench \
  --path framework/workbench/ --path docs/contributing/artie-workbench-contributions.md \
  --path-rename 'framework/workbench/:'

extract ArtieDaemons \
  --path framework/daemons/ --path artie-admind/ --path artie-computed/ \
  --path docs/out-of-the-box/admin-server.md --path docs/out-of-the-box/compute-server.md \
  --path-rename 'framework/daemons/:'

extract Artie00 \
  --path artie00/ \
  --path artie-common/drivers/ --path artie-common/firmware/ --path artie-common/electrical-schematics/ \
  --path drivers/ --path firmware/ --path electrical-schematics/ \
  --path framework/artietool/deploy-files/artie00/ --path artietool/deploy-files/artie00/ \
  --path docs/contributing/firmware-contributions.md --path docs/contributing/driver-contributions.md \
  --path docs/contributing/electronic-design.md --path docs/contributing/mechanical-design.md \
  --path-rename 'artie00/:' \
  --path-rename 'artie-common/drivers/:drivers/' \
  --path-rename 'artie-common/firmware/:firmware/' \
  --path-rename 'artie-common/electrical-schematics/:electrical-schematics/' \
  --path-rename 'framework/artietool/deploy-files/artie00/:deploy/artie00/' \
  --path-rename 'artietool/deploy-files/artie00/:deploy/artie00/'

# Licences. Artie Workbench keeps its own LGPL 'License' file; everything else is MIT,
# and Artie00 additionally carries the hardware licence for its schematics.
for r in ArDK ArtieTool ArtieCLI ArtieDaemons Artie00; do
  cp "$SRC/LICENSE" "$WORKSPACE/$r/LICENSE"
done
cp "$SRC/HW-LICENSE" "$WORKSPACE/Artie00/HW-LICENSE"

# A README describing the component and pointing back at the documentation hub.
python "$SRC/split-repos-readmes.py" "$WORKSPACE"

REPOS="ArDK ArtieTool ArtieCLI ArtieWorkbench ArtieDaemons Artie00"

# The branch the component repositories publish. The extraction inherits whatever branch
# this monorepo is on, which is a migration branch; in a standalone repository the
# content belongs on the default branch.
PUBLISH_BRANCH=main

for r in $REPOS; do
  cd "$WORKSPACE/$r"
  git add -A
  git commit -q -m "Add README and licence for the standalone repository

Split out of the Artie monorepo with history preserved." || true
  git branch -M "$PUBLISH_BRANCH"
  git remote remove origin 2>/dev/null || true
  git remote add origin "$ORG/$r.git"
done

echo
echo "Extracted into $WORKSPACE"
for r in $REPOS; do
  printf '  %-16s %4s commits  ->  %s\n' "$r" "$(git -C "$WORKSPACE/$r" rev-list --count HEAD)" "$ORG/$r.git"
done

if [ "$PUSH" -eq 1 ]; then
  echo
  if [ "$FORCE" -eq 1 ]; then
    echo "Force-pushing $PUBLISH_BRANCH to each origin - this DISCARDS the published history."
  else
    echo "Pushing $PUBLISH_BRANCH to each origin..."
  fi
  for r in $REPOS; do
    echo "  $r"
    if [ "$FORCE" -eq 1 ]; then
      # --force-with-lease needs a remote-tracking ref to compare against, and these are
      # fresh extractions that have never fetched. Fetch first so the lease still guards
      # against someone else pushing while this run is in progress.
      git -C "$WORKSPACE/$r" fetch -q origin "$PUBLISH_BRANCH" 2>/dev/null || true
      git -C "$WORKSPACE/$r" push --force-with-lease -u origin "$PUBLISH_BRANCH"
    else
      git -C "$WORKSPACE/$r" push -u origin "$PUBLISH_BRANCH"
    fi
  done
  echo "Done."
else
  echo
  echo "Remotes are set but nothing was pushed. Re-run with --push to publish."
fi
