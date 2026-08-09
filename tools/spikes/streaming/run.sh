#!/usr/bin/env bash
# Phase S streaming spike — runner. THROWAWAY.
#
# Brings up the spike server behind Caddy so the browser negotiates HTTP/2.
# h2 needs TLS, so Caddy issues an internal cert — the same trick the Cypress
# harness uses for its secure-context requirement.
#
# The one setting that matters: `flush_interval -1`. Without it Caddy buffers
# the proxied response and the token stream arrives as one lump at the end,
# which would make the spike look like it works while proving nothing. If you
# ever see all tokens land at once, check that line first.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
NET="${SPIKE_NET:-sage-spike}"
PORT="${SPIKE_PORT:-8443}"
IMG="python:3.11-slim"

cleanup() {
  docker rm -f spike-app spike-tls >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT
cleanup

docker network create "$NET" >/dev/null 2>&1 || true

cat > "$HERE/Caddyfile" <<'CADDY'
{
	auto_https disable_redirects
	admin off
}
# Both names: browsers reach it as localhost, the Cypress container
# reaches it as spike-tls over the docker network. One cert, both SNIs.
https://localhost:8443, https://spike-tls:8443 {
	tls internal
	reverse_proxy spike-app:8140 {
		flush_interval -1
	}
}
CADDY

echo "== spike server =="
docker run -d --name spike-app --network "$NET" \
  -v "$HERE:/spike" -w /spike "$IMG" python3 server.py 8140 >/dev/null

echo "== caddy (h2) =="
docker run -d --name spike-tls --network "$NET" -p "$PORT:8443" \
  -v "$HERE/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2-alpine >/dev/null

for i in $(seq 1 40); do
  curl -sk -o /dev/null "https://localhost:$PORT/" 2>/dev/null && break
  sleep 1
done

echo
echo "spike up: https://localhost:$PORT/  (self-signed; -k for curl)"
echo "run log:  docker logs spike-app"
echo
echo "Ctrl-C to tear down."
while true; do sleep 3600; done
