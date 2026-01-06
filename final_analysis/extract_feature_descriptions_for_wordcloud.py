#!/usr/bin/env python3
"""
Extract all feature descriptions from the 6 active participants
for word cloud generation.
"""

import json
from pathlib import Path
from collections import Counter
import re

# Load participant sessions data
data_file = Path(__file__).parent / 'participant_sessions.json'
with open(data_file, 'r') as f:
    data = json.load(f)

print("=" * 100)
print("FEATURE DESCRIPTION EXTRACTION FOR WORD CLOUD")
print("=" * 100)
print()

all_descriptions = []
participant_stats = []

participants = data.get('participants', [])

for participant_data in participants:
    participant_num = participant_data.get('p_number')
    sessions = participant_data.get('sessions', [])

    participant_descriptions = []

    for session in sessions:
        regions = session.get('regions', [])

        for region in regions:
            features = region.get('features', [])

            for feature in features:
                notes = feature.get('notes', '') or ''
                if notes.strip():  # Only include non-empty notes
                    all_descriptions.append(notes)
                    participant_descriptions.append(notes)

    participant_stats.append({
        'p_number': participant_num,
        'feature_count': len(participant_descriptions),
        'descriptions': participant_descriptions
    })

    print(f"P{participant_num}: {len(participant_descriptions)} feature descriptions")

print()
print(f"Total feature descriptions: {len(all_descriptions)}")
print()

# Save all descriptions to a text file (one per line)
output_file = Path(__file__).parent / 'word cloud' / 'feature_descriptions_all.txt'
with open(output_file, 'w') as f:
    for desc in all_descriptions:
        # Clean up description - remove extra whitespace
        cleaned = ' '.join(desc.split())
        f.write(cleaned + '\n')

print(f"✓ Saved all descriptions to: {output_file}")

# Save as single blob of text (typical for word clouds)
blob_file = Path(__file__).parent / 'word cloud' / 'feature_descriptions_blob.txt'
with open(blob_file, 'w') as f:
    text = ' '.join(all_descriptions)
    # Clean up whitespace
    text = ' '.join(text.split())
    f.write(text)

print(f"✓ Saved text blob to: {blob_file}")

# Save per-participant files
per_participant_dir = Path(__file__).parent / 'word cloud' / 'feature_descriptions_by_participant'
per_participant_dir.mkdir(exist_ok=True)

for stats in participant_stats:
    p_num = stats['p_number']
    descs = stats['descriptions']

    p_file = per_participant_dir / f'P{p_num}_descriptions.txt'
    with open(p_file, 'w') as f:
        for desc in descs:
            cleaned = ' '.join(desc.split())
            f.write(cleaned + '\n')

    print(f"✓ Saved P{p_num} descriptions to: {p_file}")

print()
print("=" * 100)
print("PREVIEW OF DESCRIPTIONS (first 10)")
print("=" * 100)
print()

for i, desc in enumerate(all_descriptions[:10], 1):
    preview = desc[:100] + '...' if len(desc) > 100 else desc
    print(f"{i}. {preview}")

print()

# Generate some basic word frequency stats
print("=" * 100)
print("BASIC WORD FREQUENCY (excluding common words)")
print("=" * 100)
print()

# Common words to exclude
stopwords = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
    'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
    'to', 'was', 'will', 'with', 'this', 'but', 'they', 'have', 'had',
    'what', 'when', 'where', 'who', 'which', 'why', 'how', 'all', 'each',
    'she', 'or', 'other', 'some', 'such', 'no', 'not', 'only', 'own',
    'than', 'too', 'very', 'can', 'just', 'should', 'now'
}

# Extract all words
all_words = []
for desc in all_descriptions:
    # Convert to lowercase and extract words (letters only)
    words = re.findall(r'\b[a-z]+\b', desc.lower())
    all_words.extend(words)

# Filter out stopwords and short words
filtered_words = [w for w in all_words if w not in stopwords and len(w) > 2]

# Count frequencies
word_counts = Counter(filtered_words)

print("Top 50 most common words:")
print()

for word, count in word_counts.most_common(50):
    print(f"{word:20s} {count:4d} {'█' * (count // 2)}")

print()
print(f"Total unique words (after filtering): {len(word_counts)}")
print(f"Total words (after filtering): {len(filtered_words)}")
print()

# Save word frequencies to JSON
freq_file = Path(__file__).parent / 'word cloud' / 'word_frequencies.json'
with open(freq_file, 'w') as f:
    json.dump(dict(word_counts.most_common()), f, indent=2)

print(f"✓ Saved word frequencies to: {freq_file}")
print()
