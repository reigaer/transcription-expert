"""Tests for health_check module."""

import time
from unittest.mock import MagicMock, patch

import health_check


class TestServiceRunning:
    def test_service_running(self):
        mock_result = MagicMock(
            returncode=0,
            stdout="123\t0\tcom.transcription-expert\n",
        )
        with patch("subprocess.run", return_value=mock_result):
            ok, detail = health_check.check_service_running()
            assert ok is True
            assert "123" in detail

    def test_service_down(self):
        mock_result = MagicMock(
            returncode=0,
            stdout="-\t3\tcom.transcription-expert\n",
        )
        with patch("subprocess.run", return_value=mock_result):
            ok, detail = health_check.check_service_running()
            assert ok is False
            assert "exit code 3" in detail

    def test_service_not_loaded(self):
        mock_result = MagicMock(returncode=3, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            ok, detail = health_check.check_service_running()
            assert ok is False
            assert "not loaded" in detail


class TestLastActivity:
    def test_last_activity_recent(self, tmp_path):
        pf = tmp_path / ".processed_files"
        pf.write_text("file1.m4a")
        with patch.object(health_check, "PROCESSED_FILES", pf):
            ok, detail = health_check.check_last_activity()
            assert ok is True

    def test_last_activity_stale(self, tmp_path):
        pf = tmp_path / ".processed_files"
        pf.write_text("file1.m4a")
        # Set mtime to 48 hours ago
        old_time = time.time() - (48 * 3600)
        import os
        os.utime(pf, (old_time, old_time))

        # Create a fake voice memos dir with a pending file
        voice_dir = tmp_path / "voice_memos"
        voice_dir.mkdir()
        (voice_dir / "recording.m4a").write_text("audio")

        with patch.object(health_check, "PROCESSED_FILES", pf), \
             patch.object(health_check.config, "VOICE_MEMOS_PATH", voice_dir):
            ok, detail = health_check.check_last_activity()
            assert ok is False
            assert "Stale" in detail
            assert "1 files waiting" in detail

    def test_stale_but_no_pending_files(self, tmp_path):
        pf = tmp_path / ".processed_files"
        pf.write_text("file1.m4a")
        old_time = time.time() - (48 * 3600)
        import os
        os.utime(pf, (old_time, old_time))

        voice_dir = tmp_path / "voice_memos"
        voice_dir.mkdir()  # empty directory

        with patch.object(health_check, "PROCESSED_FILES", pf), \
             patch.object(health_check.config, "VOICE_MEMOS_PATH", voice_dir):
            ok, detail = health_check.check_last_activity()
            assert ok is True
            assert "Idle" in detail

    def test_no_processed_files(self, tmp_path):
        pf = tmp_path / ".processed_files_nonexistent"
        with patch.object(health_check, "PROCESSED_FILES", pf):
            ok, detail = health_check.check_last_activity()
            assert ok is True


class TestRecentErrors:
    def test_no_errors(self, tmp_path):
        log = tmp_path / "transcription.log"
        log.write_text("INFO: all good\nINFO: processing file\n")
        with patch.object(health_check, "LOG_FILE", log):
            ok, detail = health_check.check_recent_errors()
            assert ok is True
            assert "0 errors" in detail

    def test_error_spike(self, tmp_path):
        log = tmp_path / "transcription.log"
        lines = ["ERROR: something broke\n"] * 5 + ["INFO: ok\n"] * 5
        log.write_text("".join(lines))
        with patch.object(health_check, "LOG_FILE", log):
            ok, detail = health_check.check_recent_errors()
            assert ok is False
            assert "5 errors" in detail

    def test_below_threshold(self, tmp_path):
        log = tmp_path / "transcription.log"
        lines = ["ERROR: minor\n"] * 2 + ["INFO: ok\n"] * 10
        log.write_text("".join(lines))
        with patch.object(health_check, "LOG_FILE", log):
            ok, detail = health_check.check_recent_errors()
            assert ok is True

    def test_no_log_file(self, tmp_path):
        log = tmp_path / "nonexistent.log"
        with patch.object(health_check, "LOG_FILE", log):
            ok, detail = health_check.check_recent_errors()
            assert ok is True


class TestFormatAlert:
    def test_format_alert_html(self):
        checks = [
            ("Service", False, "DOWN (exit code 1)"),
            ("Activity", True, "Last activity: 2h ago"),
            ("Errors", False, "5 errors in last 100 lines"),
        ]
        result = health_check.format_alert(checks)
        assert "ALERT" in result
        assert "\u274c" in result  # ❌
        assert "\u2705" in result  # ✅
        assert "DOWN" in result
        assert "5 errors" in result


class TestMain:
    @patch.object(health_check.telegram, "send_alert")
    @patch.object(health_check, "check_recent_errors", return_value=(True, "0 errors"))
    @patch.object(health_check, "check_last_activity", return_value=(True, "Recent"))
    @patch.object(health_check, "check_service_running", return_value=(True, "Running"))
    def test_all_healthy_no_alert(self, mock_svc, mock_act, mock_err, mock_send):
        health_check.main()
        mock_send.assert_not_called()

    @patch.object(health_check.telegram, "send_alert")
    @patch.object(health_check, "check_recent_errors", return_value=(True, "0 errors"))
    @patch.object(health_check, "check_last_activity", return_value=(True, "Recent"))
    @patch.object(health_check, "check_service_running", return_value=(False, "DOWN"))
    def test_alert_sent_on_failure(self, mock_svc, mock_act, mock_err, mock_send):
        health_check.main()
        mock_send.assert_called_once()
        alert_text = mock_send.call_args[0][0]
        assert "ALERT" in alert_text
        assert "DOWN" in alert_text
