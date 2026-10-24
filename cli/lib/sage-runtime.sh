# shellcheck shell=bash
# sage-runtime.sh: the runtime code sage-runtime and trellis-crm source from
# lib/ beside them. AI-UI keeps a copy in cli/lib/ for ai-ui, refreshed by its
# make runtime_sync, and a drift test fails while the two differ. Edit it only
# here, in the homebrew-apps tap, then run that sync.
#
# Source it under bash 3.2 with set -euo pipefail. Sourcing defines constants
# and functions and, on a Mac, unsets the variables that would turn docker or
# Colima elsewhere; it runs nothing else. Call trap_cleanup before a copy or a
# conversion. The commands stay in each tool. Messages send people to
# sage-runtime's use and convert; a tool with its own sets USE_COMMAND and
# CONVERT_COMMAND after sourcing.

SAGE_CONFIG_DIR="${HOME}/.sage-is"
# The commands messages send people to; convert acts with --yes.
USE_COMMAND="sage-runtime use"
CONVERT_COMMAND="sage-runtime convert"
RUNTIME_FILE="${SAGE_CONFIG_DIR}/runtime"
RUNTIMES="colima docker-desktop orbstack"
APPLICATIONS_DIR="${APPLICATIONS_DIR:-/Applications}"
DOCKER_CONFIG_FILE="${DOCKER_CONFIG:-$HOME/.docker}/config.json"
# Docker Desktop's own settings, written at its first start.
DESKTOP_SETTINGS="$HOME/Library/Group Containers/group.com.docker/settings-store.json"
DOCKER_PLUGINS="${DOCKER_CONFIG:-$HOME/.docker}/cli-plugins"
# Where Docker Desktop links its socket and its tools for the whole Mac.
SYSTEM_SOCKET="${SYSTEM_SOCKET:-/var/run/docker.sock}"
SYSTEM_BIN="${SYSTEM_BIN:-/usr/local/bin}"
COPY_IMAGE="alpine:3"
# Folders both runtimes mount (the Sprig registry, backups, caches). Two VMs
# never share file locks, so two runtimes writing here at once lose data with
# no error (measured 2026-10-06). One runtime uses it at a time.
SAGE_DATA="${SAGE_DATA:-$HOME/SageData}"
# Copies pass through a file here, under $HOME, which every runtime mounts. A
# stream from one daemon straight into another stalled for good at 2.86 GB on
# 2026-10-08: Colima's socket runs through Lima's port forward. With a file,
# each side finishes or fails on its own. One copy at a time; each file goes
# when its copy ends. Only this user may open the folder: a staged file is a
# whole volume or image, and another account on the Mac can read ~.
STAGE_DIR="${SAGE_CONFIG_DIR}/staging"
# One line per verified copy: the volume, from, to, and the source's files and
# folders and KiB. A copy drops its line before it touches the target and
# writes it once the counts match, so a copy that stopped halfway has none.
MIGRATED_FILE="${SAGE_CONFIG_DIR}/migrated"
# What a conversion to krunkit must keep across the vz VM's delete: its size,
# mounts and contents. It stays while a rerun has the conversion to finish.
CONVERT_FILE="${SAGE_CONFIG_DIR}/convert"
BUILD_PROFILE="build"
# Lima reads its override file from the Lima home Colima 0.10.3 gives it
# (config/files.go): $LIMA_HOME, else _lima in Colima's home. That home is
# $COLIMA_HOME, else ~/.colima, or $XDG_CONFIG_HOME/colima while ~/.colima is
# missing. Colima skips a $COLIMA_HOME that does not exist yet;
# fix_lima_override creates it. The VMs' disks live in _disks there.
_colima_home="$HOME/.colima"
if [[ ! -e "$_colima_home" && -n "${XDG_CONFIG_HOME:-}" ]]; then _colima_home="$XDG_CONFIG_HOME/colima"; fi
LIMA_DIR="${LIMA_HOME:-${COLIMA_HOME:-$_colima_home}/_lima}"
LIMA_OVERRIDE="$LIMA_DIR/_config/override.yaml"
# The everyday VM's Colima settings, which colima delete removes with the VM.
COLIMA_SETTINGS="${COLIMA_HOME:-$_colima_home}/default/colima.yaml"
# krunkit comes from a tap, and Homebrew 7 loads a tap's formulae only once the
# tap is trusted. Trust the whole tap: krunkit's dependencies come from it too.
KRUNKIT_INSTALL="brew tap libkrun/krun && brew trust libkrun/krun && brew install krunkit"
# An engine answers docker info or ps in a second or two. A half-started one
# held a call open for ten minutes on 2026-10-08, so a question gets this many
# seconds, and a runtime that is starting gets SAGE_RUNTIME_WAIT in all.
ANSWER_SECONDS=10
START_WAIT="${SAGE_RUNTIME_WAIT:-180}"
# This tool reads, restores and sets docker's saved context, the one new shells
# and apps use, and names a context on every engine call. An exported
# DOCKER_CONTEXT or DOCKER_HOST would stand in for the saved one, here and in
# the docker commands Colima runs as it starts and stops a VM. An exported
# COLIMA_PROFILE would turn Colima's bare start, stop and list to another VM.
# On Linux docker runs the engine its own settings name, such as a rootless one.
if [[ "$OSTYPE" == darwin* ]]; then unset DOCKER_CONTEXT DOCKER_HOST COLIMA_PROFILE; fi

die() {
  echo "Error: $*" >&2
  exit 1
}

# --- the runtimes -------------------------------------------------------------

# The docker context each runtime creates for itself.
runtime_context() {
  case "$1" in
    colima)         echo colima ;;
    docker-desktop) echo desktop-linux ;;
    orbstack)       echo orbstack ;;
  esac
}

check_runtime() {
  [[ -n "$(runtime_context "${1:-}")" ]] || die "unknown runtime '${1:-}'. Use one of: $RUNTIMES"
}

runtime_installed() {
  case "$1" in
    colima)         command -v colima &>/dev/null ;;
    docker-desktop) [[ -d "$APPLICATIONS_DIR/Docker.app" ]] ;;
    orbstack)       [[ -d "$APPLICATIONS_DIR/OrbStack.app" ]] ;;
  esac
}

runtime_install_command() {
  case "$1" in
    colima)         echo "brew install colima docker docker-buildx docker-credential-helper" ;;
    docker-desktop) echo "brew install --cask docker-desktop" ;;
    orbstack)       echo "brew install --cask orbstack" ;;
  esac
}

# PID $1's children, theirs, and so on, deepest first.
descendants() {
  local child
  for child in $(pgrep -P "$1"); do
    descendants "$child"
    echo "$child"
  done
}

# Runs a question for an engine, such as docker info, for at most
# ANSWER_SECONDS: a stock Mac has no timeout(1). Time up, its children go
# too: colima ssh runs limactl shell, which runs ssh, and each holds the
# output a $(...) waits on. Called off, the watcher stops its own sleep, so
# nothing outlives the answer.
briefly() {
  local pid watcher status=0
  "$@" &
  pid=$!
  (
    nap=""
    trap 'kill "$nap" 2>/dev/null; exit 0' TERM
    sleep "$ANSWER_SECONDS" &
    nap=$!
    # shellcheck disable=SC2046 # one PID a word
    wait "$nap" && kill $(descendants "$pid") "$pid"
  ) >/dev/null 2>&1 &
  watcher=$!
  wait "$pid" || status=$?
  kill "$watcher" 2>/dev/null || true
  return "$status"
}

# Whether RUNTIME's engine answers.
runtime_running() {
  briefly docker --context "$(runtime_context "$1")" info &>/dev/null
}

# Colima's VMs, one per line: the name, then its state (Running, Stopped).
colima_vms() {
  colima list --json 2>/dev/null | sed -n 's/.*"name":"\([^"]*\)","status":"\([^"]*\)".*/\1 \2/p' || true
}

# What Colima says of VM $1 (default if none); nothing when there is no such VM.
colima_state() {
  colima_vms | awk -v name="${1:-default}" '$1 == name {print $2}'
}

colima_exists() {
  [[ -n "$(colima_state "${1:-}")" ]]
}

# The CPUs, memory and disk (in bytes) Colima lists for VM $1, running or not.
colima_size() {
  colima list --json 2>/dev/null \
    | sed -n "s/^{\"name\":\"$1\",.*\"cpus\":\([0-9][0-9]*\),\"memory\":\([0-9][0-9]*\),\"disk\":\([0-9][0-9]*\).*/\1 \2 \3/p" || true
}

