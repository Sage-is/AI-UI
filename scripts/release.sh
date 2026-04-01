#!/bin/bash
# git-release — Full git-flow release workflow with optional interactive mode.
# Works with any project that has standard Makefile targets:
#   patch_release, minor_release, major_release, hotfix, custom_release,
#   release_finish, hotfix_finish
#
# Usage:
#   git-release                   # interactive — prompts for type
#   git-release patch             # non-interactive patch release
#   git-release major             # non-interactive major release
#   git-release minor             # non-interactive minor release
#   git-release custom 2.1.0     # non-interactive custom version
#   git-release -i patch          # interactive with pauses between steps
#
set -euo pipefail

INTERACTIVE=false
TYPE=""
VER=""

# Parse flags
while [[ $# -gt 0 ]]; do
	case "$1" in
		-i|--interactive) INTERACTIVE=true; shift ;;
		patch|minor|major|hotfix) TYPE="$1"; shift ;;
		custom)
			TYPE="custom"
			VER="${2:-}"
			if [ -z "$VER" ]; then
				echo "Error: custom release requires a version (e.g. git-release custom 2.1.0)"
				exit 1
			fi
			shift 2
			;;
		-h|--help)
			echo "Usage: $0 [-i] <patch|minor|major|hotfix|custom VERSION>"
			echo ""
			echo "  -i, --interactive   Pause between steps for review"
			echo "  patch               Bump patch version (X.Y.Z+1)"
			echo "  minor               Bump minor version (X.Y+1.0)"
			echo "  major               Bump major version (X+1.0.0)"
			echo "  hotfix              Start hotfix"
			echo "  custom VERSION      Release specific version"
			echo ""
			echo "Without arguments, prompts interactively."
			exit 0
			;;
		*) echo "Unknown argument: $1"; exit 1 ;;
	esac
done

# Check we're in a git repo with a Makefile
if [ ! -f Makefile ]; then
	echo "Error: no Makefile in current directory"
	exit 1
fi

pause() {
	if $INTERACTIVE; then
		echo ""
		read -r -p "Press Enter to continue (or Ctrl+C to abort)... "
		echo ""
	fi
}

# Helper: run a make target only if it exists
has_target() {
	make -n "$1" >/dev/null 2>&1
}

# If no type given, prompt
if [ -z "$TYPE" ]; then
	INTERACTIVE=true
	echo "========================================="
	echo "  Release Flow"
	echo "========================================="
	echo ""
	has_target show-version && make show-version && echo ""
	has_target check-upstream && make check-upstream && echo ""
	echo "Release type:"
	echo "  1) patch   — bump X.Y.Z+1"
	echo "  2) minor   — bump X.Y+1.0"
	echo "  3) major   — bump X+1.0.0"
	echo "  4) hotfix  — hotfix from master"
	echo "  5) custom  — specify exact version"
	echo ""
	read -r -p "Choose [1-5]: " choice
	case "$choice" in
		1) TYPE="patch" ;;
		2) TYPE="minor" ;;
		3) TYPE="major" ;;
		4) TYPE="hotfix" ;;
		5)
			TYPE="custom"
			read -r -p "Version (e.g. 2.1.0): " VER
			if [ -z "$VER" ]; then echo "Error: version required"; exit 1; fi
			;;
		*) echo "Invalid choice"; exit 1 ;;
	esac
fi

# Build the make target
case "$TYPE" in
	patch)   START_TARGET="patch_release";  FINISH_TARGET="release_finish" ;;
	minor)   START_TARGET="minor_release";  FINISH_TARGET="release_finish" ;;
	major)   START_TARGET="major_release";  FINISH_TARGET="release_finish" ;;
	hotfix)  START_TARGET="hotfix";         FINISH_TARGET="hotfix_finish" ;;
	custom)  START_TARGET="custom_release"; FINISH_TARGET="release_finish" ;;
esac

# Step 1: Start
echo ""
echo ">>> Step 1: make $START_TARGET"
echo ""
if [ "$TYPE" = "custom" ]; then
	make "$START_TARGET" VER="$VER"
else
	make "$START_TARGET"
fi

pause

# Step 2: Review (interactive only)
if $INTERACTIVE; then
	echo ">>> Review: check the changes before finishing"
	echo ""
	git log --oneline -3
	echo ""
	git diff --stat HEAD~1
	pause
fi

# Step 3: Finish
echo ""
echo ">>> Step 2: make $FINISH_TARGET"
echo ""
make "$FINISH_TARGET"

echo ""
echo ">>> Done! Release complete."
echo ""
has_target show-version && make show-version
