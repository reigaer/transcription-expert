"""Core transcription engine."""

import json
import logging
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import ollama
from faster_whisper import WhisperModel

import config
import telegram

logger = logging.getLogger(__name__)


class TranscriptionEngine:
    """Handles audio transcription, cleanup, and markdown generation."""

    def __init__(self) -> None:
        self.whisper_model: WhisperModel | None = None
        self.processed_files = self._load_processed_files()
        self.lock = threading.Lock()  # Thread-safe access to processed_files

    def _load_processed_files(self) -> set[str]:
        """Load set of already processed file paths."""
        processed_file = Path(__file__).parent / ".processed_files"
        if processed_file.exists():
            return set(processed_file.read_text().splitlines())
        return set()

    def _save_processed_file(self, filepath: str) -> None:
        """Mark a file as processed (atomic write)."""
        with self.lock:
            self.processed_files.add(filepath)
            processed_file = Path(__file__).parent / ".processed_files"
            # Atomic write: write to temp file then rename
            temp_file = processed_file.with_suffix(".tmp")
            temp_file.write_text("\n".join(sorted(self.processed_files)))
            temp_file.replace(processed_file)  # Atomic on POSIX systems

    def _load_whisper(self) -> None:
        """Lazy load Whisper model to conserve memory."""
        if self.whisper_model is None:
            logger.info(f"Loading Whisper model: {config.WHISPER_MODEL}")
            self.whisper_model = WhisperModel(
                config.WHISPER_MODEL,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )

    def cleanup(self) -> None:
        """Release model resources."""
        if self.whisper_model is not None:
            logger.info("Releasing Whisper model")
            del self.whisper_model
            self.whisper_model = None

    def _get_duration(self, audio_path: Path) -> str:
        """Get audio duration in 'Xm Ys' format using ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(result.stdout)
            total_seconds = float(data["format"]["duration"])
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            return f"{minutes}m {seconds}s"
        except Exception as e:
            logger.warning(f"Could not determine duration: {e}")
            return "unknown"

    def _remove_repetitive_phrases(self, text: str, min_length: int = 10, min_repeats: int = 3) -> str:
        """
        Remove phrases that repeat excessively (e.g., TV subtitles, watermarks).

        Args:
            text: Input text
            min_length: Minimum phrase length to consider (in characters)
            min_repeats: Minimum number of repetitions to trigger removal

        Returns:
            Text with repetitive phrases removed
        """
        import re

        # Use sliding window to find repeated n-grams (word sequences)
        words = text.split()

        # Try different n-gram sizes (4-10 words)
        repetitive_patterns = set()

        for n in range(4, 11):
            if n > len(words):
                continue

            ngram_counts: dict[str, int] = {}
            for i in range(len(words) - n + 1):
                ngram = ' '.join(words[i:i+n]).lower()
                if len(ngram) >= min_length:
                    ngram_counts[ngram] = ngram_counts.get(ngram, 0) + 1

            # Find n-grams that repeat too much
            for ngram, count in ngram_counts.items():
                if count >= min_repeats:
                    repetitive_patterns.add(ngram)

        if not repetitive_patterns:
            return text

        # Sort patterns by length (longest first) to avoid partial matches
        repetitive_patterns_list = sorted(repetitive_patterns, key=len, reverse=True)

        logger.warning(f"Found {len(repetitive_patterns_list)} repetitive phrase(s), removing...")

        # Remove all occurrences of repetitive patterns (case-insensitive)
        result = text
        for pattern in repetitive_patterns_list:
            # Create case-insensitive regex pattern
            pattern_regex = re.compile(re.escape(pattern), re.IGNORECASE)

            # Count occurrences before removal
            matches = pattern_regex.findall(result)
            if matches:
                logger.debug(f"Removing {len(matches)}x repetitive: '{pattern[:50]}...'")
                # Remove all occurrences
                result = pattern_regex.sub('', result)

        # Clean up extra whitespace and fragments
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'\s+([.,!?])', r'\1', result)

        # Remove trailing fragments (short repeated words/phrases at the end)
        # This catches leftover bits like "ZDF für ZDF für" after main removal
        final_words = result.split()
        if len(final_words) > 5:
            # Check last 10 words for repetition
            last_section = ' '.join(final_words[-10:]).lower() if len(final_words) >= 10 else ' '.join(final_words).lower()
            word_freq: dict[str, int] = {}
            for word in last_section.split():
                if len(word) > 2:  # Only count words longer than 2 chars
                    word_freq[word] = word_freq.get(word, 0) + 1

            # If any word appears 3+ times in the last section, truncate
            if any(count >= 3 for count in word_freq.values()):
                # Find where the repetition starts
                for i in range(len(final_words) - 10, len(final_words)):
                    if i < 0:
                        i = 0
                    section_check = ' '.join(final_words[i:]).lower()
                    section_words = section_check.split()
                    section_freq: dict[str, int] = {}
                    for word in section_words:
                        if len(word) > 2:
                            section_freq[word] = section_freq.get(word, 0) + 1
                    if any(count >= 3 for count in section_freq.values()):
                        # Truncate here
                        result = ' '.join(final_words[:i])
                        logger.debug(f"Removed trailing repetitive fragments")
                        break

        return result.strip()

    def transcribe(self, audio_path: Path) -> tuple[str, str]:
        """
        Transcribe audio and detect language.

        Returns:
            (transcription_text, language_code)
        """
        self._load_whisper()
        assert self.whisper_model is not None

        logger.info(f"Transcribing: {audio_path.name}")

        segments, info = self.whisper_model.transcribe(
            str(audio_path),
            language=None,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )

        text = " ".join(segment.text for segment in segments).strip()
        language = info.language

        # Remove repetitive phrases (TV subtitles, watermarks, etc.)
        text = self._remove_repetitive_phrases(text)

        logger.info(f"Transcription complete. Language: {language}, Length: {len(text)} chars")
        return text, language

    def cleanup_text(self, text: str, language: str) -> tuple[str, str]:
        """Clean up transcription using Ollama and extract sentiment.

        Returns:
            Tuple of (cleaned_text, sentiment)
        """
        logger.info(f"Cleaning transcription with LLM (language: {language})")

        try:
            response = ollama.chat(
                model=config.OLLAMA_MODEL,
                messages=[{"role": "user", "content": config.CLEANUP_PROMPT.format(text=text, language=language)}],
                options={"temperature": 0.1, "num_predict": 16384},
            )
            cleaned = response["message"]["content"].strip()

            # Convert literal \n strings to actual newlines
            # LLMs often return literal "\n" instead of newline characters
            cleaned = cleaned.replace('\\n', '\n')

            # Extract sentiment from the last line
            sentiment = "neutral"  # default
            lines = cleaned.strip().split('\n')
            if lines and lines[-1].upper().startswith("SENTIMENT:"):
                sentiment_line = lines[-1]
                sentiment = sentiment_line.split(":", 1)[1].strip().lower()
                # Validate sentiment is one of the expected values
                if sentiment not in ("positive", "neutral", "reflective", "negative"):
                    sentiment = "neutral"
                # Remove the sentiment line from the text
                cleaned = '\n'.join(lines[:-1]).strip()

            logger.info(f"Cleanup complete. Sentiment: {sentiment}")
            return cleaned, sentiment
        except Exception as e:
            logger.error(f"Cleanup failed: {e}. Using original text.")
            return text, "neutral"

    def generate_topic(self, text: str) -> str:
        """Generate topic title from transcription."""
        logger.info("Generating topic")

        try:
            sample = text[:1000] if len(text) > 1000 else text
            response = ollama.chat(
                model=config.OLLAMA_MODEL,
                messages=[{"role": "user", "content": config.TOPIC_PROMPT.format(text=sample)}],
                options={"temperature": 0.5, "num_predict": 50},
            )
            topic = response["message"]["content"].strip().strip("\"'")
            logger.info(f"Generated topic: {topic}")
            return topic
        except Exception as e:
            logger.error(f"Topic generation failed: {e}")
            return "Voice Memo"

    def _detect_blog_mode(self, text: str) -> bool:
        """Detect if transcription starts with blog trigger word."""
        first_words = text.lower().split()[:10]  # Check first 10 words
        # Strip punctuation from each word before checking
        return any(word.strip(".,!?;:") == config.BLOG_TRIGGER for word in first_words)

    def _detect_checkin_checkout(self, text: str) -> str | None:
        """
        Detect if transcription starts with checkin or checkout phrase.

        Returns:
            'checkin', 'checkout', or None
        """
        # Normalize text for detection
        text_lower = text.lower().strip()

        # Check for "check in" / "checkin" / "check-in" (EN/DE)
        checkin_patterns = ["check in", "checkin", "check-in", "einchecken"]
        for pattern in checkin_patterns:
            if text_lower.startswith(pattern):
                return "checkin"

        # Check for "check out" / "checkout" / "check-out" (EN/DE)
        checkout_patterns = ["check out", "checkout", "check-out", "auschecken"]
        for pattern in checkout_patterns:
            if text_lower.startswith(pattern):
                return "checkout"

        return None

    def _remove_checkin_checkout_phrase(self, text: str, mode: str) -> str:
        """Remove the checkin/checkout phrase from text."""
        text_lower = text.lower().strip()

        if mode == "checkin":
            patterns = ["check in", "checkin", "check-in", "einchecken"]
        else:
            patterns = ["check out", "checkout", "check-out", "auschecken"]

        for pattern in patterns:
            if text_lower.startswith(pattern):
                # Remove the pattern (case-insensitive) and clean up
                result = text[len(pattern):].lstrip(" .,!?;:-")
                return result

        return text

    def _remove_trigger_word(self, text: str) -> str:
        """Remove the trigger word from text."""
        words = text.split()
        # Find and remove first occurrence of trigger word (case-insensitive)
        for i, word in enumerate(words):
            if word.lower().strip(".,!?;:") == config.BLOG_TRIGGER:
                words.pop(i)
                break
        return " ".join(words).strip()

    def _generate_blog_metadata(self, text: str, language: str) -> dict[str, str | list[str]]:
        """Generate blog metadata using LLM."""
        logger.info("Generating blog metadata")

        # Get language-specific categories
        categories = config.BLOG_CATEGORIES.get(language, config.BLOG_CATEGORIES["en"])
        categories_str = ", ".join(categories)

        prompt = config.BLOG_METADATA_PROMPT.format(
            language=language, categories=categories_str, text=text[:2000]
        )

        try:
            response = ollama.chat(
                model=config.OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.5, "num_predict": 200},
            )

            # Parse line-based format
            metadata: dict[str, str | list[str]] = {
                "title": "",
                "category": "",
                "description": "",
                "tags": [],
            }

            for line in response["message"]["content"].strip().split("\n"):
                line = line.strip()
                if line.startswith("TITLE:"):
                    metadata["title"] = line[6:].strip()
                elif line.startswith("CATEGORY:"):
                    category = line[9:].strip()
                    # Validate category is in allowed list
                    if category in categories:
                        metadata["category"] = category
                    else:
                        metadata["category"] = categories[0]
                elif line.startswith("DESCRIPTION:"):
                    metadata["description"] = line[12:].strip()[:160]
                elif line.startswith("TAGS:"):
                    tags_str = line[5:].strip()
                    metadata["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

            # Ensure we have required fields
            if not metadata["title"]:
                metadata["title"] = "Untitled"
            if not metadata["category"]:
                metadata["category"] = categories[0]
            if not metadata["description"]:
                # Use first sentence as fallback
                first_sentence = text.split(".")[0][:160]
                metadata["description"] = first_sentence

            logger.info(f"Title: {metadata['title']}, Category: {metadata['category']}")
            return metadata

        except Exception as e:
            logger.error(f"Metadata generation failed: {e}")
            # Return sensible defaults
            return {
                "title": "Untitled",
                "category": categories[0],
                "description": text[:150] + "...",
                "tags": [],
            }

    def create_markdown(
        self,
        text: str,
        language: str,
        topic: str,
        source_file: Path,
        duration: str,
        blog_metadata: dict[str, str | list[str]] | None = None,
        checkin_checkout_mode: str | None = None,
        sentiment: str = "neutral",
    ) -> Path:
        """Create markdown file with frontmatter (blog or regular)."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().isoformat()

        # Build filename prefix based on mode
        if checkin_checkout_mode:
            mode_prefix = f"{date_str}_{checkin_checkout_mode}_"
        else:
            mode_prefix = f"{date_str}_"

        if blog_metadata:
            # Blog mode: Use Hugo frontmatter with _blog_ prefix
            title = str(blog_metadata["title"])
            title_safe = title.replace(" ", "_").replace("/", "_")[:60]
            filename = f"{mode_prefix}blog_{title_safe}.md"

            # Format tags as YAML array
            tags = blog_metadata.get("tags", [])
            if isinstance(tags, list):
                tags_yaml = "[" + ", ".join(f'"{tag}"' for tag in tags) + "]"
            else:
                tags_yaml = "[]"

            frontmatter = config.HUGO_FRONTMATTER.format(
                title=title,
                date=timestamp,
                description=str(blog_metadata["description"]),
                category=f'"{blog_metadata["category"]}"',
                tags=tags_yaml,
            )
        else:
            # Regular note mode: Use simple frontmatter
            topic_safe = topic.replace(" ", "_").replace("/", "_")[:60]
            filename = f"{mode_prefix}{topic_safe}.md"

            frontmatter = f"""---
date: {timestamp}
sentiment: {sentiment}
language: {language}
topic: {topic}
source_file: {source_file.name}
duration: {duration}
---"""

        # Create output path and handle duplicates
        output_path = config.TRANSCRIPTIONS_FOLDER / filename
        counter = 1
        while output_path.exists():
            base = filename.rsplit(".", 1)[0]
            filename = f"{base}_{counter}.md"
            output_path = config.TRANSCRIPTIONS_FOLDER / filename
            counter += 1

        # Write file
        content = f"{frontmatter}\n\n{text}\n"
        output_path.write_text(content, encoding="utf-8")
        logger.info(f"Saved: {output_path.name}")
        return output_path

    def process(self, audio_path: Path) -> Path | None:
        """
        Main processing pipeline.

        Returns:
            Path to created markdown file, or None if failed/skipped.
        """
        # Thread-safe check if already processed
        with self.lock:
            if str(audio_path) in self.processed_files:
                logger.info(f"Already processed: {audio_path.name}")
                return None

        if audio_path.stat().st_size < config.MIN_FILE_SIZE_BYTES:
            logger.warning(f"File too small: {audio_path.name}")
            return None

        try:
            logger.info(f"Processing: {audio_path.name}")

            # Transcribe audio
            duration = self._get_duration(audio_path)
            text, language = self.transcribe(audio_path)

            if not text:
                logger.warning(f"Empty transcription: {audio_path.name}")
                return None

            # Detect checkin/checkout mode (before other processing)
            checkin_checkout_mode = self._detect_checkin_checkout(text)
            if checkin_checkout_mode:
                logger.info(f"{checkin_checkout_mode.capitalize()} mode detected")
                text = self._remove_checkin_checkout_phrase(text, checkin_checkout_mode)

            # Detect blog mode
            is_blog = self._detect_blog_mode(text)

            if is_blog:
                logger.info(f"Blog mode detected (language: {language})")
                # Remove trigger word before cleanup
                text = self._remove_trigger_word(text)

            # Clean up transcription and extract sentiment
            cleaned_text, sentiment = self.cleanup_text(text, language)

            # Generate metadata based on mode
            if is_blog:
                # Blog mode: Generate Hugo frontmatter metadata
                blog_metadata = self._generate_blog_metadata(cleaned_text, language)
                topic = str(blog_metadata.get("title", "Blog Post"))
                output_path = self.create_markdown(
                    cleaned_text, language, "", audio_path, duration, blog_metadata,
                    checkin_checkout_mode=checkin_checkout_mode, sentiment=sentiment
                )
            else:
                # Regular mode: Generate simple topic
                topic = self.generate_topic(cleaned_text)
                output_path = self.create_markdown(
                    cleaned_text, language, topic, audio_path, duration,
                    checkin_checkout_mode=checkin_checkout_mode, sentiment=sentiment
                )

            # Send to Telegram
            telegram.send_note(
                text=cleaned_text,
                topic=topic,
                checkin_checkout_mode=checkin_checkout_mode,
                sentiment=sentiment,
                language=language,
                duration=duration,
            )

            self._save_processed_file(str(audio_path))
            logger.info(f"✓ Successfully processed: {audio_path.name}")
            return output_path

        except Exception as e:
            logger.error(f"Error processing {audio_path.name}: {e}", exc_info=True)
            return None