# Whether RUNTIME's VM or app is up, asked of Colima or macOS rather than of
# the engine: an engine that does not answer may still run containers. orb
# start runs OrbStack's engine with its app closed, so an engine that answers
# counts too. The build VM counts here by its context, so the $SAGE_DATA
# guard covers it.
runtime_up() {
  case "$1" in
    colima)         [[ "$(colima_state)" == Running ]] ;;
    docker-desktop) [[ "$(osascript -e 'application "Docker" is running' 2>/dev/null)" == true ]] ;;
    orbstack)       [[ "$(osascript -e 'application "OrbStack" is running' 2>/dev/null)" == true ]] \
                      || runtime_running orbstack ;;
    "colima-$BUILD_PROFILE") [[ "$(colima_state "$BUILD_PROFILE")" == Running ]] ;;
  esac
}

installed_runtimes() {
  local rt
  for rt in $RUNTIMES; do
    if runtime_installed "$rt"; then echo "$rt"; fi
  done
}

# The runtime in use: the saved choice, else the one docker's context names.
current_runtime() {
  if [[ -f "$RUNTIME_FILE" ]]; then
    cat "$RUNTIME_FILE"
    return
  fi
  case "$(docker context show 2>/dev/null)" in
    desktop-linux) echo docker-desktop ;;
    orbstack)      echo orbstack ;;
    *)             echo colima ;;
  esac
}

clamp() {
  local value="$1" low="$2" high="$3"
  if (( value < low )); then value=$low; fi
  if (( value > high )); then value=$high; fi
  echo "$value"
}

# Lima's boot step for a krunkit VM's data disk: mount each Lima disk by its
# label before Colima binds /var/lib/docker from it. A vz VM has its disk
# mounted already, so the step passes it by.
data_disk_step() {
  cat <<'EOF'
  - mode: dependency
    script: |
      #!/bin/sh
      for link in /dev/disk/by-label/lima-*; do
        [ -e "$link" ] || continue
        dir="/mnt/${link##*/}"
        mountpoint -q "$dir" || { mkdir -p "$dir" && mount "$link" "$dir"; }
      done
EOF
}

# Appends stdin to Lima's override file. A file that ends mid-line would
# swallow the first new line into its last.
append_override() {
  if [[ -s "$LIMA_OVERRIDE" && -n "$(tail -c 1 "$LIMA_OVERRIDE")" ]]; then echo >> "$LIMA_OVERRIDE"; fi
  cat >> "$LIMA_OVERRIDE"
}

# Lima's override file mends two krunkit faults for every Colima VM, and keeps
# whatever else it held. Colima 0.10.3 hands Lima 9p for a krunkit VM, and Lima
# 2.2 refuses it (abiosoft/colima#1607): mountType forces virtiofs, which vz
# uses already and a QEMU VM cannot. krunkit puts the data disk on vdc, where
# Lima looks for vdb, so after the VM's first boot the disk stays unmounted and
# Docker starts afresh on the 20 GiB root disk (abiosoft/colima#1614): the boot
# step mounts it. A file with its own provision list gets no second one, which
# YAML would refuse; the step is printed to add by hand. Drop each part once
# Colima ships its fix.
fix_lima_override() {
  mkdir -p "$(dirname "$LIMA_OVERRIDE")"
  if ! grep -q '^mountType:' "$LIMA_OVERRIDE" 2>/dev/null; then
    printf '%s\n' "# Colima 0.10.3 hands Lima 9p for krunkit, and Lima 2.2 refuses it: abiosoft/colima#1607" \
      "mountType: virtiofs" | append_override
    echo "Added \"mountType: virtiofs\" to $LIMA_OVERRIDE (abiosoft/colima#1607). A QEMU Colima profile will not start while that line is there."
  fi
  grep -qF '/dev/disk/by-label/lima-' "$LIMA_OVERRIDE" && return 0
  if grep -q '^provision:' "$LIMA_OVERRIDE"; then
    echo "Warning: $LIMA_OVERRIDE has its own provision list. Add this step to it, or Docker in a krunkit VM moves to the root disk after a restart (abiosoft/colima#1614):" >&2
    data_disk_step >&2
    return 0
  fi
  {
    echo "# krunkit puts the data disk on vdc, where Lima 2.2 looks for vdb; mount it by label: abiosoft/colima#1614"
    echo "provision:"
    data_disk_step
  } | append_override
  echo "Added a boot step to $LIMA_OVERRIDE that mounts the VM's data disk (abiosoft/colima#1614)."
}

# Whether Lima's override file holds both of fix_lima_override's mends.
override_ready() {
  grep -q '^mountType: virtiofs' "$LIMA_OVERRIDE" 2>/dev/null && grep -qF '/dev/disk/by-label/lima-' "$LIMA_OVERRIDE"
}

# Whether the everyday Colima VM is a krunkit one, as Lima's file for it says.
krunkit_vm() {
  grep -q '^vmType: krunkit' "$LIMA_DIR/colima/lima.yaml" 2>/dev/null
}

# The everyday Colima VM's type (vz, krunkit or qemu), as Lima's file for it says.
vm_type() {
  sed -n 's/^vmType: *//p' "$LIMA_DIR/colima/lima.yaml" 2>/dev/null || true
}

# krunkit runs only on Apple Silicon.
krunkit_ready() {
  [[ "$(uname -m)" == arm64 ]] && command -v krunkit &>/dev/null
}

# Where Docker in the everyday Colima VM keeps its data, as the VM itself
# says: data (a disk of its own), root (a folder of the root disk, mounted
# over), or none (no mount of its own, on a VM made before Colima had a data
# disk). Nothing when the VM gives no answer.
docker_disk() {
  # shellcheck disable=SC2016 # the VM's shell expands them
  briefly colima ssh --profile default -- sh -c \
    'r="$(findmnt -no SOURCE /)" || exit 1; d="$(findmnt -no SOURCE /var/lib/docker)" || { echo none; exit 0; }; [ "${d%%\[*}" = "$r" ] && echo root || echo data' \
    < /dev/null 2>/dev/null || true
}

# Where Docker in the everyday Colima VM keeps data that a krunkit VM made on
# the same data disk would not find: its root folder when that is not
# /var/lib/docker (a data-root in the VM's Colima settings, which a new VM
# lacks), else whichever of /var/lib/docker and /var/lib/containerd (images,
# in Docker 29's containerd store) is on the root disk. data when none is;
# nothing when the VM gives no answer. findmnt -T names the disk that holds
# a folder, whether or not it is a mount of its own. One line, as docker_disk
# sends it.
# shellcheck disable=SC2016 # the VM's shell expands them
docker_data_disk() {
  local probe
  probe='r="$(findmnt -no SOURCE /)" && d="$(docker info --format "{{.DockerRootDir}}")" || exit 1;'
  probe+=' [ "$d" = /var/lib/docker ] || { echo "$d"; exit 0; };'
  probe+=' for p in /var/lib/docker /var/lib/containerd; do s="$(findmnt -no SOURCE -T "$p")" || exit 1;'
  probe+=' [ "${s%%\[*}" != "$r" ] || { echo "$p"; exit 0; }; done; echo data'
  briefly colima ssh --profile default -- sh -c "$probe" < /dev/null 2>/dev/null || true
}

# Colima binds /var/lib/docker from the VM's data disk, which a krunkit VM
# leaves unmounted after its first boot (see fix_lima_override). Docker then
# starts afresh on the root disk, without the images and volumes the data disk
# holds, and whatever is copied there drops out of sight once the disk is
# mounted again. So nothing goes on while Docker is there. A VM with no data
# disk, made before Colima had one, keeps Docker on its root disk by design:
# its /var/lib/docker is no mount of its own. A question that gets no answer
# only warns: it is no sign of the fault.
check_data_disk() {
  case "$(docker_disk)" in
    data|none) return 0 ;;
    root) ;;
    *)    echo "Warning: could not ask the colima VM which disk Docker uses. Check: colima ssh -- findmnt /var/lib/docker" >&2
          return 0 ;;
  esac
  if krunkit_vm; then fix_lima_override; fi
  die "Docker in the colima VM runs on the VM's root disk, not its data disk, so it lacks the images and volumes Colima keeps (abiosoft/colima#1614). Restart Colima to mount the data disk, then run this again: colima restart"
}

