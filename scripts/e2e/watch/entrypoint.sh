#!/bin/bash
# Virtual display -> VNC -> noVNC web page, then the interactive Cypress GUI.
set -e
export DISPLAY=:99
# Electron/Chromium inside a root container: no setuid sandbox, no GPU, and
# don't lean on /dev/shm (renderer dies with "bad IPC message reason 114"
# when shm is tiny — run-cypress-watch.sh also passes --shm-size=2g).
export ELECTRON_EXTRA_LAUNCH_ARGS="--no-sandbox --disable-gpu --disable-dev-shm-usage"
Xvfb :99 -screen 0 1440x900x24 &
# Wait for the X socket BEFORE attaching anything — x11vnc loses the race
# against Xvfb otherwise and dies silently (noVNC then "fails to connect").
for i in $(seq 1 50); do [ -S /tmp/.X11-unix/X99 ] && break; sleep 0.2; done
fluxbox >/dev/null 2>&1 &
# -loop: if x11vnc ever dies (display hiccup), it restarts itself.
x11vnc -display :99 -nopw -forever -shared -loop -quiet >/dev/null 2>&1 &
websockify --web /usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &
echo ""
echo "==============================================================="
echo "  Watch the automation:  http://localhost:6080/vnc.html"
echo "==============================================================="
echo ""
# Auto-dismiss Cypress's "What's New / major version welcome" screen so the
# GUI opens directly on the spec list — zero ceremonial clicks. The launchpad
# tracks this per major version in the global state.json; derive the major
# from the installed binary cache so a future image bump keeps working.
MAJOR=$(ls /root/.cache/Cypress 2>/dev/null | head -1 | cut -d. -f1)
if [ -n "$MAJOR" ]; then
  python3 - "$MAJOR" <<'PY'
import json, os, sys, time
major = sys.argv[1]
p = "/root/.config/Cypress/cy/production/projects/__global__/state.json"
os.makedirs(os.path.dirname(p), exist_ok=True)
try:
    s = json.load(open(p))
except Exception:
    s = {}
s.setdefault("majorVersionWelcomeDismissed", {})[major] = int(time.time() * 1000)
json.dump(s, open(p, "w"), indent=2)
PY
fi

exec cypress open --project /e2e --e2e --browser electron
