"""File system watcher for new audio files."""

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

import config

logger = logging.getLogger(__name__)


class AudioFileHandler(FileSystemEventHandler):
    """Handles new audio file events."""

    def __init__(self, process_callback: Callable[[Path], Path | None]) -> None:
        self.process_callback = process_callback
        self.pending_files: dict[str, float] = {}
        self.lock = threading.Lock()  # Thread-safe access to pending_files

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if file_path.suffix.lower() not in config.SUPPORTED_FORMATS:
            return

        filepath_str = str(file_path)

        # Thread-safe check and add (atomic operation)
        with self.lock:
            # Ignore if already pending (iCloud triggers multiple events)
            if filepath_str in self.pending_files:
                return

            logger.info(f"Detected new file: {file_path.name}")
            self.pending_files[filepath_str] = time.time()

    def process_pending_files(self) -> None:
        """Process files that have stabilized."""
        now = time.time()
        to_process = []

        # Thread-safe iteration and modification
        with self.lock:
            for filepath, created_time in list(self.pending_files.items()):
                file_path = Path(filepath)

                if not file_path.exists():
                    del self.pending_files[filepath]
                    continue

                # Wait for file to stabilize
                elapsed = now - created_time
                if elapsed < config.STABLE_FILE_WAIT_SECONDS:
                    continue

                # Check if file size is stable
                try:
                    size = file_path.stat().st_size
                    time.sleep(0.5)
                    new_size = file_path.stat().st_size

                    if size != new_size:
                        # File still growing, wait longer
                        self.pending_files[filepath] = now
                        continue

                    to_process.append(file_path)
                    del self.pending_files[filepath]

                except Exception as e:
                    logger.error(f"Error checking file {file_path.name}: {e}")
                    del self.pending_files[filepath]

        # Process files outside the lock to avoid blocking new detections
        for file_path in to_process:
            try:
                self.process_callback(file_path)
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {e}", exc_info=True)


class AudioWatcher:
    """Watches for new audio files and triggers processing."""

    def __init__(self, process_callback: Callable[[Path], Path | None]) -> None:
        self.handler = AudioFileHandler(process_callback)
        self.observer = Observer()

    def start(self, watch_path: Path) -> None:
        """Start watching the specified directory."""
        if not watch_path.exists():
            raise FileNotFoundError(f"Watch path does not exist: {watch_path}")

        logger.info(f"Starting watcher on: {watch_path}")
        self.observer.schedule(self.handler, str(watch_path), recursive=False)
        self.observer.start()

        logger.info("Watcher started. Monitoring for new audio files...")

    def run(self) -> None:
        """Run the watcher loop."""
        try:
            while True:
                time.sleep(1)
                self.handler.process_pending_files()
        except KeyboardInterrupt:
            logger.info("Stopping watcher...")
            self.stop()

    def stop(self) -> None:
        """Stop the watcher."""
        self.observer.stop()
        self.observer.join()
        logger.info("Watcher stopped")