# Sets VM_TYPE, VM_SIZE and VM_FLAGS (what colima start needs) for a new VM
# named $1, sized for this Mac. Image builds need more than Colima's 2 GiB:
# AI-UI's Vite build alone takes a 4 GiB heap. krunkit (libkrun), the default
# on Apple Silicon, hands the pages a VM frees back to macOS, so the VM may
# take half the Mac's memory (4 to 12 GiB); it also passes the GPU through as
# Vulkan. vz keeps memory it has touched until it stops, so it gets a third (4
# to 8). The build VM is vz with Rosetta, stopped after its builds: a third, 9
# to 12, since AI-UI's multi-arch release wants 8 GiB in docker info and the
# VM's kernel keeps a quarter GiB of what Colima gives it. Folders in
# VM_MOUNTS (--mount PATH pairs, which convert carries across) replace Colima's
# default mount of the home folder.
plan_colima() {
  local profile="$1" arch ram_gib cores memory cpu disk
  arch="$(uname -m)"
  # sysctl lives in /usr/sbin, which a minimal PATH leaves out: the floors apply then.
  ram_gib=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 ))
  cores=$(sysctl -n hw.ncpu 2>/dev/null || echo 0)
  if [[ "$profile" == "$BUILD_PROFILE" ]]; then
    VM_TYPE=vz
    memory=$(clamp $(( ram_gib / 3 )) 9 12)
  elif krunkit_ready; then
    VM_TYPE=krunkit
    memory=$(clamp $(( ram_gib / 2 )) 4 12)
  else
    VM_TYPE=vz
    memory=$(clamp $(( ram_gib / 3 )) 4 8)
    if [[ "$arch" == arm64 ]]; then
      echo "Warning: krunkit, the default VM on Apple Silicon, is not installed, so this VM uses vz. Get it: $KRUNKIT_INSTALL"
    fi
  fi
  memory="${SAGE_RUNTIME_MEMORY:-$memory}"
  cpu="${SAGE_RUNTIME_CPU:-$(clamp $(( cores / 2 )) 2 8)}"
  disk="${SAGE_RUNTIME_DISK:-100}"
  VM_SIZE="$memory GiB memory, $cpu CPUs, $disk GiB disk"
  VM_FLAGS=(--profile "$profile" --vm-type "$VM_TYPE")
  # Colima knows --vz-rosetta only on Apple Silicon.
  if [[ "$VM_TYPE" == vz && "$arch" == arm64 ]]; then VM_FLAGS+=(--vz-rosetta); fi
  if [[ "$profile" == "$BUILD_PROFILE" ]]; then VM_FLAGS+=(--activate=false); fi
  VM_FLAGS+=(--mount-type virtiofs --mount-inotify --memory "$memory" --cpu "$cpu" --disk "$disk")
  # bash 3.2 calls an empty array unbound under set -u.
  VM_FLAGS+=(${VM_MOUNTS[@]+"${VM_MOUNTS[@]}"})
}

# Starts a new Colima VM named $1. The everyday one becomes docker's current
# context, as any Colima VM does by default; the build VM never does.
start_new_colima() {
  plan_colima "$1"
  if [[ "$VM_TYPE" == krunkit ]]; then fix_lima_override; fi
  echo "Creating the Colima VM $1 ($VM_TYPE): $VM_SIZE."
  colima start "${VM_FLAGS[@]}"
}

# A desktop app that has run before starts in the background, hidden. Its very
# first start stays in view: it shows terms or setup screens that need a click.
open_app() {
  local app="$1" set_up_marker="$2"
  if [[ -e "$set_up_marker" ]]; then
    open -g -j -a "$app"
  else
    echo "$app's first start shows its own setup screens. Sign-in is optional."
    open -a "$app"
  fi
}

# Colima and Docker Desktop each make themselves docker's current context as
# they start. Starting one for a copy or a build must not move everyday work,
# so the context goes back to $1; `use` then sets the one it means. Colima
# drops its context as its VM stops, which leaves docker on default: once the
# runtime in use has its context ($2) again, everyday work goes there.
restore_context() {
  local ctx="$1"
  if [[ "$ctx" == default ]] && docker context inspect "$2" &>/dev/null; then ctx="$2"; fi
  [[ -n "$ctx" && "$(docker context show 2>/dev/null)" != "$ctx" ]] || return 0
  docker context use "$ctx" >/dev/null 2>&1 \
    || echo "Warning: docker's context moved, and it would not go back. Run: docker context use $ctx" >&2
}

# The runtimes this command started, so a refusal can stop them again.
STARTED=""

start_engine() {
  local rt="$1" before in_use deadline
  runtime_running "$rt" && return 0
  runtime_installed "$rt" || die "$rt is not installed. Install it: $(runtime_install_command "$rt")"
  before="$(docker context show 2>/dev/null || true)"
  in_use="$(runtime_context "$(current_runtime)")"
  echo "Starting $rt..."
  case "$rt" in
    colima)
      if colima_exists; then colima start; else start_new_colima default; fi
      ;;
    docker-desktop) open_app Docker "$DESKTOP_SETTINGS" ;;
    orbstack)       open_app OrbStack "$HOME/.orbstack" ;;
  esac
  STARTED+=" $rt"
  deadline=$(( SECONDS + START_WAIT ))
  until runtime_running "$rt"; do
    if (( SECONDS >= deadline )); then
      restore_context "$before" "$in_use"
      die "$rt did not answer within $START_WAIT seconds. Finish any setup screen it shows and run this again."
    fi
    sleep 1
  done
  restore_context "$before" "$in_use"
}

# Starts RUNTIME unless its engine answers. Colima's must keep its data on the
# VM's data disk, however the VM came up.
start_runtime() {
  start_engine "$1"
  if [[ "$1" == colima ]]; then check_data_disk; fi
}

# Stops the runtimes this command started, so a refusal leaves them as they were.
stop_started() {
  local rt
  for rt in $STARTED; do stop_runtime "$rt"; done
}

stop_runtime() {
  local rt="$1"
  runtime_up "$rt" || return 0
  echo "Stopping $rt..."
  case "$rt" in
    colima)         colima stop ;;
    docker-desktop) osascript -e 'quit app "Docker"' >/dev/null ;;
    # Quitting the app leaves an engine that orb start ran without it. orb
    # lives in ~/.orbstack/bin, which OrbStack's shell setup puts on PATH.
    orbstack)
      osascript -e 'quit app "OrbStack"' >/dev/null
      if runtime_running orbstack && ! PATH="$PATH:$HOME/.orbstack/bin" orb stop >/dev/null; then
        die "OrbStack's engine still runs without its app. Stop it (orb stop), then run this again."
      fi ;;
    "colima-$BUILD_PROFILE") colima stop --profile "$BUILD_PROFILE" ;;
  esac
}

# --- docker's own config ------------------------------------------------------

# Whether docker should keep its logins with the Keychain helper itself while
# RUNTIME is in use. Docker Desktop's helper only wraps it, so the switch
# keeps every login, and Docker Desktop puts its own back when it is the
# runtime again.
keychain_serves() {
  [[ "$1" == colima ]] && command -v docker-credential-osxkeychain &>/dev/null
}

# Docker Desktop writes "credsStore": "desktop". Its helper leaves with the app,
# and then every pull and login fails with "error getting credentials". With
# Colima in use ($1, else the runtime in use now), the Keychain helper takes
# over even while Docker Desktop stays installed.
fix_credentials() {
  local store why backup
  [[ -f "$DOCKER_CONFIG_FILE" ]] || return 0
  store="$(plutil -extract credsStore raw -o - "$DOCKER_CONFIG_FILE" 2>/dev/null)" || return 0
  if ! command -v "docker-credential-$store" &>/dev/null; then
    why="$store has no helper here"
  elif [[ "$store" == desktop ]] && keychain_serves "${1:-$(current_runtime)}"; then
    why="desktop goes through Docker Desktop"
  else
    return 0
  fi
  backup="$DOCKER_CONFIG_FILE.$(date +%Y%m%d-%H%M%S).bak"
  cp "$DOCKER_CONFIG_FILE" "$backup"
  if command -v docker-credential-osxkeychain &>/dev/null; then
    plutil -replace credsStore -string osxkeychain "$DOCKER_CONFIG_FILE"
    echo "credsStore: $why; now osxkeychain (backup: $backup)"
  else
    plutil -remove credsStore "$DOCKER_CONFIG_FILE"
    echo "credsStore: removed $store, which has no helper here (backup: $backup)"
    echo "  Keep logins in the keychain: brew install docker-credential-helper"
  fi
}

