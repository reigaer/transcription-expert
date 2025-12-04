#!/bin/bash
# Uninstall transcription service

set -e

PLIST_NAME="com.transcription-expert.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "=== Uninstalling Transcription Expert Service ==="
echo ""

if [ -f "$PLIST_DEST" ]; then
    echo "Stopping service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true

    echo "Removing launch agent..."
    rm "$PLIST_DEST"

    echo ""
    echo "✓ Service uninstalled successfully!"
else
    echo "Service is not installed."
fi

echo ""
