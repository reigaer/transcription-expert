"""Configuration for the transcription system."""

import os
from pathlib import Path

# Load .env file (stdlib only, no python-dotenv needed)
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _val = _line.partition("=")
            os.environ.setdefault(_key.strip(), _val.strip())

# Voice Memos source folder (Group Container location)
VOICE_MEMOS_PATH = (
    Path.home()
    / "Library"
    / "Group Containers"
    / "group.com.apple.VoiceMemos.shared"
    / "Recordings"
)

# Output folder in iCloud Drive
ICLOUD_DRIVE = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
TRANSCRIPTIONS_FOLDER = ICLOUD_DRIVE / "Transcriptions"

# Obsidian vault on iCloud
OBSIDIAN_VAULT = ICLOUD_DRIVE / "texts"
CALENDAR_FOLDER = OBSIDIAN_VAULT / "Calendar"

# Month names for Calendar/YYYY/MM-Month/ folder structure
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def get_calendar_folder(dt: "datetime | None" = None) -> Path:
    """Return Calendar/YYYY/MM-Month/ for the given datetime, creating if needed."""
    from datetime import datetime as _dt
    if dt is None:
        dt = _dt.now()
    folder = CALENDAR_FOLDER / str(dt.year) / f"{dt.month:02d}-{MONTH_NAMES[dt.month]}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

# Model settings
WHISPER_MODEL = (
    "large-v3-turbo"  # 2.7x faster than large-v3, better accuracy (1.9% vs 2.9% WER)
)
WHISPER_DEVICE = "auto"
WHISPER_COMPUTE_TYPE = "auto"
OLLAMA_MODEL = (
    "granite3.3:8b"  # Purpose-built for structured output and instruction following
)

# Supported audio formats
SUPPORTED_FORMATS = {".m4a", ".mp3", ".wav", ".aiff", ".caf", ".aac", ".qta"}

# Processing settings
MIN_FILE_SIZE_BYTES = 1024
STABLE_FILE_WAIT_SECONDS = 2

# LLM prompts
CLEANUP_PROMPT = """You are a minimal transcription cleaner. Your ONLY job is to fix obvious errors while keeping the speaker's EXACT word choices.

DETECTED LANGUAGE: {language}

⚠️ CRITICAL: DO NOT ADD ANY CONTENT THAT IS NOT IN THE ORIGINAL TRANSCRIPTION ⚠️
You must output ONLY what was actually spoken. When the transcription ends, STOP IMMEDIATELY.
Do NOT continue the thought, add conclusions, or invent additional sentences.

WHAT YOU MAY CHANGE (only these things):
1. Add punctuation (periods, commas, question marks, etc.)
2. Fix capitalization (sentence starts, proper nouns, "I")
3. Split the content into logical paragraphs with natural breaks
   - Add a blank line (two newlines) between each paragraph
   - Start new paragraphs when the topic shifts or after natural pauses
4. Remove ONLY these filler words:
   - English: um, uh, er, ah
   - German: äh, ähm
5. Fix ONLY obvious stutters where the same word is repeated (e.g., "the the" → "the")

WHAT YOU MUST NOT CHANGE:
- Do NOT rephrase or improve the speaker's wording
- Do NOT change word choices, even if they seem imperfect or informal
- Do NOT fix grammar beyond punctuation (keep the speaker's natural grammar)
- Do NOT remove words like "like", "you know", "actually", "also", "sort of" unless they're clearly filler
- Do NOT summarize or shorten anything
- Do NOT add new words or ideas - NEVER INVENT CONTENT
- Do NOT translate or change language
- Do NOT add concluding thoughts or continue incomplete sentences
- Keep ALL the original words in their original order (except pure fillers like "um", "äh")

⚠️ STOP EXACTLY WHERE THE TRANSCRIPTION ENDS - DO NOT ADD ANYTHING BEYOND WHAT WAS SPOKEN ⚠️

KEEP THE ENTIRE TEXT IN THE ORIGINAL LANGUAGE: {language}

FORMATTING REQUIREMENTS:
- Separate paragraphs with a blank line (two newlines: \\n\\n)
- Each paragraph should be readable on its own
- Use paragraph breaks to improve readability and flow

Your goal: Make it readable with punctuation and proper paragraph formatting, but preserve the speaker's authentic voice and exact word choices.

Transcription:
{text}

Return the minimally cleaned text in {language} with proper paragraph breaks.

SENTIMENT ANALYSIS (required):
After the cleaned text, add a blank line, then exactly: SENTIMENT: [word]

Choose ONE sentiment based on the speaker's emotional tone:

positive - Speaker expresses:
  EN: gratitude, excitement, hope, joy, optimism, enthusiasm
  DE: Dankbarkeit, Freude, Hoffnung, Begeisterung, Optimismus

neutral - Speaker conveys:
  EN: facts, information, plans, descriptions, observations
  DE: Fakten, Informationen, Pläne, Beschreibungen, Beobachtungen

reflective - Speaker is:
  EN: contemplating, processing, thinking through, pondering, questioning
  DE: nachdenklich, grübelnd, überlegend, verarbeitend

negative - Speaker feels:
  EN: worried, frustrated, sad, stressed, anxious, disappointed
  DE: besorgt, frustriert, traurig, gestresst, ängstlich, enttäuscht

Output format:
[cleaned text]

SENTIMENT: [positive|neutral|reflective|negative]"""