# Homebrew's prefix, as the shell names it or brew gives it: /opt/homebrew on
# Apple Silicon, /usr/local on Intel. Nothing without Homebrew.
brew_prefix() {
  if [[ -n "${HOMEBREW_PREFIX:-}" ]]; then echo "$HOMEBREW_PREFIX"; else brew --prefix 2>/dev/null || true; fi
}

# Homebrew's plugin folder.
brew_plugins() {
  local prefix
  prefix="$(brew_prefix)"
  if [[ -n "$prefix" ]]; then echo "$prefix/lib/docker/cli-plugins"; fi
}

# The links in docker's plugin folder into a Docker.app that no longer holds
# their target (the app is gone, or an update dropped the plugin), each name
# after a space. docker lists each as a broken plugin. A link that resolves
# never counts, nor one that leads elsewhere, such as onto a drive not
# mounted now.
dead_plugins() {
  local link
  for link in "$DOCKER_PLUGINS"/*; do
    if [[ -L "$link" && ! -e "$link" && "$(readlink "$link")" == */Docker.app/* ]]; then printf ' %s' "${link##*/}"; fi
  done
}

# Docker Desktop's dead plugin links go. Homebrew's buildx and compose live
# outside docker's own plugin folder.
fix_plugin_dirs() {
  local name gone plugins i=0 dir
  gone="$(dead_plugins)"
  for name in $gone; do rm "$DOCKER_PLUGINS/$name"; done
  if [[ -n "$gone" ]]; then echo "cli-plugins: removed$gone, which led nowhere in Docker.app"; fi
  plugins="$(brew_plugins)"
  [[ -d "$plugins" ]] || return 0
  if [[ ! -f "$DOCKER_CONFIG_FILE" ]]; then
    # plutil reads a bare {} as an OpenStep plist, which it cannot write back.
    mkdir -p "$(dirname "$DOCKER_CONFIG_FILE")"
    echo '{"cliPluginsExtraDirs": []}' > "$DOCKER_CONFIG_FILE"
  fi
  while dir="$(plutil -extract "cliPluginsExtraDirs.$i" raw -o - "$DOCKER_CONFIG_FILE" 2>/dev/null)"; do
    [[ "$dir" == "$plugins" ]] && return 0
    i=$((i + 1))
  done
  cp "$DOCKER_CONFIG_FILE" "$DOCKER_CONFIG_FILE.$(date +%Y%m%d-%H%M%S).bak"
  if (( i == 0 )); then
    plutil -replace cliPluginsExtraDirs -json "[\"$plugins\"]" "$DOCKER_CONFIG_FILE"
  else
    plutil -insert cliPluginsExtraDirs.0 -string "$plugins" "$DOCKER_CONFIG_FILE"
  fi
  echo "cliPluginsExtraDirs: added $plugins (Homebrew's buildx and compose)"
}

# The socket each runtime's engine listens on, for tools that skip docker's
# context and go to $SYSTEM_SOCKET.
runtime_socket() {
  case "$1" in
    colima)         echo "${COLIMA_HOME:-$_colima_home}/default/docker.sock" ;;
    docker-desktop) echo "$HOME/.docker/run/docker.sock" ;;
    orbstack)       echo "$HOME/.orbstack/run/docker.sock" ;;
  esac
}

# Whether a Login Item named "Docker Desktop" opens it at login; its own
# AutoStart setting may well be off. macOS may first ask whether this
# terminal may read Login Items, so no answer in time counts as none.
desktop_login_item() {
  local items
  items="$(briefly osascript -e 'tell application "System Events" to get the name of every login item' 2>/dev/null)" \
    || return 1
  [[ ", $items, " == *", Docker Desktop, "* ]]
}

# What Docker Desktop leaves behind that still steers docker while RUNTIME,
# the one in use, is another: one line each, with its mend. use mends the
# dead plugin links and credsStore. The rest is only named, never changed:
# Docker Desktop wants it back as the runtime again, and most of it needs
# sudo. With Docker Desktop in use, only the dead links count. Its links in
# $SYSTEM_BIN count once they lead nowhere, or where Homebrew links docker
# there too (Intel): while Docker Desktop stays as a fallback, its helper
# there keeps its logins. Homebrew's formulae those links kept from linking
# must link once they go, or docker is gone; Homebrew may count one as linked
# already, so it unlinks first. Login Items are asked only while it is
# installed: an item for an app that is gone opens nothing.
desktop_leftovers() {
  local rt="$1" link gone links="" relink="" formula store target prefix
  gone="$(dead_plugins)"
  if [[ -n "$gone" ]]; then
    echo "$DOCKER_PLUGINS holds links into Docker.app that lead nowhere:$gone. docker lists each as a broken plugin. Remove them: $USE_COMMAND $rt"
  fi
  [[ "$rt" != docker-desktop ]] || return 0
  store="$(plutil -extract credsStore raw -o - "$DOCKER_CONFIG_FILE" 2>/dev/null)" || store=""
  if [[ "$store" == desktop ]] && command -v docker-credential-desktop &>/dev/null && keychain_serves "$rt"; then
    echo "credsStore \"desktop\" keeps docker's logins through Docker Desktop; the Keychain helper holds the same ones. Hand them over: $USE_COMMAND $rt"
  fi
  target="$(readlink "$SYSTEM_SOCKET" 2>/dev/null)" || target=""
  case "$target" in
    */.docker/run/docker.sock|*/com.docker.docker/*)
      echo "$SYSTEM_SOCKET leads to Docker Desktop, so tools that skip docker's context miss $rt. Point it at $rt: sudo ln -sf $(runtime_socket "$rt") $SYSTEM_SOCKET" ;;
  esac
  if [[ "$(plutil -extract features.hooks raw -o - "$DOCKER_CONFIG_FILE" 2>/dev/null)" == true ]]; then
    echo "$DOCKER_CONFIG_FILE turns on Docker Desktop's plugin hooks, so docker calls its plugins after run, build and pull. Turn them off: plutil -remove features.hooks $DOCKER_CONFIG_FILE"
  fi
  prefix="$(brew_prefix)"
  for link in "$SYSTEM_BIN"/docker*; do
    [[ -L "$link" && "$(readlink "$link")" == */Docker.app/* ]] || continue
    if [[ ! -e "$link" || "$SYSTEM_BIN" == "$prefix/bin" ]]; then links+=" $link"; fi
    formula="${link##*/}"
    if [[ "$formula" == docker-credential-osxkeychain ]]; then formula=docker-credential-helper; fi
    if [[ "$SYSTEM_BIN" == "$prefix/bin" && -d "$prefix/Cellar/$formula" ]]; then relink+=" $formula"; fi
  done
  if [[ -n "$relink" ]]; then relink="; then link Homebrew's own: brew unlink$relink && brew link$relink"; fi
  if [[ -n "$links" ]]; then
    echo "$SYSTEM_BIN holds links into Docker.app that lead nowhere or keep Homebrew's docker from linking there. Remove them: sudo rm$links$relink"
  fi
  if [[ "$rt" == colima ]] && runtime_installed docker-desktop && desktop_login_item; then
    echo "A Login Item opens Docker Desktop at login, and it takes docker's context from colima. Remove it: osascript -e 'tell application \"System Events\" to delete login item \"Docker Desktop\"'"
  fi
}

