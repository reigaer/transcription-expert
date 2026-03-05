#!/bin/bash
# Setup script for Transcription Expert

set -e

echo "=== Transcription Expert Setup ==="
echo ""

# Check Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "Error: Python 3.11 is required but not found"
    echo "Install with: brew install python@3.11"
    exit 1
fi

echo "✓ Python 3.11 found"

# Check ffmpeg/ffprobe
if ! command -v ffprobe &> /dev/null; then
    echo "Error: ffmpeg is required but not found"
    echo "Install with: brew install ffmpeg"
    exit 1
fi

echo "✓ ffmpeg found"

# Check ollama
if ! command -v ollama &> /dev/null; then
    echo "Error: ollama is required but not found"
    echo "Install from: https://ollama.ai"
    exit 1
fi

echo "✓ ollama found"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3.11 -m venv venv

# Install dependencies
echo "Installing dependencies..."
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt

echo "✓ Dependencies installed"

# Pull Ollama model
echo ""
echo "Downloading Ollama model (granite3.3:8b)..."
echo "This may take a few minutes..."
ollama pull granite3.3:8b

echo "✓ Ollama model ready"

# Download Whisper model (will happen on first run, but we can check)
echo ""
echo "Note: Whisper large-v3 model (~3GB) will download on first transcription"

# Create output folder
echo ""
echo "Creating transcriptions folder..."
venv/bin/python3 -c "import config; config.ensure_folders_exist()"
echo "✓ Folders created"

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "To start the transcription service:"
echo "  ./venv/bin/python3 main.py"
echo ""
echo "Or use the convenience script:"
echo "  ./run.sh"
echo ""
echo "Output location: ~/Library/Mobile Documents/com~apple~CloudDocs/Transcriptions"
echo ""
