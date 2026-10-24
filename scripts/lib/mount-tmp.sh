# mount-tmp.sh — a temp folder a container can bind-mount.
#
# Docker on Colima shares only $HOME with its VM: a folder in /tmp or
# /var/folders mounts as an empty folder, with no error. And macOS mktemp
# ignores TMPDIR unless it is given a template. So every temp folder that ends
# up behind `-v` comes from here, under $AI_UI_TMP (the Makefile sets it).
#
#   . "$(dirname "${BASH_SOURCE[0]}")/lib/mount-tmp.sh"
#   WORK="$(mount_tmp sign-sprigs)"; trap 'rm -rf "$WORK"' EXIT

mount_tmp() {
  local root="${AI_UI_TMP:-$HOME/.cache/ai-ui/tmp}"
  mkdir -p "$root" && mktemp -d "$root/$1.XXXXXX"
}
