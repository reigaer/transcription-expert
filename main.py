#!/usr/bin/env python3
"""Automatic voice memo transcription service."""

import logging
import sys
from logging.handlers import RotatingFileHandler

import config
import transcriber
import watcher


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                "transcription.log",
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=2,
            ),
        ],
    )


def main() -> None:
    """Run the transcription service."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=== Transcription Expert Starting ===")
    logger.info(f"Whisper model: {config.WHISPER_MODEL}")
    logger.info(f"Cleanup model: {config.OLLAMA_MODEL}")
    logger.info(f"Watching: {config.VOICE_MEMOS_PATH}")
    logger.info(f"Output: {config.TRANSCRIPTIONS_FOLDER}")

    # Ensure folders exist
    config.ensure_folders_exist()

    # Initialize transcription engine
    engine = transcriber.TranscriptionEngine()

    # Create watcher with transcription callback
    audio_watcher = watcher.AudioWatcher(engine.process)

    try:
        audio_watcher.start(config.VOICE_MEMOS_PATH)
        audio_watcher.run()
    except FileNotFoundError:
        logger.error(f"Voice Memos folder not found: {config.VOICE_MEMOS_PATH}")
        logger.error("Please check the path in config.py")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        engine.cleanup()


if __name__ == "__main__":
    main()
