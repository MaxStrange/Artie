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
# This script only writes to $WORKSPACE. It does not create anything on GitHub and does
# not push. Adding remotes and pushing is a deliberate, separate step - see the end.
#
# Usage:
#   ./split-repos.sh [workspace-directory]      # defaults to ~/artie-workspace
#
set -euo pipefail

WORKSPACE="${1:-$HOME/artie-workspace}"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRANCH="$(git -C "$SRC" rev-parse --abbrev-ref HEAD)"

command -v git-filter-repo >/dev/null 2>&1 || {
  echo "git-filter-repo is required: pip install git-filter-repo" >&2
  exit 1
}

mkdir -p "$WORKSPACE"

extract() {
  local name="$1"; shift
  echo "==> $name"
  rm -rf "${WORKSPACE:?}/$name"
  git clone -q --no-local "$SRC" "$WORKSPACE/$name" --branch "$BRANCH"
  # On Git Bash, MSYS rewrites arguments that look like paths, which mangles the
  # 'old:new' form of --path-rename. Disable it for this call only - setting it for the
  # whole script would stop git clone above from seeing a usable source path.
  ( cd "$WORKSPACE/$name" && MSYS2_ARG_CONV_EXCL='*' git-filter-repo --force "$@" >/dev/null )
  echo "    $(git -C "$WORKSPACE/$name" rev-list --count HEAD) commits, back to $(git -C "$WORKSPACE/$name" log --format=%ad --date=short | tail -1)"
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

echo
echo "Extracted into $WORKSPACE"
echo
echo "Next, to verify before publishing anything:"
echo "  cat > ~/.artie/config.yaml <<'EOF'"
echo "  workspace: $WORKSPACE"
echo "  repos:"
for r in ardk:ArDK artietool:ArtieTool artiecli:ArtieCLI artieworkbench:ArtieWorkbench artiedaemons:ArtieDaemons artie00:Artie00; do
  echo "    ${r%%:*}: { path: $WORKSPACE/${r##*:} }"
done
echo "  EOF"
echo "  cd $WORKSPACE/ArtieTool && python artie-tool.py build all"
echo
echo "Publishing is deliberately not automated. For each repository, create it on"
echo "GitHub, then: git remote add origin <url> && git push -u origin <branch>"
