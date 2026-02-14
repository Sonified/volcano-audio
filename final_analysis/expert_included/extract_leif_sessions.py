#!/usr/bin/env python3
"""
Extract ALL of Leif's session data (17 complete sessions)
Focus on session-level mood pre-post shifts, particularly:
- Connected (to nature during session)
- Calm
- Focused
- Wonder

Then look for positive trends to potentially combine with participant data.
"""

import json
from pathlib import Path
from datetime import datetime

# Leif's participant ID
LEIF_ID = 'R_79bBz3856cnKDLj'

# Load Qualtrics export
export_path = Path(__file__).parent.parent.parent / 'Qualtrics' / 'Downloaded_Data' / 'qualtrics_export_2025-12-12_10-20-36.json'

print(f"Loading: {export_path}\n")

with open(export_path, 'r') as f:
    data = json.load(f)

# Find all of Leif's responses
leif_sessions = []

for response in data['responses']:
    values = response.get('values', {})
    session_tracking = values.get('SessionTracking')

    if not session_tracking:
        continue

    try:
        st_data = json.loads(session_tracking)
        participant_id = st_data.get('participantId')

        if participant_id == LEIF_ID:
            # Check for timeout
            timed_out = (
                st_data.get('sessionTimedOut', False) or
                st_data.get('workflowFlags', {}).get('study_session_timed_out', False)
            )

            # Skip timeout sessions (consistent with participant analysis)
            if timed_out:
                continue

            # Extract mood surveys (QID5 = PRE, QID12 = POST)
            # Items: 1=Calm, 2=Energized, 3=Connected, 4=Nervous, 5=Focused, 6=Wonder
            pre_mood = {
                'calm': values.get('QID5_1'),
                'energized': values.get('QID5_2'),
                'connected': values.get('QID5_3'),
                'nervous': values.get('QID5_4'),
                'focused': values.get('QID5_5'),
                'wonder': values.get('QID5_6')
            }

            post_mood = {
                'calm': values.get('QID12_1'),
                'energized': values.get('QID12_2'),
                'connected': values.get('QID12_3'),
                'nervous': values.get('QID12_4'),
                'focused': values.get('QID12_5'),
                'wonder': values.get('QID12_6')
            }

            # Extract AWE-SF if present (QID13_1 through QID13_12)
            awesf_items = {}
            for i in range(1, 13):
                val = values.get(f'QID13_{i}')
                if val is not None:
                    awesf_items[i] = val

            # Extract feature count
            regions = st_data.get('regions', [])
            feature_count = sum(len(region.get('features', [])) for region in regions)

            # Extract volcano
            volcano = st_data.get('volcano', 'Unknown')

            session = {
                'responseId': response.get('responseId'),
                'sessionId': st_data.get('sessionId'),
                'date': values.get('startDate', ''),
                'volcano': volcano,
                'feature_count': feature_count,
                'region_count': len(regions),
                'pre_mood': pre_mood,
                'post_mood': post_mood,
                'awesf': awesf_items if awesf_items else None
            }

            leif_sessions.append(session)

    except Exception as e:
        print(f"Error processing response: {e}")
        continue

# Sort by date
leif_sessions.sort(key=lambda s: s['date'])

# Calculate changes
for session in leif_sessions:
    session['mood_changes'] = {}
    for item in ['calm', 'energized', 'connected', 'nervous', 'focused', 'wonder']:
        pre = session['pre_mood'].get(item)
        post = session['post_mood'].get(item)
        if pre is not None and post is not None:
            session['mood_changes'][item] = post - pre
        else:
            session['mood_changes'][item] = None

print("=" * 100)
print(f"LEIF'S SESSION DATA ({len(leif_sessions)} complete sessions)")
print("=" * 100)
print()

# Print session-by-session breakdown
for i, s in enumerate(leif_sessions, 1):
    date = s['date'][:10] if s['date'] else 'Unknown'
    print(f"Session {i}: {date} - {s['volcano']}")
    print(f"  Features: {s['feature_count']}, Regions: {s['region_count']}")
    print(f"  Mood Changes (Post - Pre):")

    for item in ['calm', 'energized', 'connected', 'nervous', 'focused', 'wonder']:
        change = s['mood_changes'].get(item)
        if change is not None:
            sign = '+' if change > 0 else ''
            print(f"    {item.capitalize():12} {sign}{change}")
        else:
            print(f"    {item.capitalize():12} (missing data)")

    if s['awesf']:
        avg_awesf = sum(s['awesf'].values()) / len(s['awesf'])
        print(f"  AWE-SF: {avg_awesf:.2f} average across {len(s['awesf'])} items")

    print()

# Aggregate statistics
print("=" * 100)
print("AGGREGATE MOOD SHIFTS ACROSS ALL SESSIONS")
print("=" * 100)
print()

for item in ['calm', 'energized', 'connected', 'nervous', 'focused', 'wonder']:
    changes = [s['mood_changes'][item] for s in leif_sessions if s['mood_changes'].get(item) is not None]

    if not changes:
        print(f"{item.capitalize():12} No data")
        continue

    avg_change = sum(changes) / len(changes)
    positive_count = sum(1 for c in changes if c > 0)
    negative_count = sum(1 for c in changes if c < 0)
    zero_count = sum(1 for c in changes if c == 0)

    print(f"{item.capitalize():12}")
    print(f"  Average change: {avg_change:+.2f}")
    print(f"  Positive shifts: {positive_count} ({100*positive_count/len(changes):.1f}%)")
    print(f"  Negative shifts: {negative_count} ({100*negative_count/len(changes):.1f}%)")
    print(f"  No change:       {zero_count} ({100*zero_count/len(changes):.1f}%)")
    print()

# Save to JSON for further analysis
output_path = Path(__file__).parent / 'leif_sessions.json'
with open(output_path, 'w') as f:
    json.dump(leif_sessions, f, indent=2)

print(f"Saved detailed data to: {output_path}")
