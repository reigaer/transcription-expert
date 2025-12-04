"""Tests for file watcher."""

import time
from pathlib import Path
from unittest.mock import MagicMock

import watcher


def test_audio_file_handler_ignores_directories(tmp_path):
    """Test that directory creation events are ignored."""
    callback = MagicMock()
    handler = watcher.AudioFileHandler(callback)

    event = MagicMock(is_directory=True, src_path=str(tmp_path / "subdir"))
    handler.on_created(event)

    assert len(handler.pending_files) == 0


def test_audio_file_handler_ignores_unsupported_formats(tmp_path):
    """Test that non-audio files are ignored."""
    callback = MagicMock()
    handler = watcher.AudioFileHandler(callback)

    test_file = tmp_path / "document.txt"
    test_file.write_text("not audio")

    event = MagicMock(is_directory=False, src_path=str(test_file))
    handler.on_created(event)

    assert len(handler.pending_files) == 0


def test_audio_file_handler_detects_supported_formats(tmp_path):
    """Test that supported audio formats are detected."""
    callback = MagicMock()
    handler = watcher.AudioFileHandler(callback)

    test_file = tmp_path / "recording.m4a"
    test_file.write_bytes(b"fake audio")

    event = MagicMock(is_directory=False, src_path=str(test_file))
    handler.on_created(event)

    assert str(test_file) in handler.pending_files


def test_audio_file_handler_processes_stable_files(tmp_path):
    """Test that stable files are processed."""
    callback = MagicMock()
    handler = watcher.AudioFileHandler(callback)

    test_file = tmp_path / "recording.m4a"
    test_file.write_bytes(b"fake audio data" * 100)

    # Add file to pending
    handler.pending_files[str(test_file)] = time.time() - 10

    # Process pending files
    handler.process_pending_files()

    # Should have called callback
    callback.assert_called_once_with(test_file)
    assert str(test_file) not in handler.pending_files


def test_audio_file_handler_waits_for_unstable_files(tmp_path):
    """Test that recently created files are not processed immediately."""
    callback = MagicMock()
    handler = watcher.AudioFileHandler(callback)

    test_file = tmp_path / "recording.m4a"
    test_file.write_bytes(b"fake audio data" * 100)

    # Add file just now
    handler.pending_files[str(test_file)] = time.time()

    # Process pending files
    handler.process_pending_files()

    # Should NOT have called callback yet
    callback.assert_not_called()
    assert str(test_file) in handler.pending_files


def test_audio_watcher_initialization():
    """Test AudioWatcher initialization."""
    callback = MagicMock()
    audio_watcher = watcher.AudioWatcher(callback)

    assert audio_watcher.handler is not None
    assert audio_watcher.observer is not None


def test_audio_watcher_start_requires_valid_path():
    """Test that AudioWatcher requires a valid path."""
    callback = MagicMock()
    audio_watcher = watcher.AudioWatcher(callback)

    try:
        audio_watcher.start(Path("/nonexistent/path"))
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass
