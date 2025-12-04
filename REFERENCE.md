# Reference

Detailed configuration, troubleshooting, and architecture information.

## Configuration

All settings in `config.py`:

### Paths

```python
# Voice Memos source (macOS Group Container)
VOICE_MEMOS_PATH = (
    Path.home() / "Library" / "Group Containers" /
    "group.com.apple.VoiceMemos.shared" / "Recordings"
)

# Output folder (iCloud Drive)
ICLOUD_DRIVE = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
TRANSCRIPTIONS_FOLDER = ICLOUD_DRIVE / "Transcriptions"
```

**To change output location:**
```python
TRANSCRIPTIONS_FOLDER = Path.home() / "Documents" / "Transcriptions"
```

### Models

```python
# Whisper: large-v3-turbo (best), large-v3, medium (faster), base (fastest)
WHISPER_MODEL = "large-v3-turbo"  # 2.7x faster than large-v3, better accuracy
WHISPER_DEVICE = "auto"  # auto, cpu, cuda
WHISPER_COMPUTE_TYPE = "auto"  # auto, int8, float16

# Ollama: any model from ollama.com/library
OLLAMA_MODEL = "granite3.3:8b"  # Best instruction-following for cleanup
# Alternatives:
# - "qwen2.5:7b" (good quality, slower)
# - "llama3.2:3b" (faster, smaller)
```

**Model sizes:**
- Whisper large-v3-turbo: ~1.5GB download, ~2.5GB RAM
- Whisper large-v3: ~3GB download, ~4GB RAM
- Whisper medium: ~1.5GB download, ~2GB RAM
- granite3.3:8b: ~5GB download, ~5GB RAM

### Processing Settings

```python
# Supported audio formats
SUPPORTED_FORMATS = {".m4a", ".mp3", ".wav", ".aiff", ".caf", ".aac"}

# Minimum file size (bytes) - ignore tiny files
MIN_FILE_SIZE_BYTES = 1024

# Wait time (seconds) for file to stabilize before processing
STABLE_FILE_WAIT_SECONDS = 2
```

## Special Modes

Use trigger words at the **start** of your recording to activate special modes.

### Blog Mode

Start with **"Hugo"** to generate Hugo-compatible blog posts with full frontmatter.

**Trigger:** `Hugo` (first word)

**Output filename:** `2025-12-04_blog_My_Blog_Title.md`

**Output format:**
```markdown
---
title: "My Blog Title"
date: 2025-12-04T10:30:00
author: Reiner
description: "Auto-generated description"
tags: ["tag1", "tag2"]
categories: ["Thoughts"]
draft: false
---

Your blog content here.
```

### Checkin/Checkout Mode

Start with **"Check in"** or **"Check out"** for daily journaling with tagged filenames.

**Triggers (English):** `Check in`, `Checkin`, `Check-in`
**Triggers (German):** `Einchecken`

**Triggers (English):** `Check out`, `Checkout`, `Check-out`
**Triggers (German):** `Auschecken`

**Output filenames:**
- `2025-12-04_checkin_Morning_Thoughts.md`
- `2025-12-04_checkout_Daily_Summary.md`

The trigger phrase is removed from the transcription. Content uses regular note format.

### Combining Modes

Modes can be combined. Start with checkin/checkout, then Hugo:

**Recording:** "Check in. Hugo. Today I want to write about..."

**Output:** `2025-12-04_checkin_blog_My_Topic.md` (Hugo frontmatter)

### LLM Prompts

Customize text cleanup behavior:

```python
CLEANUP_PROMPT = """Clean up this voice transcription by:
1. Adding proper punctuation and capitalization
2. Creating paragraph breaks at natural pauses or topic changes
3. Removing filler words (um, uh, like, you know, etc.)

CRITICAL: Do not change, add, or remove any meaningful words. Only format and remove fillers.

Transcription:
{text}

Return only the cleaned text."""

TOPIC_PROMPT = """Generate a concise 3-6 word topic title for this transcription.
Make it descriptive and filename-safe (no special characters except spaces/hyphens).

Transcription:
{text}

Return only the topic title."""
```

