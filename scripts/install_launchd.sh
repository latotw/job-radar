#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.example.globalremoteradar"
TEMPLATE="$ROOT/scripts/$LABEL.plist.template"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"
sed "s|__PROJECT__|$ROOT|g" "$TEMPLATE" > "$TARGET"
plutil -lint "$TARGET"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$TARGET"
echo "Installed and enabled $LABEL from $TARGET. It runs daily at 23:00 local time."
