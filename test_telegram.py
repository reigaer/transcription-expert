"""Tests for Telegram integration — edge cases and error handling."""

from unittest.mock import patch

import telegram

# --- Helper: mock _telegram_api to capture calls without hitting network ---

def _mock_api_ok(method, data):
    """Simulate successful Telegram API response."""
    return {"ok": True, "result": {"message_id": 1}}


def _mock_api_fail(method, data):
    """Simulate failed Telegram API response."""
    return {"ok": False, "description": "Bad Request"}


def _mock_api_none(method, data):
    """Simulate network failure."""
    return None


# =============================================================================
# 1. HTML escaping
# =============================================================================

class TestHtmlEscaping:
    def test_ampersand(self):
        assert telegram._escape_html("A & B") == "A &amp; B"

    def test_angle_brackets(self):
        result = telegram._escape_html("<script>alert('xss')</script>")
        assert result == "&lt;script&gt;alert('xss')&lt;/script&gt;"

    def test_mixed_special_chars(self):
        text = "if x < 5 & y > 3: print('ok')"
        result = telegram._escape_html(text)
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result
        assert "<" not in result.replace("&lt;", "").replace("&amp;", "")

    def test_already_safe_text(self):
        text = "Hello world, this is a normal note."
        assert telegram._escape_html(text) == text

    def test_german_umlauts_untouched(self):
        text = "Über die Straße läuft ein Mädchen"
        assert telegram._escape_html(text) == text

    def test_empty_string(self):
        assert telegram._escape_html("") == ""


# =============================================================================
# 2. Message formatting — mode labels
# =============================================================================

class TestFormatNote:
    def test_checkin_label(self):
        msg = telegram._format_note("text", "topic", "checkin", "neutral", "en", "1m")
        assert "CHECK-IN" in msg
        assert "CHECK-OUT" not in msg

    def test_checkout_label(self):
        msg = telegram._format_note("text", "topic", "checkout", "neutral", "en", "1m")
        assert "CHECK-OUT" in msg
        assert "CHECK-IN" not in msg

    def test_regular_note_label(self):
        msg = telegram._format_note("text", "topic", None, "neutral", "en", "1m")
        assert "AUDIO NOTE" in msg
        assert "CHECK-IN" not in msg
        assert "CHECK-OUT" not in msg

    def test_invalid_mode_falls_back_to_audio_note(self):
        msg = telegram._format_note("text", "topic", "invalid_mode", "neutral", "en", "1m")
        assert "AUDIO NOTE" in msg

    def test_empty_mode_falls_back_to_audio_note(self):
        msg = telegram._format_note("text", "topic", "", "neutral", "en", "1m")
        assert "AUDIO NOTE" in msg


# =============================================================================
# 3. Sentiment icons
# =============================================================================

class TestSentiment:
    def test_all_valid_sentiments(self):
        for sentiment in ("positive", "neutral", "reflective", "negative"):
            msg = telegram._format_note("text", "", None, sentiment, "en", "1m")
            assert sentiment in msg

    def test_unknown_sentiment_gets_default_icon(self):
        msg = telegram._format_note("text", "", None, "confused", "en", "1m")
        # Should use default icon ○ and still include the word
        assert "confused" in msg

    def test_empty_sentiment(self):
        msg = telegram._format_note("text", "", None, "", "en", "1m")
        # Should not crash
        assert "AUDIO NOTE" in msg


# =============================================================================
# 4. Metadata line
# =============================================================================

