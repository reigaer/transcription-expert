#!/bin/bash
# Run the transcription service

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    ./setup.sh
fi

echo "Starting Transcription Expert..."
echo "Press Ctrl+C to stop"
echo ""

./venv/bin/python3 main.py
