"""Compare granite4:3b vs granite3.3:8b for transcription cleanup."""

import time
import ollama

# Sample raw transcription (German, with fillers and no punctuation)
raw_transcription = """heute ist der 9 november 2025 äh ich habe ungewöhnlich lange geschlafen jetzt ist es schon äh 6 40 uhr normalerweise stehe ich um 5 45 uhr auf ich sitze auf meinem wunderbar gemütlichen sofa und äh denke darüber nach wie ich die nächste woche angehen möchte im schlafzimmer schläft yolanda die in ungefähr 15 minuten aufstehen muss weil wir dann die lilly nach port stephens fahren müssen dort wird sie mit einem großen segelschiff an einer regatta teilnehmen"""

cleanup_prompt = f"""You are a minimal transcription cleaner. Your ONLY job is to fix obvious errors while keeping the speaker's EXACT word choices.

DETECTED LANGUAGE: de

WHAT YOU MAY CHANGE (only these things):
1. Add punctuation (periods, commas, question marks, etc.)
2. Fix capitalization (sentence starts, proper nouns, "I")
3. Add paragraph breaks at natural pauses
4. Remove ONLY these filler words:
   - German: äh, ähm
5. Fix ONLY obvious stutters where the same word is repeated (e.g., "the the" → "the")

WHAT YOU MUST NOT CHANGE:
- Do NOT rephrase or improve the speaker's wording
- Do NOT change word choices
- Do NOT fix grammar beyond punctuation
- Do NOT remove words like "like", "you know", "actually"
- Do NOT summarize or shorten anything
- Do NOT add new words or ideas

KEEP THE ENTIRE TEXT IN THE ORIGINAL LANGUAGE: de

Your goal: Make it readable with punctuation, but preserve the speaker's authentic voice.

Transcription:
{raw_transcription}

Return ONLY the minimally cleaned text in de, no explanations."""

print("=" * 80)
print("RAW TRANSCRIPTION:")
print("=" * 80)
print(raw_transcription)
print()

# Test granite3.3:8b
print("=" * 80)
print("TESTING: granite3.3:8b (current model)")
print("=" * 80)
start = time.time()
response1 = ollama.chat(
    model="granite3.3:8b",
    messages=[{"role": "user", "content": cleanup_prompt}],
    options={"temperature": 0.3, "num_predict": 16384}
)
time1 = time.time() - start
result1 = response1["message"]["content"].strip()

print(f"Time: {time1:.2f}s")
print()
print(result1)
print()

# Test granite4:3b
print("=" * 80)
print("TESTING: granite4:3b (new model)")
print("=" * 80)
start = time.time()
response2 = ollama.chat(
    model="granite4:3b",
    messages=[{"role": "user", "content": cleanup_prompt}],
    options={"temperature": 0.3, "num_predict": 16384}
)
time2 = time.time() - start
result2 = response2["message"]["content"].strip()

print(f"Time: {time2:.2f}s")
print()
print(result2)
print()

# Comparison
print("=" * 80)
print("COMPARISON:")
print("=" * 80)
print(f"granite3.3:8b - Time: {time1:.2f}s, Length: {len(result1)} chars")
print(f"granite4:3b   - Time: {time2:.2f}s, Length: {len(result2)} chars")
print(f"Speed improvement: {((time1 - time2) / time1 * 100):.1f}%")
print()
print("Verdict:")
if time2 < time1 and len(result2) > 0:
    print("✓ granite4:3b is FASTER and produces output")
    print(f"  - {time1 - time2:.2f}s faster ({((time1 - time2) / time1 * 100):.1f}% improvement)")
else:
    print("granite3.3:8b remains competitive")