class TestMetadata:
    def test_language_uppercase(self):
        msg = telegram._format_note("text", "", None, "neutral", "de", "1m")
        assert "DE" in msg

    def test_duration_shown(self):
        msg = telegram._format_note("text", "", None, "neutral", "en", "3m 42s")
        assert "3m 42s" in msg

    def test_unknown_duration_hidden(self):
        msg = telegram._format_note("text", "", None, "neutral", "en", "unknown")
        assert "unknown" not in msg

    def test_empty_duration_hidden(self):
        msg = telegram._format_note("text", "", None, "neutral", "en", "")
        # Should not have empty duration marker
        assert msg.count("·") <= 1  # only sentiment · language at most

    def test_empty_language_hidden(self):
        msg = telegram._format_note("text", "", None, "neutral", "", "1m")
        # Language should not appear as empty uppercase
        lines = msg.split("\n")
        meta_line = lines[1]  # second line is metadata
        assert "· ·" not in meta_line  # no empty segment


# =============================================================================
# 5. Full note text included and escaped
# =============================================================================

class TestFullNoteInMessage:
    def test_full_text_present(self):
        note = "Dies ist ein Testnote über mein Projekt."
        msg = telegram._format_note(note, "", None, "neutral", "de", "1m")
        assert telegram._escape_html(note) in msg

    def test_html_in_note_escaped(self):
        note = "Use <b>bold</b> and & ampersand"
        msg = telegram._format_note(note, "", None, "neutral", "en", "1m")
        assert "&lt;b&gt;bold&lt;/b&gt;" in msg
        assert "&amp; ampersand" in msg
        # The header <b> tags should NOT be escaped
        assert "<b>" in msg

    def test_empty_text(self):
        msg = telegram._format_note("", "", None, "neutral", "en", "1m")
        # Should not crash, header still present
        assert "AUDIO NOTE" in msg


# =============================================================================
# 6. Message splitting for long notes
# =============================================================================

class TestMessageSplitting:
    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_short_message_single_call(self, mock_api):
        result = telegram._send_message("123", "short text")
        assert result is True
        assert mock_api.call_count == 1

    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_long_message_split_into_chunks(self, mock_api):
        # Create a message longer than 4096 chars
        long_text = "A" * 5000
        result = telegram._send_message("123", long_text)
        assert result is True
        assert mock_api.call_count >= 2

    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_long_message_splits_at_newlines(self, mock_api):
        # Create text with paragraphs that total > 4096
        paragraphs = ["Paragraph " + str(i) + ". " + "x" * 200 for i in range(30)]
        long_text = "\n\n".join(paragraphs)
        assert len(long_text) > 4096
        result = telegram._send_message("123", long_text)
        assert result is True
        # Each chunk should be within limit
        for call in mock_api.call_args_list:
            sent_text = call[0][1]["text"]
            assert len(sent_text) <= telegram.MAX_MESSAGE_LENGTH

    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_continued_label_on_subsequent_chunks(self, mock_api):
        long_text = "\n".join(["Line " + str(i) + " " + "x" * 200 for i in range(30)])
        telegram._send_message("123", long_text)
        # Second chunk should have "continued" label
        if mock_api.call_count > 1:
            second_text = mock_api.call_args_list[1][0][1]["text"]
            assert "continued" in second_text

    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_single_very_long_line_still_sends(self, mock_api):
        # One line with no newlines, longer than limit
        long_line = "A" * 8000
        result = telegram._send_message("123", long_line)
        assert result is True
        assert mock_api.call_count >= 1

    @patch.object(telegram, '_telegram_api')
    def test_partial_failure_returns_false(self, mock_api):
        # First chunk succeeds, second fails
        mock_api.side_effect = [
            {"ok": True, "result": {}},
            {"ok": False, "description": "error"},
        ]
        long_text = "A" * 5000
        result = telegram._send_message("123", long_text)
        assert result is False

    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_exactly_4096_chars_no_split(self, mock_api):
        text = "A" * 4096
        result = telegram._send_message("123", text)
        assert result is True
        assert mock_api.call_count == 1

    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_4097_chars_triggers_split(self, mock_api):
        text = "A" * 4097
        telegram._send_message("123", text)
        assert mock_api.call_count >= 2


# =============================================================================
# 7. Config guard — TELEGRAM_ENABLED=False
# =============================================================================

