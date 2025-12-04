# Transcription Expert

**Automatic voice memo transcription for macOS. Record → Get searchable markdown.**

## The Problem

You record voice memos but never transcribe them. They sit unused because manual transcription takes forever.

## The Solution

This system watches your Voice Memos folder and automatically:

1. Detects new recordings (any language)
2. Transcribes with Whisper large-v3-turbo
3. Cleans up text (punctuation, paragraphs, removes fillers)
4. Saves to iCloud Drive as searchable markdown

**Zero interaction. Set and forget.**

## Example

**You record:** "Um, so I was thinking, like, we need to prioritize the backend API development before moving to, uh, the frontend components..."

**You get:** `2025-11-08_Backend_API_Priority_Discussion.md`

```markdown
---
date: 2025-11-08T14:30:22
language: en
topic: Backend API Priority Discussion
duration: 2m 15s
---

We need to prioritize the backend API development before moving to the frontend components.
The database schema should be finalized by next week, allowing the team to begin integration testing.
```

## Who This Is For

- You record voice memos regularly
- You want them searchable and readable
- You don't want to think about transcription
- You have a Mac with 16GB+ RAM

## What You Get

- **Fully automated** - Runs in background, starts on login
- **High accuracy** - Whisper large-v3-turbo, multi-language
- **Clean output** - AI removes fillers, adds formatting
- **Searchable** - Markdown in iCloud Drive (Spotlight indexed)
- **Fast** - ~1-2 minutes per 3-minute recording (M4 Mac)

## System Requirements

- macOS (tested on M4 Mac Mini)
- 16GB RAM minimum
- Python 3.11
- ~5GB disk space (models)

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) - Running in 5 minutes.

## Configuration & Troubleshooting

See [REFERENCE.md](REFERENCE.md) for detailed options.

## Philosophy

This project follows **das wenige** (the essential):

- Does ONE thing perfectly
- No UI, no dashboard, no complexity
- Runs silently in background
- Zero configuration needed
- Every feature earns its place

**Q:** "Why not add [feature X]?"
**A:** Does it make automatic transcription simpler? No? Then no.

## License

MIT

## Credits

- **Whisper** - OpenAI's speech recognition
- **faster-whisper** - Optimized implementation
- **Ollama** - Local LLM runtime (granite3.3:8b)
