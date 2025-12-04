"""Tests for transcription engine."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import transcriber


def test_load_processed_files_empty():
    """Test loading when no processed files exist."""
    engine = transcriber.TranscriptionEngine()
    assert isinstance(engine.processed_files, set)


def test_save_processed_file(tmp_path, monkeypatch):
    """Test saving processed file paths."""
    # Mock Path(__file__).parent to return tmp_path
    import transcriber

    monkeypatch.setattr(transcriber, "__file__", str(tmp_path / "transcriber.py"))

    engine = transcriber.TranscriptionEngine()
    engine._save_processed_file("/test/path.m4a")
    assert "/test/path.m4a" in engine.processed_files

    processed_file = tmp_path / ".processed_files"
    assert processed_file.exists()
    assert "/test/path.m4a" in processed_file.read_text()


def test_get_duration(tmp_path):
    """Test duration calculation with mock ffprobe."""
    engine = transcriber.TranscriptionEngine()

    mock_output = '{"format": {"duration": "125.0"}}'
    with patch("transcriber.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_output)
        duration = engine._get_duration(Path("test.m4a"))
        assert duration == "2m 5s"


def test_create_markdown(tmp_path, monkeypatch):
    """Test markdown file creation."""
    import config

    output_folder = tmp_path / "transcriptions"
    output_folder.mkdir()
    monkeypatch.setattr(config, "TRANSCRIPTIONS_FOLDER", output_folder)

    engine = transcriber.TranscriptionEngine()
    output_path = engine.create_markdown(
        text="Test transcription content.",
        language="en",
        topic="Test Topic",
        source_file=Path("recording.m4a"),
        duration="1m 30s",
    )

    assert output_path.exists()
    content = output_path.read_text()
    assert "---" in content
    assert "language: en" in content
    assert "topic: Test Topic" in content
    assert "Test transcription content." in content


def test_process_skips_processed_files(tmp_path, monkeypatch):
    """Test that already processed files are skipped."""
    monkeypatch.chdir(tmp_path)
    engine = transcriber.TranscriptionEngine()

    test_file = tmp_path / "test.m4a"
    test_file.write_bytes(b"fake audio data" * 100)

    engine.processed_files.add(str(test_file))
    result = engine.process(test_file)
    assert result is None


def test_process_skips_small_files(tmp_path):
    """Test that files below minimum size are skipped."""
    engine = transcriber.TranscriptionEngine()

    test_file = tmp_path / "tiny.m4a"
    test_file.write_bytes(b"x")

    result = engine.process(test_file)
    assert result is None
