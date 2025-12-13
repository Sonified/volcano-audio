#!/usr/bin/env python3
"""
Extract which participants reported hearing earthquakes and in which sessions
"""

import json
from pathlib import Path

# Load participant sessions data
data_file = Path(__file__).parent / 'participant_sessions.json'
with open(data_file, 'r') as f:
    data = json.load(f)

print("=" * 100)
print("PARTICIPANTS WHO REPORTED HEARING EARTHQUAKES")
print("=" * 100)

earthquake_mentions = []

participants = data.get('participants', [])
for participant_data in participants:
    participant_id = participant_data.get('value', '?')
    participant_num = participant_data.get('p_number', '?')
    sessions = participant_data.get('sessions', [])

    for session in sessions:
        session_num = session.get('session_number', '?')
        session_date = session.get('date', '?')
        volcano = session.get('volcano', '?')
        regions = session.get('regions', [])

        # Check for earthquake mentions in feature notes
        for region in regions:
            region_features = region.get('features', [])
            for feature in region_features:
                notes = feature.get('notes', '') or ''
                if 'earthquake' in notes.lower() or 'quake' in notes.lower():
                    earthquake_mentions.append({
                        'participant_id': participant_id,
                        'participant_num': participant_num,
                        'session_num': session_num,
                        'session_date': session_date,
                        'volcano': volcano,
                        'feature_num': feature.get('featureNumber', '?'),
                        'notes': feature.get('notes', ''),
                        'type': feature.get('type', 'Unknown'),
                        'repetition': feature.get('repetition', 'Unknown')
                    })

# Group by participant
by_participant = {}
for mention in earthquake_mentions:
    pid = mention['participant_id']
    if pid not in by_participant:
        by_participant[pid] = []
    by_participant[pid].append(mention)

# Print results
print(f"\nTotal earthquake mentions: {len(earthquake_mentions)}")
print(f"Participants who mentioned earthquakes: {len(by_participant)}")
print("\n")

for participant_id in sorted(by_participant.keys()):
    mentions = by_participant[participant_id]
    participant_num = mentions[0]['participant_num']

    print(f"\n{'─' * 100}")
    print(f"PARTICIPANT {participant_num} ({participant_id})")
    print(f"{'─' * 100}")
    print(f"Total earthquake mentions: {len(mentions)}\n")

    # Group by session
    by_session = {}
    for mention in mentions:
        session_key = f"Session {mention['session_num']} ({mention['session_date']}) - {mention['volcano']}"
        if session_key not in by_session:
            by_session[session_key] = []
        by_session[session_key].append(mention)

    for session_key in sorted(by_session.keys()):
        session_mentions = by_session[session_key]
        print(f"  {session_key}:")
        print(f"  {len(session_mentions)} earthquake feature(s)\n")

        for mention in session_mentions:
            print(f"    • Feature #{mention['feature_num']} ({mention['type']}, {mention['repetition']})")
            print(f"      Notes: \"{mention['notes']}\"")
            print()

# Print summary table
print("\n" + "=" * 100)
print("SUMMARY TABLE")
print("=" * 100)
print(f"\n{'Participant':<15} {'Sessions with Earthquakes':<50} {'Total Mentions'}")
print("─" * 100)

for participant_id in sorted(by_participant.keys()):
    mentions = by_participant[participant_id]
    participant_num = mentions[0]['participant_num']

    # Get unique sessions
    sessions = set()
    for mention in mentions:
        sessions.add(f"S{mention['session_num']} ({mention['session_date']})")

    sessions_str = ", ".join(sorted(sessions))

    print(f"P{participant_num:<14} {sessions_str:<50} {len(mentions)}")

print("\n")
