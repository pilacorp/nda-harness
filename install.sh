#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  echo 'NDA Harness requires Python 3.9+; no pip installation is needed.' >&2
  exit 2
fi
exec python3 "$root/scripts/install_cli.py" "$@"