## Architecture

### System Flow

```
Voice Memos Folder
       ↓
File Watcher (watchdog)
  • Detects .m4a files
  • Waits for stability (2s)
       ↓
Transcription Engine
  • Load Whisper (lazy)
  • Transcribe + detect language
  • Get duration via ffprobe
       ↓
Text Cleanup (Ollama)
  • Remove fillers
  • Add punctuation
  • Format paragraphs
       ↓
Topic Generation (Ollama)
  • Analyze content
  • Generate 3-6 word title
       ↓
Markdown Generation
  • YAML frontmatter
  • Sanitized filename
  • Save to iCloud
```

### Project Structure

```
transcription-expert/
├── main.py              # Entry point, logging, coordination
├── config.py            # All settings
├── transcriber.py       # Whisper + Ollama processing
├── watcher.py           # File system monitoring
├── setup.sh            # Installation script
├── run.sh              # Start script
├── install-service.sh  # LaunchAgent installer
├── requirements.txt    # Python dependencies
├── .processed_files    # Tracking (auto-generated)
└── transcription.log   # Logs (auto-generated, rotates at 5MB)
```

### Memory Management

**Lazy Loading:**
- Whisper model loads only on first transcription
- Model stays loaded for subsequent files
- Released on shutdown via `engine.cleanup()`

**Typical RAM usage:**
- Idle (watcher only): ~100MB
- Transcribing: ~3-4GB (Whisper loaded)
- Cleanup: ~2GB (Ollama loaded separately)
- Peak: ~4GB (never both models simultaneously)

### Output Format

**Filename:** `YYYY-MM-DD_Topic_Title.md`

**Content:**
```markdown
---
date: 2025-11-08T14:30:22
language: en
topic: Descriptive Topic Title
source_file: Recording_001.m4a
duration: 3m 45s
---

Transcription text with proper formatting.

Paragraph breaks at natural pauses.
```

**Duplicate handling:** Appends `_1`, `_2`, etc. if filename exists.

## Troubleshooting

### Voice Memos Folder Not Found

**Symptom:** `FileNotFoundError: Voice Memos folder not found`

**Solutions:**

1. **Check default location:**
   ```bash
   ls ~/Library/Group\ Containers/group.com.apple.VoiceMemos.shared/Recordings
   ```

2. **Find your recordings:**
   ```bash
   mdfind -name "Voice Memos"
   ```

3. **Update config.py:**
   ```python
   VOICE_MEMOS_PATH = Path("/your/actual/path")
   ```

### Ollama Connection Errors

**Symptom:** `Connection refused` or `Ollama not responding`

**Solutions:**

1. **Start ollama service:**
   ```bash
   ollama serve
   ```

2. **Check if running:**
   ```bash
   curl http://localhost:11434
   ```

3. **Verify model downloaded:**
   ```bash
   ollama list
   ```

4. **Download model manually:**
   ```bash
   ollama pull qwen2.5:3b
   ```

### Whisper Model Download Issues

**Symptom:** `Model download failed` or stalls

**Solutions:**

1. **Check disk space:**
   ```bash
   df -h
   ```
   Need ~5GB free.

2. **Check internet connection**

3. **Download manually:**
   ```bash
   ./venv/bin/python3 -c "from faster_whisper import WhisperModel; WhisperModel('large-v3')"
   ```

### Service Not Starting

**Symptom:** Service doesn't run on login

**Check if loaded:**
```bash
launchctl list | grep transcription
```

**View service logs:**
```bash
tail -f transcription.log
```

**Reload service:**
```bash
launchctl unload ~/Library/LaunchAgents/com.transcription-expert.plist
launchctl load ~/Library/LaunchAgents/com.transcription-expert.plist
```

**Check permissions:**
```bash
ls -l ~/Library/LaunchAgents/com.transcription-expert.plist
```