TOPIC_PROMPT = """Generate a concise, descriptive topic title (3-6 words) for this transcription.

Requirements:
- Capture the main subject or purpose
- Use title case (capitalize major words)
- Make it filename-safe (no special characters except spaces and hyphens)
- Be specific and informative
- Use the same language as the transcription

Examples:
- "Project Timeline Discussion and Tasks"
- "German Grammar Learning Notes"
- "Weekly Team Status Update"

Transcription:
{text}

Return ONLY the topic title, nothing else."""

# Blog mode settings
BLOG_TRIGGER = "hugo"
AIDENKING_TRIGGER = "aiden king"

# Blog output folders (iCloud vault, language-routed)
BLOG_OUTPUT = {
    "de": ICLOUD_DRIVE / "texts" / "Writings" / "blog-de",
    "en": ICLOUD_DRIVE / "texts" / "Writings" / "blog-en",
}
AIDENKING_OUTPUT = ICLOUD_DRIVE / "texts" / "Writings" / "aidenking-blog"

# Aiden King frontmatter template (simpler than Hugo)
AIDENKING_FRONTMATTER = """---
title: "{title}"
date: {date}
description: "{description}"
draft: true
---"""

# Essential categories (das-wenige: 6 only, bilingual)
BLOG_CATEGORIES = {
    "de": [
        "Gedanken",
        "Produktivität",
        "Buchnotizen",
        "Technologie",
        "Leben",
        "Reisen",
    ],
    "en": ["Thoughts", "Productivity", "Book Notes", "Technology", "Life", "Travel"],
}

# Blog metadata generation prompt
BLOG_METADATA_PROMPT = """Generate blog post metadata for this content. Write metadata in {language}.

Categories to choose from: {categories}

Content:
{text}

RULES:
- Title: engaging blog post title, 5-10 words, title case. Based on the topic, NOT a description of the speaker.
- Category: pick ONE from the list above
- Description: write a compelling 1-sentence blog teaser that makes readers want to click. Write about what the blog post is ABOUT, not what the speaker said. Under 160 characters.
- Tags: 3-5 keywords relevant to the topic
- Do NOT use phrases like "the author discusses" or "the speaker talks about"

Provide metadata in this exact format:
TITLE: [blog post title]
CATEGORY: [ONE category from the list]
DESCRIPTION: [blog teaser sentence]
TAGS: [keywords, comma-separated]

Return ONLY these 4 lines in this exact format, nothing else."""

# Aiden King metadata prompt (always English, blog-ready description)
AIDENKING_METADATA_PROMPT = """Generate blog post metadata for this content. The content may be in German but ALL metadata must be in ENGLISH.

Content:
{text}

RULES:
- Title: engaging English blog post title, 5-10 words, title case
- Description: write a compelling 1-sentence blog teaser that makes readers want to click — NOT a summary of what the speaker said, but what the blog post is ABOUT. Under 160 characters. In English.
- Tags: 3-5 English keywords relevant to the topic

Provide metadata in this exact format:
TITLE: [English blog post title]
DESCRIPTION: [English blog teaser sentence]
TAGS: [English keywords, comma-separated]

Return ONLY these 3 lines in this exact format, nothing else."""

# Hugo frontmatter template
HUGO_FRONTMATTER = """---
title: "{title}"
date: {date}
author: Reiner
authorLink: https://reinergaertner.de
description: "{description}"
license:
tags: {tags}
categories:
- {category}
hiddenFromHomePage: false
toc: false
autoCollapseToc: false
draft: true
---"""


# Telegram bot settings
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Weekly reflection email settings
EMAIL_ENABLED = True
EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "")
EMAIL_SMTP_PORT = 587
EMAIL_USE_SSL = False  # STARTTLS on 587
EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")


def ensure_folders_exist() -> None:
    """Create necessary folders if they don't exist."""
    TRANSCRIPTIONS_FOLDER.mkdir(parents=True, exist_ok=True)
    CALENDAR_FOLDER.mkdir(parents=True, exist_ok=True)
