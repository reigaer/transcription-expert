"""Test paragraph formatting with the updated cleanup prompt."""

import ollama
from config import CLEANUP_PROMPT

# Sample transcription with multiple topics (should create paragraphs)
raw_transcription = """heute ist der 9 november 2025 äh ich habe ungewöhnlich lange geschlafen jetzt ist es schon äh 6 40 uhr normalerweise stehe ich um 5 45 uhr auf ich sitze auf meinem wunderbar gemütlichen sofa und äh denke darüber nach wie ich die nächste woche angehen möchte im schlafzimmer schläft yolanda die in ungefähr 15 minuten aufstehen muss weil wir dann die lilly nach port stephens fahren müssen dort wird sie mit einem großen segelschiff an einer regatta teilnehmen das wetter sieht gut aus und ich freue mich sehr darauf äh die nächste woche wird sehr intensiv werden ich habe mehrere wichtige meetings geplant und muss auch noch einige projekte abschließen außerdem möchte ich endlich mit dem neuen buch anfangen das ich mir letzte woche gekauft habe"""

# Format the prompt
cleanup_prompt = CLEANUP_PROMPT.format(language="de", text=raw_transcription)

print("=" * 80)
print("TESTING PARAGRAPH FORMATTING WITH granite3.3:8b")
print("=" * 80)
print()

response = ollama.chat(
    model="granite3.3:8b",
    messages=[{"role": "user", "content": cleanup_prompt}],
    options={"temperature": 0.3, "num_predict": 16384}
)

result = response["message"]["content"].strip()

# Apply the fix: convert literal \n to actual newlines
result = result.replace('\\n', '\n')

print("CLEANED OUTPUT:")
print("=" * 80)
print(result)
print()
print("=" * 80)

# Count actual newlines
actual_breaks = result.count('\n\n')

print(f"Actual paragraph breaks (\\n\\n): {actual_breaks}")

if actual_breaks > 0:
    print(f"✓ SUCCESS: Found {actual_breaks} paragraph breaks with blank lines")
    paragraphs = [p.strip() for p in result.split('\n\n') if p.strip()]
    print(f"✓ Total paragraphs: {len(paragraphs)}")
else:
    print("✗ ISSUE: No actual paragraph breaks detected")

# Show each paragraph separately
print()
print("PARAGRAPHS (separated):")
print("=" * 80)
for i, para in enumerate(result.split('\n\n'), 1):
    if para.strip():
        print(f"[Paragraph {i}]")
        print(para.strip())
        print()