### Files Not Processing

**Symptom:** Voice memo created but not transcribed

**Debug steps:**

1. **Check if file is supported format:**
   ```bash
   # .m4a files are default for Voice Memos
   file /path/to/recording.m4a
   ```

2. **Check file size:**
   ```bash
   ls -lh /path/to/recording.m4a
   # Must be >1KB (see MIN_FILE_SIZE_BYTES)
   ```

3. **Check if already processed:**
   ```bash
   cat .processed_files
   ```

4. **Watch logs in real-time:**
   ```bash
   tail -f transcription.log
   ```

5. **Test manually:**
   ```bash
   ./venv/bin/python3 -c "
   from pathlib import Path
   from transcriber import TranscriptionEngine
   engine = TranscriptionEngine()
   engine.process(Path('/path/to/recording.m4a'))
   "
   ```

### Poor Transcription Quality

**Symptoms:** Wrong words, missing content, wrong language

**Solutions:**

1. **Use larger Whisper model:**
   ```python
   # In config.py
   WHISPER_MODEL = "large-v3-turbo"  # Best accuracy (default)
   ```

2. **Check audio quality:**
   - Use external mic on Mac
   - Avoid noisy environments
   - Speak clearly

3. **Force language (if auto-detect fails):**
   ```python
   # In transcriber.py, line 85
   segments, info = self.whisper_model.transcribe(
       str(audio_path),
       language="en",  # Force English
       vad_filter=True,
   )
   ```

### Excessive Memory Usage

**Symptom:** System slowing down, high RAM usage

**Solutions:**

1. **Use smaller Whisper model:**
   ```python
   WHISPER_MODEL = "medium"  # ~2GB vs 4GB
   ```

2. **Use smaller Ollama model:**
   ```python
   OLLAMA_MODEL = "gemma2:2b"  # ~1.5GB vs 2GB
   ```

3. **Restart service periodically:**
   ```bash
   launchctl kickstart -k gui/$UID/com.transcription-expert
   ```

## Performance

**M4 Mac Mini, 16GB RAM (with large-v3-turbo):**

| Recording Length | Transcription Time | Cleanup Time | Total Time |
|-----------------|-------------------|--------------|------------|
| 1 minute        | 30-60 seconds     | 10-15 seconds| ~1 minute  |
| 3 minutes       | 2-3 minutes       | 15-20 seconds| ~3 minutes |
| 10 minutes      | 6-10 minutes      | 20-30 seconds| ~10 minutes|

**Factors affecting speed:**
- Whisper model size (large > medium > base)
- Audio quality (noisy audio takes longer)
- CPU load (other processes)
- Language (English fastest, others similar)

## Development

### Run Tests

```bash
./venv/bin/pytest -v
```

**18 tests covering:**
- Configuration validation
- Watcher behavior
- Transcription pipeline
- File handling
- Error cases

### Lint Code

```bash
./venv/bin/ruff check .
```

Configured in `pyproject.toml`:
- Line length: 100
- Python 3.11+ syntax
- Import sorting
- PEP8 compliance

### Manual Testing

```bash
# Create test audio file
./venv/bin/python3 test_transcriber.py

# Process single file
./venv/bin/python3 -c "
from pathlib import Path
from transcriber import TranscriptionEngine
engine = TranscriptionEngine()
result = engine.process(Path('test.m4a'))
print(f'Created: {result}')
"
```

## Logs

**Location:** `transcription.log` in project directory

**Rotation:** Max 5MB, keeps 2 backups (15MB total)

**Log levels:**
- INFO: Normal operation
- WARNING: Skipped files, minor issues
- ERROR: Failed processing, exceptions

**Useful log patterns:**

```bash
# Watch processing in real-time
tail -f transcription.log

# Find errors
grep ERROR transcription.log

# See what was processed today
grep $(date +%Y-%m-%d) transcription.log

# Count processed files
grep "Successfully processed" transcription.log | wc -l
```

## License

MIT - Free to use, modify, distribute.
