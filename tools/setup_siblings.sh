#!/usr/bin/env bash
# setup_siblings.sh — verify the Sage.is sibling-repo chain and establish the
# distribution.env copies. Idempotent. Safe to re-run.
#
# The Sage.is product is composed of three repos that share canonical facts
# (image tag, volume name, install command, CLI version) through an ordinary
# copy of `distribution.env` in each. This script:
#   1. Checks that all three repos are checked out as siblings of one another.
#   2. If any are missing, prints the exact `git clone` command and exits 1.
#   3. If all three are present, calls `make distribution_sync` to publish this
#      repo's copy to the other two.
#
# Run once on a fresh machine, and again after cloning a sibling.
#
# Same script lives in all three repos. The sibling list is identical.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
PARENT=$(cd "${REPO_ROOT}/.." && pwd)

# name | https URL | ssh URL
SIBLINGS=(
  "homebrew-apps|https://github.com/Sage-is/homebrew-apps.git|git@github.com:Sage-is/homebrew-apps.git"
  "WEB-AI--Sage-is-AI-UI|https://github.com/Sage-is/WEB-AI--Sage-is-AI-UI.git|git@github.com:Sage-is/WEB-AI--Sage-is-AI-UI.git"
  "WEB-Sage.Education-docs|https://github.com/Sage-is/WEB-Sage.Education-docs.git|git@github.com:Sage-is/WEB-Sage.Education-docs.git"
)

missing=0
for entry in "${SIBLINGS[@]}"; do
  IFS='|' read -r name https ssh <<<"$entry"
  if [ ! -d "${PARENT}/${name}" ]; then
    echo "MISSING: ${PARENT}/${name}"
    echo "  Clone with one of:"
    echo "    git -C ${PARENT} clone ${https}"
    echo "    git -C ${PARENT} clone ${ssh}"
    echo ""
    missing=1
  else
    echo "OK:      ${PARENT}/${name}"
  fi
done

if [ "$missing" = "1" ]; then
  echo "Clone the missing sibling(s) above, then re-run 'make setup_siblings'."
  exit 1
fi

echo ""
echo "All siblings present. Publishing distribution.env via distribution_sync..."
make -C "$REPO_ROOT" distribution_sync