# A buildx builder remembers the context it was made on. One whose context is
# gone is found by name, so `inspect || create` guards never replace it.
# Colima removes a VM's context as the VM stops and makes it again at start,
# so the context of any VM Colima lists counts as there.
stale_builders() {
  local dir="${DOCKER_CONFIG:-$HOME/.docker}/buildx/instances" contexts file endpoint vm state
  [[ -d "$dir" ]] || return 0
  contexts=" $(docker context ls -q 2>/dev/null | tr '\n' ' ') "
  while read -r vm state; do
    if [[ "$vm" == default ]]; then contexts+="colima "; elif [[ -n "$vm" ]]; then contexts+="colima-$vm "; fi
  done <<< "$(colima_vms)"
  for file in "$dir"/*; do
    [[ -f "$file" ]] || continue
    endpoint="$(plutil -extract Nodes.0.Endpoint raw -o - "$file" 2>/dev/null)" || continue
    [[ "$endpoint" == unix://* || "$endpoint" == tcp://* ]] && continue
    [[ "$contexts" == *" $endpoint "* ]] || echo "$(basename "$file") $endpoint"
  done
}

# --- what runs where ----------------------------------------------------------

# Containers in RUNTIME, one per line: the name, a tab, then what it mounts
# (volume names, bind sources) between commas. Running ones, or all with -a.
# Docker Desktop lists a bind source as its VM sees it, under /host_mnt; the
# prefix goes. One listing, never an inspect per container: an inspect waits
# for a container its engine is still busy with, and once waited for good. A
# runtime whose app or VM is up gets listed, and a listing that fails stops
# the command, since nothing seen is not nothing running. The build VM goes by
# its context.
container_mounts() {
  local listing name mounts ctx
  runtime_up "$1" || return 0
  ctx="$(runtime_context "$1")"
  listing="$(briefly docker --context "${ctx:-$1}" ps "${@:2}" --no-trunc --format $'{{.Names}}\t{{.Mounts}}')" \
    || die "could not list the containers in $1"
  while IFS=$'\t' read -r name mounts; do
    [[ -n "$name" ]] || continue
    mounts=",$mounts,"
    printf '%s\t%s\n' "$name" "${mounts//,\/host_mnt\//,/}"
  done <<< "$listing"
}

# The containers in a container_mounts listing ($1) that mount $2: a volume by
# name, or a folder of the Mac or one inside it.
users_of() {
  local name mounts users=""
  while IFS=$'\t' read -r name mounts; do
    if [[ "$mounts" == *",$2,"* || "$mounts" == *",$2/"* ]]; then users+=" $name"; fi
  done <<< "$1"
  echo "${users# }"
}

# Refuse when RUNTIME, or the build VM by its context, and another running
# runtime or the build VM both have containers on $SAGE_DATA. Restart
# policies bring containers back as a runtime starts, so the refusal first
# stops what this command started: it must not leave the two writers it found.
guard_shared_data() {
  local rt="$1" other mine theirs listing
  listing="$(container_mounts "$rt")" || exit 1
  mine="$(users_of "$listing" "$SAGE_DATA")"
  [[ -n "$mine" ]] || return 0
  for other in $RUNTIMES "colima-$BUILD_PROFILE"; do
    [[ "$other" == "$rt" ]] && continue
    listing="$(container_mounts "$other")" || exit 1
    theirs="$(users_of "$listing" "$SAGE_DATA")"
    if [[ -n "$theirs" ]]; then
      stop_started
      die "both $rt ($mine) and $other ($theirs) are using $SAGE_DATA. Two runtimes writing there at once lose data. Stop one side first."
    fi
  done
}

# Stops while running containers use the volumes named in $2 in RUNTIME $1,
# or those in $4 in RUNTIME $3. A copy would read files mid-write: a database
# copied that way comes out torn with every file there, so the count passes.
# Restart policies bring containers back as a runtime starts; call this after.
refuse_in_use() {
  local rt names listing name users busy=""
  while (( $# >= 2 )); do
    rt="$1" names="$2"
    shift 2
    listing="$(container_mounts "$rt")" || exit 1
    for name in $names; do
      users="$(users_of "$listing" "$name")"
      if [[ -n "$users" ]]; then busy+=$'\n'"  $name: $users ($rt)"; fi
    done
  done
  [[ -z "$busy" ]] || die "running containers use these volumes, so nothing was copied:$busy"$'\n'"Stop them, then run this again."
}

# The words of $1, such as volume names, that $2 lacks.
lacking() {
  local word have out=""
  have=" $(tr '\n' ' ' <<< "$2") "
  for word in $1; do
    [[ "$have" == *" $word "* ]] || out+=" $word"
  done
  echo "${out# }"
}

# --- copies -------------------------------------------------------------------

# True when RUNTIME holds the volume. Only a listing that worked and lacks it
# means no: a failed probe once read as "empty", and the copy that followed
# deleted the data it should have kept.
volume_exists() {
  local names
  names="$(briefly docker --context "$(runtime_context "$1")" volume ls -q)" || die "could not list the volumes in $1"
  [[ $'\n'"$names"$'\n' == *$'\n'"$2"$'\n'* ]]
}

# Sets ENTRIES and KIB for volume $2 in RUNTIME $1: its files and folders (its
# own folder counts, so an empty volume has 1) and its size. A probe that
# fails stops the command, for the same reason.
measure_volume() {
  local out
  out="$(docker --context "$(runtime_context "$1")" run --rm -v "$2:/v:ro" "$COPY_IMAGE" \
    sh -c 'find /v | wc -l; du -sk /v | cut -f1' | tr '\n' ' ')" || out=""
  read -r ENTRIES KIB <<< "$out"
  [[ "$ENTRIES" =~ ^[0-9]+$ && "$KIB" =~ ^[0-9]+$ ]] || die "could not look inside volume $2 in $1"
}

# The Mac disk that holds a folder, and its free KiB: "DEVICE KIB".
room() {
  df -Pk "$1" 2>/dev/null | awk 'NR == 2 {print $1, $4}'
}

gib() {
  awk -v k="$1" 'BEGIN {printf "%.1f GiB", k / 1048576}'
}

# Fails, and says why, unless FREE KiB in WHERE cover NEED KiB.
fits() {
  local where="$1" free="$2" need="$3"
  if [[ ! "$free" =~ ^[0-9]+$ ]]; then
    echo "could not measure the free space in $where"
    return 1
  fi
  (( free >= need )) && return 0
  echo "not enough room in $where: the copy needs $(gib "$need") and $(gib "$free") is free. Free some space, then run it again."
  return 1
}

# The Mac folder that holds RUNTIME's VM disk: Colima's _disks, or Docker
# Desktop's data folder with Docker.raw. Docker Desktop's default one, and
# OrbStack's, live under ~/Library, on the home folder's disk; the home folder
# stands in, since macOS guards other apps' folders there.
vm_disk_dir() {
  case "$1" in
    colima)
      if [[ -d "$LIMA_DIR/_disks" ]]; then echo "$LIMA_DIR/_disks"; else echo "$LIMA_DIR"; fi ;;
    docker-desktop) plutil -extract DataFolder raw -o - "$DESKTOP_SETTINGS" 2>/dev/null || echo "$HOME" ;;
    orbstack)       echo "$HOME" ;;
  esac
}

# Fails, and says why, unless a copy of KIB fits, with a tenth and 1 GiB to
# spare: as the staged file on the Mac, and as the volume or image in the
# target VM. The VM's disk is a file on the Mac that grows as the VM writes,
# and the VM cannot see how full the Mac is (on 2026-10-08 Colima's saw 29
# GiB free on a drive with 15), so that disk needs the room too; when it is
# the staging disk, both must fit.
check_space() {
  local to="$1" mount="$2" kib="$3" need free stage disk
  need=$(( kib + kib / 10 + 1048576 ))
  free="$(docker --context "$(runtime_context "$to")" run --rm -v "$mount" "$COPY_IMAGE" df -Pk /v \
    | awk 'NR == 2 {print $4}')" || free=""
  fits "the $to VM" "$free" "$need" || return 1
  stage="$(room "$STAGE_DIR")" || stage=""
  disk="$(room "$(vm_disk_dir "$to")/")" || disk=""
  if [[ -n "$disk" && "${disk% *}" == "${stage% *}" ]]; then
    fits "$STAGE_DIR, which shares its disk with the $to VM" "${stage#* }" $(( need + kib ))
    return
  fi
  fits "the disk that holds the $to VM" "${disk#* }" "$need" || return 1
  fits "$STAGE_DIR" "${stage#* }" "$need"
}

make_stage_dir() {
  mkdir -p "$STAGE_DIR"
  chmod 700 "$STAGE_DIR"
}

# Drops the record of any copy into volume $1 in RUNTIME $2.
forget_copy() {
  [[ -f "$MIGRATED_FILE" ]] || return 0
  awk -v n="$1" -v t="$2" '!($1 == n && $3 == t)' "$MIGRATED_FILE" > "$MIGRATED_FILE.new"
  mv "$MIGRATED_FILE.new" "$MIGRATED_FILE"
}

# Records a verified copy of volume $1 from $2 to $3; $4 holds the source's
# files and folders and KiB.
record_copy() {
  forget_copy "$1" "$3"
  mkdir -p "$SAGE_CONFIG_DIR"
  echo "$1 $2 $3 $4" >> "$MIGRATED_FILE"
}

# The source's files and folders and KiB at the last verified copy of volume
# $1 from $2 to $3, if one is recorded.
recorded_copy() {
  [[ -f "$MIGRATED_FILE" ]] || return 0
  awk -v n="$1" -v f="$2" -v t="$3" '$1 == n && $2 == f && $3 == t {print $4, $5}' "$MIGRATED_FILE"
}

# A copy that fails or is cut short must not look finished. A volume the copy
# made goes; one a probe found empty just before, or whose data --force gave
# up, is emptied.
discard_copy() {
  local ctx
  ctx="$(runtime_context "$1")"
  case "$3" in
    made)
      docker --context "$ctx" volume rm -f "$2" >/dev/null 2>&1 \
        || echo "Warning: remove the half-made volume $2 in $1 before you use it: docker --context $ctx volume rm $2" >&2 ;;
    empty)
      docker --context "$ctx" run --rm -v "$2:/v" "$COPY_IMAGE" find /v -mindepth 1 -delete \
        || echo "Warning: empty the half-made volume $2 in $1 before you use it." >&2 ;;
  esac
}

# Copies volume NAME from runtime FROM to TO through a file in $STAGE_DIR,
# checks that both hold as many files and folders, and records the copy.
# FORCE=1 replaces a target that holds data.
copy_volume() {
  local name="$1" from="$2" to="$3" force="$4" src dst entries kib why state=made mount=/v
  # --force would clear the only copy before it is written back.
  [[ "$from" != "$to" ]] || die "volume $name would be copied from $to onto itself"
  src="$(runtime_context "$from")"
  dst="$(runtime_context "$to")"
  volume_exists "$from" "$name" || die "$from has no volume $name"
  refuse_in_use "$from" "$name" "$to" "$name"
  measure_volume "$from" "$name"
  entries=$ENTRIES kib=$KIB
  if volume_exists "$to" "$name"; then
    measure_volume "$to" "$name"
    state=empty mount="$name:/v:ro"
    if (( ENTRIES > 1 )); then
      (( force == 1 )) || die "$to already has a volume $name with data in it. Add --force to copy over it."
      state=data
    fi
  fi
  make_stage_dir
  why="$(check_space "$to" "$mount" "$kib")" || die "$why"
  echo "Copying volume $name from $from to $to..."
  STAGED="$STAGE_DIR/$name.tar"
  docker --context "$src" run --rm -v "$name:/v:ro" -v "$STAGE_DIR:/stage" "$COPY_IMAGE" \
    tar -C /v -cf "/stage/$name.tar" . \
    || die "could not read volume $name in $from. Free space in $STAGE_DIR: $(df -h "$STAGE_DIR" | awk 'NR==2 {print $4}')"
  forget_copy "$name" "$to"
  # --force gave up what the target held: a copy that stops from here, even
  # partway through the clear, leaves it empty rather than half cleared.
  HALF_MADE="$to $name ${state/data/empty}"
  if [[ "$state" == data ]]; then
    # Cleared only now, once the source is safely read: an exact copy, not a merge.
    docker --context "$dst" run --rm -v "$name:/v" "$COPY_IMAGE" find /v -mindepth 1 -delete \
      || die "could not clear volume $name in $to; run the copy again"
  fi
  docker --context "$dst" run --rm -v "$name:/v" -v "$STAGE_DIR:/stage:ro" "$COPY_IMAGE" \
    tar -C /v -xf "/stage/$name.tar" || die "could not write volume $name in $to; run the copy again"
  rm -f "$STAGED"
  STAGED=""
  measure_volume "$to" "$name"
  (( ENTRIES == entries )) || die "copy incomplete: $entries files and folders in $from, $ENTRIES in $to"
  HALF_MADE=""
  record_copy "$name" "$from" "$to" "$entries $kib"
  echo "Copied $ENTRIES files and folders ($KIB KiB; $kib KiB in $from)."
}

# docker for context $1, run inside the VM when that is a Colima one: an image
# save or load streams the whole image through the docker socket, and a big
# stream through Colima's (Lima's port forward) stalled for good (see
# STAGE_DIR). The VM reaches the staged file at the same path through its
# home-folder mount. ssh reads stdin, which a caller's loop may be reading.
vm_docker() {
  local ctx="$1"
  shift
  case "$ctx" in
    colima)   colima ssh --profile default -- docker "$@" < /dev/null ;;
    colima-*) colima ssh --profile "${ctx#colima-}" -- docker "$@" < /dev/null ;;
    *)        docker --context "$ctx" "$@" ;;
  esac
}

# Fails, and says why, unless image REF from RUNTIME FROM fits in runtime TO,
# by the size docker gives for it (see check_space).
image_fits() {
  local from="$1" to="$2" ref="$3" bytes
  bytes="$(briefly docker --context "$(runtime_context "$from")" image inspect --format '{{.Size}}' "$ref" 2>/dev/null)" \
    || bytes=""
  if [[ ! "$bytes" =~ ^[0-9]+$ ]]; then
    echo "$from has no image $ref"
    return 1
  fi
  make_stage_dir
  check_space "$to" /v $(( bytes / 1024 ))
}

# Saved to a file, then loaded: no stream between two daemons (see STAGE_DIR).
copy_image() {
  local src="$1" dst="$2" ref="$3" ok=0
  make_stage_dir
  STAGED="$STAGE_DIR/image-${ref//[\/:@]/_}.tar"
  if vm_docker "$src" save -o "$STAGED" "$ref" && vm_docker "$dst" load -i "$STAGED" >/dev/null; then ok=1; fi
  rm -f "$STAGED"
  STAGED=""
  (( ok == 1 ))
}

# --- convert ------------------------------------------------------------------

# A vz VM made before krunkit was the default stays vz until it is converted.
hint_convert() {
  krunkit_ready || return 0
  if colima_exists && [[ "$(vm_type)" == vz ]]; then
    echo "The Colima VM default is still vz. Move it to krunkit, keeping its images and volumes: $CONVERT_COMMAND"
  elif [[ -f "$CONVERT_FILE" ]]; then
    echo "A conversion of the Colima VM default to krunkit stopped partway. Finish it: $CONVERT_COMMAND --yes"
  fi
}

# The folders the everyday VM mounts in place of the home folder, from its
# Colima settings, one per line as colima start --mount takes them:
# PATH[:MOUNTPOINT][:w]. The list may sit at its key's indent or deeper. A
# line it cannot carry across comes out after a "?": a key colima start has
# no flag for, an item that does not start with its location, a flow-style
# list, a mount point that is not a full path.
colima_mounts() {
  [[ -f "$COLIMA_SETTINGS" ]] || return 0
  awk -v home="$HOME" '
    function flush() {
      if (path != "") print path (point != "" ? ":" point : "") (writable ? ":w" : "")
      path = ""; point = ""; writable = 0
    }
    function value(line) {
      sub(/^[^:]*: */, "", line)
      if (match(line, /^"[^"]*"/) || match(line, /^\047[^\047]*\047/)) return substr(line, 2, RLENGTH - 2)
      sub(/ +#.*$/, "", line); sub(/ +$/, "", line)
      return line
    }
    /^mounts:/ { inside = 1; if ($0 !~ /^mounts: *(\[\] *)?(#.*)?$/) print "?" $0; next }
    !inside || /^ *(#.*)?$/ { next }
    /^[^ -]/ { flush(); inside = 0; next }
    /^ *- *location:/ { flush(); path = value($0); sub(/^~/, home, path); next }
    path != "" && point == "" && /^ +mountPoint:/ { point = value($0); if (point ~ /^\//) next }
    path != "" && /^ +writable: *(true|false) *(#.*)?$/ { writable = ($0 ~ /: *true/); next }
    { print "?" $0 }
    END { flush() }
  ' "$COLIMA_SETTINGS"
}

# The folders of the everyday VM's root disk that its containers bind, or
# its volumes are bound to, one "OWNER: FOLDER" a line. Docker makes such a
# folder inside the VM for docker run -v /srv/pg:..., when the Mac does not
# share /srv. The system's own folders hold no app data, and findmnt -T tells
# the Mac's folders, Docker's and /run apart from the root disk.
# shellcheck disable=SC2016 # the VM's shell expands them
root_binds() {
  local listing name mounts path names device found probe
  local pairs=()
  listing="$(container_mounts colima -a)" || exit 1
  while IFS=$'\t' read -r name mounts; do
    IFS=, read -r -a found <<< "$mounts"
    for path in ${found[@]+"${found[@]}"}; do
      if [[ "$path" == /* ]]; then pairs+=("$name" "$path"); fi
    done
  done <<< "$listing"
  names="$(briefly docker --context colima volume ls -q)" || die "could not list the volumes in colima"
  if [[ -n "$names" ]]; then
    # shellcheck disable=SC2086 # one volume name a word
    listing="$(briefly docker --context colima volume inspect --format '{{.Name}} {{index .Options "device"}}' $names)" \
      || die "could not read the volumes in colima"
    while read -r name device; do
      if [[ "$device" == /* ]]; then pairs+=("volume $name" "$device"); fi
    done <<< "$listing"
  fi
  set -- ${pairs[@]+"${pairs[@]}"}
  pairs=()
  while (( $# >= 2 )); do
    case "$2/" in
      /bin/*|/boot/*|/etc/*|/lib/*|/lib64/*|/sbin/*|/usr/*|/var/log/*) ;;
      *) pairs+=("$1" "$2") ;;
    esac
    shift 2
  done
  (( ${#pairs[@]} > 0 )) || return 0
  probe='r="$(findmnt -no SOURCE /)" || exit 1; while [ $# -ge 2 ]; do'
  probe+=' s="$(findmnt -no SOURCE -T "$2")" && [ "${s%%\[*}" = "$r" ] && echo "$1: $2"; shift 2; done; exit 0'
  briefly colima ssh --profile default -- sh -c "$probe" sh "${pairs[@]}" < /dev/null 2>/dev/null \
    || die "could not ask the Colima VM default which disk holds the folders its containers bind. It stays vz; nothing changed."
}

# Stops unless Docker in the everyday VM keeps all its data on the data disk,
# where a krunkit VM made on it looks: colima delete takes the root disk. A
# folder there that a container binds goes too, and the comparison of names
# after the delete cannot see it.
need_data_disk() {
  local where binds nl=$'\n'
  where="$(docker_data_disk)"
  if [[ "$where" == data ]]; then
    binds="$(root_binds)" || { stop_started; exit 1; }
    [[ -n "$binds" ]] || return 0
    stop_started
    die "these keep data in folders of the Colima VM's root disk, which colima delete takes:"$'\n'"  ${binds//$nl/$nl  }"$'\n'"Move each into a volume or a folder of the Mac, or remove what holds it, then run this again. It stays vz; nothing changed."
  fi
  stop_started
  [[ -n "$where" ]] || die "could not ask the Colima VM default where Docker keeps its data (check: colima ssh -- findmnt -T /var/lib/docker), and colima delete takes its root disk with whatever is there. It stays vz; nothing changed."
  die "Docker in the Colima VM default keeps data in $where, which is not on its data disk where a krunkit VM looks (check: colima ssh -- findmnt -T $where). colima delete takes the root disk with whatever is there. It stays vz; nothing changed."
}

# Moves the everyday Colima VM from vz to krunkit; $1 is 1 to act, 0 for the
# plan alone. Docker keeps its images, volumes and containers on the VM's data
# disk, and colima delete keeps that disk unless told --data, so a krunkit VM
# made on it, at the same size, finds all of it. The delete takes the root
# disk, so a VM that does not show Docker's data on its data disk stays as it
# is. A boot that misses the disk shows none of it (abiosoft/colima#1614), so
# the volume names and image IDs go into CONVERT_FILE first and are compared
# after; a run cut short after the delete leaves the file, and the next run
# finishes from it. The delete also removes the VM's Colima settings: its size
# and mounts come across, and a copy of the file keeps the rest. Docker brings
# back by itself only the containers whose restart policy is always or
# unless-stopped; the others that ran are started by hand. Those started with
# --rm go as they stop, and Docker removes their anonymous volumes as the VM
# starts again, so neither counts. The plan starts nothing, so it reads only
# what already runs; a stopped VM is started for the record and stopped again
# at the end.
convert_colima() {
  local act="$1" type="" was_up=1 stopped=0 size cpus="" memory="" disk="" listing name policy autoremove policies line key value
  local running="" by_hand="" removed="" passing="" volumes="" images="" now gone lost="" id failed="" settings="" mounts=""
  local back lines bad
  # plan_colima, and start_new_colima through start_runtime, read these.
  local SAGE_RUNTIME_MEMORY="${SAGE_RUNTIME_MEMORY:-}" SAGE_RUNTIME_CPU="${SAGE_RUNTIME_CPU:-}" SAGE_RUNTIME_DISK="" VM_MOUNTS=()
  [[ "$(uname -m)" == arm64 ]] || die "krunkit runs only on Apple Silicon, so the Colima VM stays vz on this Mac."
  command -v krunkit &>/dev/null || die "krunkit is not installed. Get it: $KRUNKIT_INSTALL"
  if colima_exists; then
    type="$(vm_type)"
    [[ -n "$type" ]] || die "could not read the Colima VM's type from $LIMA_DIR/colima/lima.yaml"
  fi
  case "$type" in
    vz) ;;
    krunkit|"")
      if [[ ! -f "$CONVERT_FILE" ]]; then
        [[ -n "$type" ]] || die "there is no Colima VM to convert. Make a krunkit one: $USE_COMMAND colima"
        echo "The Colima VM default is a krunkit VM already."
        return 0
      fi ;;
    *) die "the Colima VM default is a $type VM; convert moves a vz VM." ;;
  esac

  if [[ "$type" == vz ]]; then
    size="$(colima_size default)"
    [[ -n "$size" ]] || die "Colima does not list the size of its VM default, and the krunkit VM must keep it."
    read -r cpus memory disk <<< "$size"
    memory="$(awk -v b="$memory" 'BEGIN {printf "%g", b / 1073741824}')"
    disk=$(( disk / 1073741824 ))
    lines="$(colima_mounts)"
    bad="$(sed -n 's/^?/  /p' <<< "$lines")"
    [[ -z "$bad" ]] || die "convert cannot carry these lines of the VM's mounts in $COLIMA_SETTINGS across:"$'\n'"$bad"$'\n'"It carries a mount's location, then its mountPoint (a full path) and writable. It stays vz; nothing changed."
    while IFS= read -r line; do
      if [[ -n "$line" ]]; then VM_MOUNTS+=(--mount "$line"); fi
    done <<< "$lines"
    [[ -e "$LIMA_DIR/_disks/colima/datadisk" ]] \
      || die "the Colima VM default has no data disk ($LIMA_DIR/_disks/colima/datadisk), so Docker keeps its images and volumes on the VM's root disk, which colima delete takes. It stays vz; nothing changed."
    runtime_up colima || was_up=0
    if (( was_up == 1 )); then need_data_disk; else stopped=1; fi
    guard_shared_data colima
    listing="$(container_mounts colima)" || exit 1
    # shellcheck disable=SC2013 # container names, one a word
    for name in $(cut -f1 <<< "$listing"); do running+=" $name"; done
    if [[ -n "$running" ]]; then
      # shellcheck disable=SC2086 # one container name a word
      policies="$(briefly docker --context colima inspect \
        --format '{{.Name}} {{.HostConfig.RestartPolicy.Name}} {{.HostConfig.AutoRemove}}' $running)" \
        || die "could not read the restart policies of the containers in colima"
      while read -r name policy autoremove; do
        name="${name#/}"
        if [[ "$autoremove" == true ]]; then
          removed+=" $name"
          # Its anonymous volumes: 64 hex digits, as migrate tells them.
          passing+="$(awk -F '\t' -v n="$name" '$1 == n {
            k = split($2, m, ","); for (i = 1; i <= k; i++) if (m[i] ~ /^[0-9a-f]+$/ && length(m[i]) == 64) printf " %s", m[i] }' <<< "$listing")"
        elif [[ "$policy" != always && "$policy" != unless-stopped ]]; then
          by_hand+=" $name"
        fi
      done <<< "$policies"
    fi
    by_hand="${by_hand# }" removed="${removed# }"
  else
    while read -r key value; do
      case "$key" in
        size)     read -r cpus memory disk <<< "$value" ;;
        mount)    VM_MOUNTS+=(--mount "$value") ;;
        settings) settings="$value" ;;
        stopped)  stopped="$value" ;;
        volumes)  volumes="$value" ;;
        images)   images="$value" ;;
        by-hand)  by_hand="$value" ;;
      esac
    done < "$CONVERT_FILE"
    [[ "$disk" =~ ^[0-9]+$ ]] || die "$CONVERT_FILE holds no size, so convert did not write it. Remove it, then run this again."
  fi
  SAGE_RUNTIME_MEMORY="${SAGE_RUNTIME_MEMORY:-$memory}" SAGE_RUNTIME_CPU="${SAGE_RUNTIME_CPU:-$cpus}" SAGE_RUNTIME_DISK="$disk"
  plan_colima default
  for line in ${VM_MOUNTS[@]+"${VM_MOUNTS[@]}"}; do
    if [[ "$line" != --mount ]]; then mounts+=" --mount $(printf '%q' "$line")"; fi
  done

  if [[ "$type" == vz ]]; then
    echo "The Colima VM default is vz: $memory GiB memory, $cpus CPUs, $disk GiB disk."
    echo "convert makes it krunkit on the same data disk: $VM_SIZE."
    if [[ -n "$mounts" ]]; then echo "It keeps the VM's mounts:$mounts"; fi
    if [[ -f "$COLIMA_SETTINGS" ]]; then
      echo "colima delete also removes the VM's Colima settings, $COLIMA_SETTINGS. The size and mounts come across; a copy of the file in $SAGE_CONFIG_DIR keeps the rest, such as docker's daemon settings."
    fi
    override_ready || echo "First it adds the krunkit settings to Lima's override file, which every Colima VM reads: $LIMA_OVERRIDE"
    if (( was_up == 0 )); then
      echo "The VM is stopped. convert starts it to check that Docker keeps its data on the data disk and to record its images and volumes, then stops it again at the end."
    else
      echo "Running containers it stops:${running:- none}"
      if [[ -n "$by_hand" ]]; then echo "It starts these again by hand, since Docker will not: $by_hand"; fi
      if [[ -n "$removed" ]]; then
        echo "Docker removes these as they stop, with their anonymous volumes, since they ran with --rm: $removed"
      fi
      if [[ -n "$running" && -z "$by_hand$removed" ]]; then echo "Docker starts them all again by itself."; fi
    fi
    if (( act == 0 )); then
      echo "Dry run: nothing changed. Convert: $CONVERT_COMMAND --yes"
      return 0
    fi
  else
    echo "A conversion of the Colima VM default to krunkit stopped partway, after colima delete. $CONVERT_FILE holds what the vz VM had."
    if [[ -z "$type" ]]; then echo "convert makes the krunkit VM on the same data disk: $VM_SIZE."; fi
    echo "It compares $(wc -w <<< "$volumes" | tr -d ' ') volumes and $(wc -w <<< "$images" | tr -d ' ') images with the vz VM's."
    if [[ -n "$by_hand" ]]; then echo "It starts these again by hand: $by_hand"; fi
    if (( act == 0 )); then
      echo "Dry run: nothing changed. Finish: $CONVERT_COMMAND --yes"
      return 0
    fi
  fi

  back="colima delete ran without --data, so the data disk keeps the vz VM's images and volumes. Once the krunkit VM is mended, finish the conversion: $CONVERT_COMMAND --yes
Or go back to vz on that disk:
  colima delete --force --profile default
  colima start --profile default --vm-type vz --vz-rosetta --mount-type virtiofs --mount-inotify --memory $memory --cpu $cpus --disk $disk$mounts"
  if [[ -n "$by_hand" ]]; then back+=$'\n'"Then start these containers again: docker --context colima start $by_hand"; fi
  if [[ -n "$settings" ]]; then back+=$'\n'"The vz VM's Colima settings: $settings"; fi

  if [[ "$type" == vz ]]; then
    # Neither needs the VM, so a refusal leaves a stopped one stopped.
    fix_lima_override
    override_ready || die "a krunkit VM needs \"mountType: virtiofs\" (abiosoft/colima#1607) and the boot step that mounts its data disk (abiosoft/colima#1614) in $LIMA_OVERRIDE. Add what it lacks, then run this again. The vz VM is as it was."
    if (( was_up == 0 )); then
      start_runtime colima
      need_data_disk
      guard_shared_data colima
    fi
    volumes="$(briefly docker --context colima volume ls -q | tr '\n' ' ')" || die "could not list the volumes in colima"
    volumes="$(lacking "$volumes" "$passing")"
    images="$(briefly docker --context colima images --all --quiet --no-trunc | sort -u | tr '\n' ' ')" \
      || die "could not list the images in colima"
    echo "Recorded $(wc -w <<< "$volumes" | tr -d ' ') volumes and $(wc -w <<< "$images" | tr -d ' ') images."
    mkdir -p "$SAGE_CONFIG_DIR"
    if [[ -f "$COLIMA_SETTINGS" ]]; then
      settings="$SAGE_CONFIG_DIR/colima-default.$(date +%Y%m%d-%H%M%S).yaml"
      cp "$COLIMA_SETTINGS" "$settings"
      back+=$'\n'"The vz VM's Colima settings: $settings"
    fi
    {
      echo "size $cpus $memory $disk"
      for line in ${VM_MOUNTS[@]+"${VM_MOUNTS[@]}"}; do
        if [[ "$line" != --mount ]]; then echo "mount $line"; fi
      done
      echo "settings $settings"
      echo "stopped $stopped"
      echo "volumes $volumes"
      echo "images $images"
      echo "by-hand $by_hand"
    } > "$CONVERT_FILE"
    stop_runtime colima
    ROLLBACK="$back"
    colima delete --force
  fi

  ROLLBACK="$back"
  start_runtime colima
  now="$(briefly docker --context colima volume ls -q)" || die "could not list the volumes in the krunkit VM"
  gone="$(lacking "$volumes" "$now")"
  if [[ -n "$gone" ]]; then lost+=$'\n'"  volumes: $gone"; fi
  now="$(briefly docker --context colima images --all --quiet --no-trunc)" || die "could not list the images in the krunkit VM"
  gone=""
  for id in $(lacking "$images" "$now"); do
    id="${id#sha256:}"
    gone+=" ${id:0:12}"
  done
  if [[ -n "$gone" ]]; then lost+=$'\n'"  images:$gone"; fi
  [[ -z "$lost" ]] || die "the krunkit VM lacks what the vz VM held:$lost"
  ROLLBACK=""
  for name in $by_hand; do
    docker --context colima start "$name" >/dev/null || failed+=" $name"
  done
  if (( stopped == 1 )); then stop_runtime colima; fi
  rm -f "$CONVERT_FILE"
  [[ -z "$failed" ]] || die "the VM is krunkit now, with every volume and image, but these containers did not start again:$failed. Start each by hand: docker --context colima start NAME"
  echo "The Colima VM default is krunkit now, with every volume and image it had."
}

# --- cleanup ------------------------------------------------------------------

# Whatever cuts a copy short, an error or a signal (Ctrl-C, a closed terminal,
# a kill), takes its staged file and any half-made volume with it. HALF_MADE
# holds the target runtime, the volume, and its state before the copy. A
# conversion cut short after the vz VM's delete prints ROLLBACK: the way on,
# and the way back. Ctrl-C skips the EXIT trap unless INT has one, and a
# cleanup step that fails would change the exit status, so none can.
STAGED="" HALF_MADE="" ROLLBACK=""
cleanup() {
  local rt name state
  if [[ -n "$STAGED" ]]; then rm -f "$STAGED" || true; fi
  if [[ -n "$HALF_MADE" ]]; then
    read -r rt name state <<< "$HALF_MADE"
    discard_copy "$rt" "$name" "$state"
  fi
  if [[ -n "$ROLLBACK" ]]; then echo "$ROLLBACK" >&2 || true; fi
}

# Sourcing sets no trap: it would replace the tool's own. A tool that copies
# or converts calls this once, right after sourcing.
trap_cleanup() {
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  trap 'exit 129' HUP
}
