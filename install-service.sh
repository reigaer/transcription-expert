#!/bin/bash
# Install transcription service to run automatically at login

set -e

PLIST_NAME="com.transcription-expert.plist"
PLIST_SRC="$(pwd)/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "=== Installing Transcription Expert as Launch Agent ==="
echo ""

# Copy plist to LaunchAgents
echo "Installing launch agent..."
cp "$PLIST_SRC" "$PLIST_DEST"

# Load the service
echo "Loading service..."
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo ""
echo "✓ Service installed successfully!"
echo ""
echo "The transcription service will now:"
echo "  - Start automatically at login"
echo "  - Restart if it crashes"
echo "  - Run in the background"
echo ""
echo "To stop the service:"
echo "  launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
echo ""
echo "To start the service manually:"
echo "  launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
echo ""
echo "To check if it's running:"
echo "  launchctl list | grep transcription"
echo ""
echo "Logs location:"
echo "  $(pwd)/transcription.log"
echo ""
