#!/usr/bin/env python3
"""Weekly reflection email - surfaces your thoughts for Sunday review."""

import smtplib
from collections import defaultdict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config

# Sentiment symbols (subtle, not distracting)
SENTIMENT_SYMBOLS = {
    "positive": "○",
    "neutral": "◐",
    "reflective": "◑",
    "negative": "●",
}


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown."""
    if not content.startswith("---"):
        return {}

    try:
        end = content.index("---", 3)
        frontmatter = content[3:end].strip()
        result = {}
        for line in frontmatter.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip()
        return result
    except ValueError:
        return {}


def get_first_sentences(content: str, max_chars: int = 250) -> str:
    """Extract first 2-3 sentences after frontmatter."""
    # Skip frontmatter
    if content.startswith("---"):
        try:
            end = content.index("---", 3)
            content = content[end + 3:].strip()
        except ValueError:
            pass

    # Get first ~250 chars, break at sentence end if possible
    if len(content) <= max_chars:
        return content

    excerpt = content[:max_chars]
    # Try to break at sentence end
    for punct in [". ", "! ", "? "]:
        last = excerpt.rfind(punct)
        if last > max_chars // 2:
            return excerpt[: last + 1]

    # Fall back to word boundary
    last_space = excerpt.rfind(" ")
    if last_space > max_chars // 2:
        return excerpt[:last_space] + "..."
    return excerpt + "..."


def get_week_range() -> tuple[datetime, datetime]:
    """Get Monday-Sunday of the current week."""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.replace(hour=0, minute=0, second=0), sunday.replace(hour=23, minute=59, second=59)


def collect_week_entries() -> dict[str, list[dict]]:
    """Collect all transcriptions from this week, grouped by day."""
    monday, sunday = get_week_range()
    entries_by_day = defaultdict(list)

    for file in sorted(config.TRANSCRIPTIONS_FOLDER.glob("*.md")):
        content = file.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)

        if not meta.get("date"):
            continue

        # Parse date from frontmatter
        try:
            file_date = datetime.fromisoformat(meta["date"].split("T")[0])
        except (ValueError, IndexError):
            continue

        # Check if in this week
        if not (monday.date() <= file_date.date() <= sunday.date()):
            continue

        day_name = file_date.strftime("%A")
        entries_by_day[day_name].append({
            "date": file_date,
            "sentiment": meta.get("sentiment", "neutral"),
            "topic": meta.get("topic", file.stem),
            "duration": meta.get("duration", ""),
            "excerpt": get_first_sentences(content),
            "filename": file.name,
        })

    return entries_by_day


def format_email() -> tuple[str, str, str]:
    """Generate email subject, plain text, and HTML body."""
    monday, sunday = get_week_range()
    week_str = f"{monday.strftime('%b %d')} - {sunday.strftime('%b %d')}"

    entries_by_day = collect_week_entries()

    subject = f"Your Week: {week_str}"

    # Sentiment colors (muted, not distracting)
    colors = {
        "positive": "#2d5a27",
        "neutral": "#666",
        "reflective": "#4a5568",
        "negative": "#8b4049",
    }

    # Build HTML
    html_parts = [
        '<!DOCTYPE html><html><head><meta charset="utf-8"></head>',
        '<body style="font-family: -apple-system, system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">',
        f'<h1 style="font-size: 20px; font-weight: normal; border-bottom: 2px solid #333; padding-bottom: 8px; margin-bottom: 24px;">Your Week: {week_str}</h1>',
    ]

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    plain_lines = [f"Your Week: {week_str}", "=" * 35, ""]

    for day in day_order:
        entries = entries_by_day.get(day, [])
        html_parts.append(f'<h2 style="font-size: 14px; font-weight: 600; margin: 20px 0 8px 0; color: #666;">{day}</h2>')
        plain_lines.extend([day, "─" * len(day)])

        if not entries:
            html_parts.append('<p style="color: #999; font-size: 14px; margin: 0 0 16px 0;">(no recordings)</p>')
            plain_lines.append("(no recordings)")
        else:
            for entry in sorted(entries, key=lambda x: x["date"]):
                sentiment = entry["sentiment"]
                color = colors.get(sentiment, "#666")
                symbol = SENTIMENT_SYMBOLS.get(sentiment, "◐")
                duration = f' <span style="color: #999;">({entry["duration"]})</span>' if entry["duration"] and entry["duration"] != "unknown" else ""
                duration_plain = f" ({entry['duration']})" if entry["duration"] and entry["duration"] != "unknown" else ""
                excerpt = entry["excerpt"].replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")

                # iCloud Drive link - opens web interface, user navigates to file
                icloud_url = "https://www.icloud.com/iclouddrive/"
                filename = entry["filename"]

                html_parts.append(f'''
                <div style="margin-bottom: 16px;">
                    <div style="font-size: 14px; margin-bottom: 4px;">
                        <span style="color: {color};">{symbol} {sentiment}</span>
                        <span style="color: #333;"> · {entry["topic"]}</span>{duration}
                    </div>
                    <p style="font-size: 13px; color: #555; margin: 0; padding-left: 16px; border-left: 2px solid #eee; line-height: 1.5;">
                        {excerpt}
                        <a href="{icloud_url}" title="Open iCloud Drive → Transcriptions → {filename}" style="color: #999; text-decoration: none; font-size: 12px; margin-left: 8px;">→ full note</a>
                    </p>
                </div>''')

                plain_lines.append(f"{symbol} {sentiment} · {entry['topic']}{duration_plain}")
                plain_lines.append(f"  {entry['excerpt'].replace(chr(10), ' ')}")
                plain_lines.append(f"  → {entry['filename']}")

        plain_lines.append("")

    # Reflection prompts
    html_parts.append('''
        <div style="border-top: 1px solid #ddd; margin-top: 32px; padding-top: 20px; color: #666; font-size: 14px;">
            <p style="margin: 0 0 8px 0;">What stands out?</p>
            <p style="margin: 0 0 8px 0;">What would you tell Monday-you?</p>
            <p style="margin: 0;">What do you want to carry forward?</p>
        </div>
        <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #eee; font-size: 11px; color: #999;">
            Full notes: <a href="https://www.icloud.com/iclouddrive/" style="color: #999;">iCloud Drive</a> → Transcriptions
        </div>
    </body></html>''')

    plain_lines.extend([
        "─" * 35, "",
        "What stands out?",
        "What would you tell Monday-you?",
        "What do you want to carry forward?",
        "",
        "─" * 35,
        "Full notes: Files app → iCloud Drive → Transcriptions"
    ])

    return subject, "\n".join(plain_lines), "".join(html_parts)


def send_email(subject: str, plain: str, html: str) -> bool:
    """Send multipart email via SMTP."""
    if not config.EMAIL_FROM or not config.EMAIL_PASSWORD:
        print("Email not configured. Set EMAIL_FROM and EMAIL_PASSWORD in config.py")
        print("\n" + "=" * 50)
        print(f"Subject: {subject}")
        print("=" * 50)
        print(plain)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM
    msg["To"] = config.EMAIL_TO or config.EMAIL_FROM

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        use_ssl = getattr(config, "EMAIL_USE_SSL", False)
        username = getattr(config, "EMAIL_USER", config.EMAIL_FROM)
        if use_ssl:
            with smtplib.SMTP_SSL(config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT) as server:
                server.login(username, config.EMAIL_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT) as server:
                server.starttls()
                server.login(username, config.EMAIL_PASSWORD)
                server.send_message(msg)
        print(f"Sent: {subject}")
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        print("\n" + "=" * 50)
        print(f"Subject: {subject}")
        print("=" * 50)
        print(plain)
        return False


def main():
    """Generate and send weekly reflection email."""
    subject, plain, html = format_email()

    if config.EMAIL_ENABLED:
        send_email(subject, plain, html)
    else:
        print(f"Subject: {subject}")
        print("=" * 50)
        print(plain)


if __name__ == "__main__":
    main()
