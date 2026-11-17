#!/bin/bash
set -euo pipefail
LABEL="com.example.globalremoteradar"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
if [ -f "$TARGET" ]; then
  launchctl unload "$TARGET" 2>/dev/null || true
  rm "$TARGET"
  echo "Removed $TARGET"
else
  echo "No installed LaunchAgent found at $TARGET"
fi
