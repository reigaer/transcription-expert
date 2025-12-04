"""Tests for configuration module."""

from pathlib import Path

import config


def test_paths_are_pathlib():
    """Ensure all paths are Path objects."""
    assert isinstance(config.VOICE_MEMOS_PATH, Path)
    assert isinstance(config.TRANSCRIPTIONS_FOLDER, Path)


def test_supported_formats():
    """Verify audio formats are defined."""
    assert ".m4a" in config.SUPPORTED_FORMATS
    assert ".mp3" in config.SUPPORTED_FORMATS


def test_ensure_folders_exist(tmp_path, monkeypatch):
    """Test folder creation."""
    test_folder = tmp_path / "test_transcriptions"
    monkeypatch.setattr(config, "TRANSCRIPTIONS_FOLDER", test_folder)

    config.ensure_folders_exist()
    assert test_folder.exists()
    assert test_folder.is_dir()
