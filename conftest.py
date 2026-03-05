"""Shared test fixtures."""

from unittest.mock import patch

import pytest


@pytest.fixture()
def telegram_enabled():
    """Enable Telegram with a fake token for testing."""
    with patch("config.TELEGRAM_ENABLED", True), \
         patch("config.TELEGRAM_BOT_TOKEN", "fake_token"):
        yield
