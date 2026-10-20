#!/bin/sh
# Open a visible terminal in the project directory and run selection-setup.
set -eu
client=${1:?}
project=${2:-$(pwd)}
case "$client" in
  codex|cursor|claude) ;;
  *)
    echo 'Unsupported client.' >&2
    exit 2
    ;;
esac
if [ ! -d "$project" ]; then
  echo 'Project directory is missing.' >&2
  exit 2
fi
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
osascript - "$project" "$root/bin/nda-plugin" "$client" <<'EOF'
on run argv
  set projectPath to item 1 of argv
  set pluginPath to item 2 of argv
  set clientName to item 3 of argv
  set commandText to "cd " & quoted form of projectPath & " && rtk proxy " & quoted form of pluginPath & " selection-setup --client " & quoted form of clientName
  tell application "Terminal"
    activate
    do script commandText
  end tell
end run
EOF
