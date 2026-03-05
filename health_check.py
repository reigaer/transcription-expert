#!/usr/bin/env python3
"""Health check for the transcription service — alerts via Telegram only when unhealthy."""

import logging
import subprocess
import time
from pathlib import Path

import config
import telegram

logger = logging.getLogger(__name__)

SERVICE_LABEL = "com.transcription-expert"
PROCESSED_FILES = Path(__file__).parent / ".processed_files"
LOG_FILE = Path(__file__).parent / "transcription.log"

# Configurable thresholds
STALE_THRESHOLD_HOURS = 24
ERROR_THRESHOLD = 3
ERROR_WINDOW_LINES = 100


def check_service_running() -> tuple[bool, str]:
    """Check launchctl for service PID. Returns (alive, detail)."""
    try:
        result = subprocess.run(
            ["launchctl", "list", SERVICE_LABEL],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return False, "DOWN (not loaded)"

        # Parse output: first column is PID (or "-" if not running)
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and parts[2] == SERVICE_LABEL:
                pid = parts[0]
                exit_code = parts[1]
                if pid == "-" or pid == "":
                    return False, f"DOWN (exit code {exit_code})"
                return True, f"Running (PID {pid})"

        # Single-service output (just the header + info)
        return True, "Running"
    except Exception as e:
        return False, f"Check failed: {e}"


def check_last_activity() -> tuple[bool, str]:
    """Check .processed_files mtime. Returns (ok, detail)."""
    if not PROCESSED_FILES.exists():
        return True, "No processed files yet"

    mtime = PROCESSED_FILES.stat().st_mtime
    age_hours = (time.time() - mtime) / 3600

    if age_hours <= STALE_THRESHOLD_HOURS:
        return True, f"Last activity: {age_hours:.0f}h ago"

    # Only alert if there are unprocessed voice memos waiting
    voice_memos = config.VOICE_MEMOS_PATH
    if voice_memos.exists():
        processed = set()
        if PROCESSED_FILES.exists():
            processed = set(PROCESSED_FILES.read_text().splitlines())
        pending = [f for f in voice_memos.iterdir()
                   if f.suffix in config.SUPPORTED_FORMATS
                   and str(f) not in processed]
        if pending:
            return False, f"Stale: {age_hours:.0f}h ago ({len(pending)} files waiting)"

    return True, f"Idle: {age_hours:.0f}h ago (no pending files)"


def check_recent_errors() -> tuple[bool, str]:
    """Count ERROR lines in last N log lines. Returns (ok, detail)."""
    if not LOG_FILE.exists():
        return True, "No log file"

    try:
        lines = LOG_FILE.read_text().splitlines()
        recent = lines[-ERROR_WINDOW_LINES:]
        error_count = sum(1 for line in recent if "ERROR" in line)

        if error_count >= ERROR_THRESHOLD:
            return False, f"{error_count} errors in last {ERROR_WINDOW_LINES} lines"
        return True, f"{error_count} errors"
    except Exception as e:
        return False, f"Log check failed: {e}"


def format_alert(checks: list[tuple[str, bool, str]]) -> str:
    """Format HTML alert message from failed checks."""
    lines = ["<b>\u26a0\ufe0f ALERT: Transcription Service</b>", ""]
    for name, ok, detail in checks:
        status = "\u2705" if ok else "\u274c"
        lines.append(f"{status} {name}: {detail}")
    return "\n".join(lines)


def main():
    """Run all checks. Send Telegram alert only if any fail."""
    checks = [
        ("Service", *check_service_running()),
        ("Activity", *check_last_activity()),
        ("Errors", *check_recent_errors()),
    ]

    if all(ok for _, ok, _ in checks):
        return  # Silent exit when healthy

    message = format_alert(checks)
    telegram.send_alert(message)


if __name__ == "__main__":
    main()
