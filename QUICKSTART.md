# Quick Start

**Goal: Running in 5 minutes.**

## Step 1: Install Prerequisites

```bash
brew install python@3.11 ffmpeg ollama
```

## Step 2: Setup

```bash
./setup.sh
```

This takes 2-3 minutes:
- Creates virtual environment
- Installs Python packages
- Downloads Ollama model (~2GB)
- Creates output folder

Whisper model (~3GB) downloads on first use.

## Step 3: Start

```bash
./run.sh
```

You should see:
```
=== Transcription Expert Starting ===
Whisper model: large-v3-turbo
Cleanup model: granite3.3:8b
Watching: ~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings
Output: ~/Library/Mobile Documents/com~apple~CloudDocs/Transcriptions/
Watcher started. Monitoring for new audio files...
```

## Step 4: Test

1. **Record a voice memo** on your iPhone or Mac (10-30 seconds)
2. **Wait ~30 seconds** for iCloud sync
3. **Watch terminal** - you'll see transcription progress
4. **Check output:**
   ```bash
   open ~/Library/Mobile\ Documents/com~apple~CloudDocs/Transcriptions
   ```

Expected timeline:
- File detected: instant
- Transcription: 1-2x realtime
- Cleanup: ~5 seconds
- Total: ~1-3 minutes for 1-minute recording

## Step 5: Run as Service (Optional)

For automatic background operation:

```bash
./install-service.sh
```

Now it starts automatically when you log in.

**To stop/uninstall:**
```bash
./uninstall-service.sh
```

## Success Criteria

✅ Terminal shows "Watcher started"
✅ Recording a memo creates a markdown file
✅ File appears in iCloud Transcriptions folder
✅ Text is cleaned (no "um", proper punctuation)

## Common Issues

**"Voice Memos folder not found"**
```bash
# Check where your recordings are:
ls ~/Library/Group\ Containers/group.com.apple.VoiceMemos.shared/Recordings

# If different, edit config.py line 6-8
```

**"Ollama connection refused"**
```bash
# Start ollama in another terminal:
ollama serve
```

**Service not auto-starting**
```bash
# Check if running:
launchctl list | grep transcription

# View logs:
tail -f transcription.log
```

## What's Next?

- **Customize**: Edit `config.py` for different models/paths
- **Troubleshoot**: See [REFERENCE.md](REFERENCE.md)
- **Just use it**: Record memos, get markdown

The system runs silently. No interaction needed.