class TestDisabledConfig:
    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_disabled_returns_false_no_api_call(self, mock_api):
        with patch('config.TELEGRAM_ENABLED', False):
            result = telegram.send_note(text="hello", sentiment="neutral")
            assert result is False
            assert mock_api.call_count == 0

    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_missing_enabled_attr_returns_false(self, mock_api):
        # Temporarily remove TELEGRAM_ENABLED to test getattr fallback
        original = getattr(telegram.config, 'TELEGRAM_ENABLED', None)
        if hasattr(telegram.config, 'TELEGRAM_ENABLED'):
            delattr(telegram.config, 'TELEGRAM_ENABLED')
        try:
            result = telegram.send_note(text="hello", sentiment="neutral")
            assert result is False
        finally:
            if original is not None:
                telegram.config.TELEGRAM_ENABLED = original


# =============================================================================
# 8. Missing/invalid bot token
# =============================================================================

class TestMissingToken:
    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_empty_token_returns_false(self, mock_api):
        with patch('config.TELEGRAM_ENABLED', True), \
             patch('config.TELEGRAM_BOT_TOKEN', ""):
            result = telegram.send_note(text="hello", sentiment="neutral")
            assert result is False

    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_missing_token_attr_returns_false(self, mock_api):
        with patch('config.TELEGRAM_ENABLED', True):
            # Remove token attribute temporarily
            original = getattr(telegram.config, 'TELEGRAM_BOT_TOKEN', None)
            if hasattr(telegram.config, 'TELEGRAM_BOT_TOKEN'):
                delattr(telegram.config, 'TELEGRAM_BOT_TOKEN')
            try:
                result = telegram.send_note(text="hello", sentiment="neutral")
                assert result is False
            finally:
                if original is not None:
                    telegram.config.TELEGRAM_BOT_TOKEN = original


# =============================================================================
# 9. Chat ID discovery
# =============================================================================

class TestChatIdDiscovery:
    def test_reads_from_file(self, tmp_path):
        chat_file = tmp_path / ".telegram_chat_id"
        chat_file.write_text("12345")
        with patch.object(telegram, 'CHAT_ID_FILE', chat_file):
            assert telegram._get_chat_id() == "12345"

    def test_empty_file_triggers_discovery(self, tmp_path):
        chat_file = tmp_path / ".telegram_chat_id"
        chat_file.write_text("")
        with patch.object(telegram, 'CHAT_ID_FILE', chat_file), \
             patch.object(telegram, '_telegram_api', return_value={
                 "ok": True,
                 "result": [{"message": {"chat": {"id": 99999}}}]
             }):
            result = telegram._get_chat_id()
            assert result == "99999"

    def test_no_file_triggers_discovery(self, tmp_path):
        chat_file = tmp_path / ".telegram_chat_id_nonexistent"
        with patch.object(telegram, 'CHAT_ID_FILE', chat_file), \
             patch.object(telegram, '_telegram_api', return_value={
                 "ok": True,
                 "result": [{"message": {"chat": {"id": 77777}}}]
             }):
            result = telegram._get_chat_id()
            assert result == "77777"
            # Should save to file
            assert chat_file.read_text() == "77777"

    def test_no_updates_returns_none(self, tmp_path):
        chat_file = tmp_path / ".telegram_chat_id_none"
        with patch.object(telegram, 'CHAT_ID_FILE', chat_file), \
             patch.object(telegram, '_telegram_api', return_value={
                 "ok": True,
                 "result": []
             }):
            result = telegram._get_chat_id()
            assert result is None

    def test_api_failure_returns_none(self, tmp_path):
        chat_file = tmp_path / ".telegram_chat_id_fail"
        with patch.object(telegram, 'CHAT_ID_FILE', chat_file), \
             patch.object(telegram, '_telegram_api', return_value=None):
            result = telegram._get_chat_id()
            assert result is None

    def test_malformed_update_without_message_key(self, tmp_path):
        """Edge case: getUpdates returns update without 'message' key (e.g. edited_message)."""
        chat_file = tmp_path / ".telegram_chat_id_malformed"
        with patch.object(telegram, 'CHAT_ID_FILE', chat_file), \
             patch.object(telegram, '_telegram_api', return_value={
                 "ok": True,
                 "result": [{"update_id": 1, "edited_message": {"chat": {"id": 123}}}]
             }):
            result = telegram._get_chat_id()
            # Should handle KeyError gracefully
            assert result is None or isinstance(result, str)


