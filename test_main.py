"""Tests for main application."""

from unittest.mock import MagicMock, patch

import main


def test_setup_logging():
    """Test logging configuration."""
    main.setup_logging()
    # Just verify it doesn't crash


@patch("main.watcher.AudioWatcher")
@patch("main.transcriber.TranscriptionEngine")
@patch("main.config.ensure_folders_exist")
def test_main_initialization(mock_ensure, mock_engine, mock_watcher, tmp_path, monkeypatch):
    """Test main function initialization."""
    import config

    # Set up mock paths
    monkeypatch.setattr(config, "VOICE_MEMOS_PATH", tmp_path / "voice_memos")
    config.VOICE_MEMOS_PATH.mkdir()

    # Mock watcher to avoid running forever
    watcher_instance = MagicMock()
    mock_watcher.return_value = watcher_instance
    watcher_instance.run.side_effect = KeyboardInterrupt

    # Run main
    try:
        main.main()
    except SystemExit:
        pass

    # Verify initialization calls
    mock_ensure.assert_called_once()
    mock_engine.assert_called_once()
    mock_watcher.assert_called_once()
    watcher_instance.start.assert_called_once()
