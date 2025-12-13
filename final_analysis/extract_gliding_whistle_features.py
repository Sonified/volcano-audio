#!/usr/bin/env python3
"""
Extract all features with 'glide', 'gliding', or 'whistle' mentions
and analyze their timing patterns in Hawaii local time
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Load participant sessions data
data_file = Path(__file__).parent / 'participant_sessions.json'
with open(data_file, 'r') as f:
    data = json.load(f)

print("=" * 100)
print("GLIDING/WHISTLE FEATURES ANALYSIS")
print("=" * 100)

gliding_features = []

# Process both participant sessions and expert sessions
all_participant_data = []

# Add regular participants
participants = data.get('participants', [])
for p in participants:
    all_participant_data.append(p)

# Add expert as a special participant
expert_data = data.get('expert', {})
if expert_data:
    expert_data['p_number'] = 'EXPERT'
    all_participant_data.append(expert_data)

print(f"\nProcessing {len(participants)} participants + expert (total {len(all_participant_data)})...")

for participant_data in all_participant_data:
    participant_id = participant_data.get('value', '?')
    participant_num = participant_data.get('p_number', '?')
    sessions = participant_data.get('sessions', [])

    for session in sessions:
        session_num = session.get('session_number', '?')
        session_date = session.get('date', '?')
        volcano = session.get('volcano', '?')
        regions = session.get('regions', [])

        # Check for glide/whistle mentions in feature notes
        for region in regions:
            region_features = region.get('features', [])
            for feature in region_features:
                notes = feature.get('notes', '') or ''
                notes_lower = notes.lower()

                if any(keyword in notes_lower for keyword in ['glid', 'whistl']):
                    # Get timestamp - features have featureStartTime in UTC
                    start_time_utc = feature.get('featureStartTime')

                    if not start_time_utc:
                        print(f"WARNING: P{participant_num} S{session_num} F{feature.get('featureNumber')} has no timestamp: {notes}")

                    if start_time_utc:
                        # Convert UTC timestamp to Hawaii time (UTC-10)
                        utc_dt = datetime.fromisoformat(start_time_utc.replace('Z', '+00:00'))
                        hawaii_dt = utc_dt - timedelta(hours=10)

                        gliding_features.append({
                            'participant_id': participant_id,
                            'participant_num': participant_num,
                            'session_num': session_num,
                            'session_date': session_date,
                            'volcano': volcano,
                            'feature_num': feature.get('featureNumber', '?'),
                            'notes': feature.get('notes', ''),
                            'type': feature.get('type', 'Unknown'),
                            'utc_time': utc_dt,
                            'hawaii_time': hawaii_dt,
                            'hour': hawaii_dt.hour,
                            'is_daytime': 6 <= hawaii_dt.hour < 18  # Day: 6am-6pm
                        })

# Sort by Hawaii time
gliding_features.sort(key=lambda x: x['hawaii_time'])

print(f"\nTotal gliding/whistle features found: {len(gliding_features)}")
print("\n")

# Print all instances with Hawaii local times
print("=" * 100)
print("ALL GLIDING/WHISTLE FEATURES (sorted by Hawaii local time)")
print("=" * 100)
print()

for feat in gliding_features:
    print(f"Participant P{feat['participant_num']}, Session {feat['session_num']}, Feature #{feat['feature_num']}")
    print(f"  Volcano: {feat['volcano']}")
    print(f"  Hawaii Time: {feat['hawaii_time'].strftime('%Y-%m-%d %I:%M:%S %p HST')}")
    print(f"  UTC Time: {feat['utc_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Notes: \"{feat['notes']}\"")
    print(f"  Time of day: {'DAYTIME (6am-6pm)' if feat['is_daytime'] else 'NIGHTTIME (6pm-6am)'}")
    print()

# Calculate average time
if gliding_features:
    # Convert times to seconds since midnight for averaging
    seconds_list = []
    for feat in gliding_features:
        seconds = feat['hour'] * 3600 + feat['hawaii_time'].minute * 60 + feat['hawaii_time'].second
        seconds_list.append(seconds)

    avg_seconds = sum(seconds_list) / len(seconds_list)
    avg_hour = int(avg_seconds // 3600)
    avg_minute = int((avg_seconds % 3600) // 60)
    avg_second = int(avg_seconds % 60)

    print("=" * 100)
    print("TIME ANALYSIS")
    print("=" * 100)
    print()
    print(f"Average time of occurrence: {avg_hour:02d}:{avg_minute:02d}:{avg_second:02d} HST")

    # Day vs night breakdown
    daytime_count = sum(1 for f in gliding_features if f['is_daytime'])
    nighttime_count = len(gliding_features) - daytime_count

    print()
    print(f"Daytime occurrences (6am-6pm): {daytime_count} ({daytime_count/len(gliding_features)*100:.1f}%)")
    print(f"Nighttime occurrences (6pm-6am): {nighttime_count} ({nighttime_count/len(gliding_features)*100:.1f}%)")

    if daytime_count > nighttime_count:
        print(f"\n✓ TREND: More gliding/whistle features during DAYTIME")
        if nighttime_count > 0:
            print(f"  Ratio: {daytime_count/nighttime_count:.2f}x more during day than night")
        else:
            print(f"  ALL features occurred during daytime (no nighttime occurrences)")
    elif nighttime_count > daytime_count:
        print(f"\n✓ TREND: More gliding/whistle features during NIGHTTIME")
        if daytime_count > 0:
            print(f"  Ratio: {nighttime_count/daytime_count:.2f}x more during night than day")
        else:
            print(f"  ALL features occurred during nighttime (no daytime occurrences)")
    else:
        print(f"\n✓ TREND: Equal distribution between day and night")

    # Hour distribution
    print()
    print("=" * 100)
    print("HOURLY DISTRIBUTION")
    print("=" * 100)
    print()

    hour_counts = defaultdict(int)
    for feat in gliding_features:
        hour_counts[feat['hour']] += 1

    for hour in sorted(hour_counts.keys()):
        count = hour_counts[hour]
        bar = '█' * count
        period = 'am' if hour < 12 else 'pm'
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        print(f"{display_hour:2d}{period}: {bar} ({count})")

    print()
