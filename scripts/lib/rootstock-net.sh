# rootstock-net.sh — curl a server on the rootstock's loopback, from outside it.
#
# Sprig™ child servers bind 127.0.0.1 inside the rootstock, so the host cannot
# reach them, and since 3.2.1 the image carries no curl or jq to call them from
# within (scripts/gates/in_container_tools.py keeps it that way). Instead curl
# runs in its own container that JOINS the rootstock's network namespace: the
# same loopback, none of the image's attack surface. Parse replies with the
# host's jq.
#
#   . "$(dirname "${BASH_SOURCE[0]}")/../lib/rootstock-net.sh"
#   DIM=$(netcurl -s "$URL/embeddings" -d '{"input":["x"]}' | jq '...')
#
# Needs $ROOT (the rootstock container name). A request that uploads a file
# (-F file=@/w/name) reads it from $NETCURL_DIR, mounted read-only at /w; make
# that folder with mount_tmp (lib/mount-tmp.sh) so Colima can mount it.
NETCURL_IMG="${NETCURL_IMG:-curlimages/curl:8.23.0@sha256:a134550be58ab783810e613ae96fd253c38f7bdd16d9bf9be350700c7a29ac06}"

netcurl() {
  docker run --rm --network "container:$ROOT" \
    ${NETCURL_DIR:+-v "$NETCURL_DIR:/w:ro"} "$NETCURL_IMG" "$@"
}
