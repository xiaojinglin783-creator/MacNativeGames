#!/usr/bin/env bash
# Compiles graphics without reading game files, keys or saves; preserves failure status.
set -euo pipefail
cd "$(dirname "$0")/.."
backend="${1:-3}"
case "$backend" in 3|4) ;; *) echo 'Usage: bash scripts/check_macos_backend.sh 3|4' >&2; exit 2;; esac
mkdir -p build
log="$PWD/build/check-metal${backend}.log"
{
  uname -sm
  if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
    echo 'BLOCKED: Apple silicon macOS and Xcode are required for native compilation.' >&2
    exit 2
  fi
  sw_vers
  xcrun --sdk macosx --show-sdk-version
  xcrun clang --version
  make -j2 "METAL_BACKEND=$backend" check-metal
  if [[ "$backend" == 3 ]]; then make METAL_BACKEND=3 probe-metal3-arguments; fi
  echo "PASS: Metal $backend native graphics compilation and applicable GPU smoke check"
} 2>&1 | tee "$log"