# =============================================================================
# 10. Network failure handling — never crashes
# =============================================================================

class TestNetworkFailure:
    @patch.object(telegram, '_get_chat_id', return_value="123")
    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_none)
    def test_api_returns_none(self, mock_api, mock_chat, telegram_enabled):
        result = telegram.send_note(text="hello", sentiment="neutral")
        assert result is False

    @patch.object(telegram, '_get_chat_id', return_value="123")
    @patch.object(telegram, '_send_message', side_effect=Exception("Network down"))
    def test_exception_in_send_caught(self, mock_send, mock_chat, telegram_enabled):
        # Must not raise
        result = telegram.send_note(text="hello", sentiment="neutral")
        assert result is False

    @patch.object(telegram, '_get_chat_id', return_value="123")
    @patch.object(telegram, '_format_note', side_effect=Exception("Format crash"))
    def test_exception_in_format_caught(self, mock_fmt, mock_chat, telegram_enabled):
        result = telegram.send_note(text="hello", sentiment="neutral")
        assert result is False


# =============================================================================
# 11. End-to-end send_note with mocked API
# =============================================================================

class TestSendNoteE2E:
    @patch.object(telegram, '_get_chat_id', return_value="123")
    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_full_checkin_flow(self, mock_api, mock_chat, telegram_enabled):
        result = telegram.send_note(
            text="Heute fokussiere ich mich auf das API Refactoring.",
            checkin_checkout_mode="checkin",
            sentiment="positive",
            language="de",
            duration="1m 5s",
        )
        assert result is True
        sent_text = mock_api.call_args[0][1]["text"]
        assert "CHECK-IN" in sent_text
        assert "API Refactoring" in sent_text
        assert "DE" in sent_text
        assert "1m 5s" in sent_text

    @patch.object(telegram, '_get_chat_id', return_value="123")
    @patch.object(telegram, '_telegram_api', side_effect=_mock_api_ok)
    def test_full_checkout_flow(self, mock_api, mock_chat, telegram_enabled):
        result = telegram.send_note(
            text="Done with the refactor, merged the PR.",
            checkin_checkout_mode="checkout",
            sentiment="reflective",
            language="en",
            duration="2m 10s",
        )
        assert result is True
        sent_text = mock_api.call_args[0][1]["text"]
        assert "CHECK-OUT" in sent_text

    @patch.object(telegram, '_get_chat_id', return_value=None)
    def test_no_chat_id_returns_false(self, mock_chat, telegram_enabled):
        result = telegram.send_note(text="hello", sentiment="neutral")
        assert result is False


# =============================================================================
# 12. send_alert
# =============================================================================

class TestSendAlert:
    @patch.object(telegram, '_get_chat_id', return_value="123")
    @patch.object(telegram, '_send_message', return_value=True)
    def test_send_alert_delegates_to_send_message(self, mock_send, mock_chat, telegram_enabled):
        result = telegram.send_alert("test alert")
        assert result is True
        mock_send.assert_called_once_with("123", "test alert")

    @patch.object(telegram, '_send_message', return_value=True)
    def test_send_alert_disabled_returns_false(self, mock_send):
        with patch('config.TELEGRAM_ENABLED', False):
            result = telegram.send_alert("test alert")
            assert result is False
            mock_send.assert_not_called()
