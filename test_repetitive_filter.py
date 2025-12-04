"""Test the repetitive phrase filter."""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from transcriber import TranscriptionEngine

# Sample text with repetitive phrases (like the ZDF subtitle issue)
test_text = """Heute ist der 9. November 2025. Ich habe ungewöhnlich lange geschlafen. Jetzt ist es schon 6.40 Uhr. Normalerweise stehe ich um 5.45 Uhr auf. Ich sitze auf meinem wunderbar gemütlichen Sofa und denke darüber nach, wie ich die nächste Woche angehen möchte. Im Schlafzimmer schläft Yolanda, die in ungefähr 15 Minuten aufstehen muss, weil wir dann die Lilly nach Port Stephens fahren müssen. Dort wird sie mit einem großen Segelschiff an einer Regatta teilnehmen. Sie kommt dann abends wieder zurück. Insofern ist der Tag davon geprägt. Judy und Yolanda werden wahrscheinlich heute noch nach Sydney fahren, weil ihre Mutter nämlich gestern ins Krankenhaus gekommen ist. Sie hatte einen Herzinfarkt und wird am Montag einen weiteren Stand bekommen. Deswegen ist es sehr wichtig, dass sie nach Sydney fahren. Denn man darf auf gar keinen Fall solche Situationen unterschätzen. Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017 Untertitelung des ZDF für funk, 2017"""

engine = TranscriptionEngine()

print("=" * 80)
print("ORIGINAL TEXT:")
print("=" * 80)
print(test_text)
print(f"\nLength: {len(test_text)} chars\n")

print("=" * 80)
print("FILTERED TEXT:")
print("=" * 80)
filtered = engine._remove_repetitive_phrases(test_text)
print(filtered)
print(f"\nLength: {len(filtered)} chars")

print("\n" + "=" * 80)
print(f"Removed {len(test_text) - len(filtered)} characters of repetitive noise")
print("=" * 80)
