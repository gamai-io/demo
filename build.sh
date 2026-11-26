#!/bin/sh
# Build index.html from the crossnode-bench v1.4.0 result files.
#
#   ./build.sh            fetch the artifacts (if absent) and regenerate index.html
#   ./build.sh --check    fetch (if absent) and verify the committed page is current
#   ARTIFACTS=DIR ./build.sh   use an existing checkout/release folder instead
#
# Stdlib only: python3 + git. No network access once artifacts/ exists.
set -eu

cd "$(dirname "$0")"

ARTIFACTS="${ARTIFACTS:-artifacts}"
TAG="v1.4.0"
UPSTREAM="https://github.com/gamai-io/crossnode-bench.git"
SUBDIR="results/vultr-fleet-2026-11-09-200"

need_artifacts() {
    [ -f "$ARTIFACTS/honest/evidence.jsonl.gz" ] && [ -f "$ARTIFACTS/liar/evidence.jsonl.gz" ]
}

fetch() {
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    echo "fetching crossnode-bench $TAG ($SUBDIR) -> $ARTIFACTS"
    git clone --quiet --depth 1 --branch "$TAG" "$UPSTREAM" "$tmp/src"
    mkdir -p "$ARTIFACTS"
    cp -R "$tmp/src/$SUBDIR/." "$ARTIFACTS/"
}

if ! need_artifacts; then
    fetch
fi

if [ "${1:-}" = "--check" ]; then
    exec python3 render.py --artifacts "$ARTIFACTS" --check
fi
python3 render.py --artifacts "$ARTIFACTS"
