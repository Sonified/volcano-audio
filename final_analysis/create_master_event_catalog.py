#!/usr/bin/env python3
"""
Create master event catalog CSV from participant_sessions.json
and expert data from Qualtrics export.

Outputs:
  - master_event_catalog_participants.csv  (participants only)
  - master_event_catalog_expert.csv        (expert/Leif only)
  - master_event_catalog_combined.csv      (both)

Each row = one feature/event marking.
"""

import json
import csv
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from frequency_correction import correct_feature_frequencies

LEIF_ID = 'R_79bBz3856cnKDLj'

FIELDNAMES = [
    "Participant", "ParticipantID", "SessionNumber", "SessionDate",
    "Volcano", "Station", "DataDuration_hrs",
    "RegionNumber", "RegionStartTime", "RegionEndTime",
    "FeatureNumber", "FeatureStartTime", "FeatureEndTime",
    "LowFreq_Hz", "HighFreq_Hz",
    "Type", "Repetition", "SpeedFactor", "NumberOfEvents",
    "Notes",
]


def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)


def flatten_participant_data(data):
    """Flatten participant_sessions.json into flat rows."""
    rows = []
    for participant in data["participants"]:
        p_num = participant["p_number"]
        p_id = participant["value"]

        for session in participant["sessions"]:
            for region in session.get("regions", []):
                for feature in region.get("features", []):
                    rows.append({
                        "Participant": f"P{p_num}",
                        "ParticipantID": p_id,
                        "SessionNumber": session.get("session_number", ""),
                        "SessionDate": session.get("date", ""),
                        "Volcano": session.get("volcano", ""),
                        "Station": session.get("station", ""),
                        "DataDuration_hrs": session.get("duration", ""),
                        "RegionNumber": region.get("regionNumber", ""),
                        "RegionStartTime": region.get("regionStartTime", ""),
                        "RegionEndTime": region.get("regionEndTime", ""),
                        "FeatureNumber": feature.get("featureNumber", ""),
                        "FeatureStartTime": feature.get("featureStartTime", ""),
                        "FeatureEndTime": feature.get("featureEndTime", ""),
                        "LowFreq_Hz": feature.get("lowFreq", ""),
                        "HighFreq_Hz": feature.get("highFreq", ""),
                        "Type": feature.get("type", ""),
                        "Repetition": feature.get("repetition", ""),
                        "SpeedFactor": feature.get("speedFactor", ""),
                        "NumberOfEvents": feature.get("numberOfEvents", ""),
                        "Notes": feature.get("notes", ""),
                    })
    return rows


def extract_expert_from_qualtrics(export_path):
    """Extract expert (Leif) features directly from Qualtrics export."""
    data = load_json(export_path)
    sessions = []

    for response in data.get('responses', []):
        values = response.get('values', {})
        st = values.get('SessionTracking')
        if not st:
            continue

        try:
            st_data = json.loads(st)
        except json.JSONDecodeError:
            continue

        if st_data.get('participantId') != LEIF_ID:
            continue

        # Skip timeouts
        timed_out = (
            st_data.get('sessionTimedOut', False) or
            st_data.get('workflowFlags', {}).get('study_session_timed_out', False)
        )
        if timed_out:
            continue

        # Extract volcano/station from tracking events
        volcano = st_data.get('volcano', 'Unknown')
        station = ''
        duration = None
        tracking_events = st_data.get('tracking', {}).get('events', [])
        for event in tracking_events:
            if event.get('type') == 'fetch_data':
                fetch = event.get('data', {})
                volcano = fetch.get('volcano', volcano)
                station = fetch.get('station', '')
                duration = fetch.get('duration')

        uses_corrected = st_data.get('usesCorrectedLogFormula', False)
        regions = st_data.get('regions', [])

        sessions.append({
            'date': values.get('startDate', '')[:10],
            'volcano': volcano,
            'station': station,
            'duration': duration,
            'uses_corrected': uses_corrected,
            'regions': regions,
        })

    # Sort by date, assign session numbers
    sessions.sort(key=lambda s: s['date'])

    rows = []
    for session_num, session in enumerate(sessions, 1):
        for region in session['regions']:
            for feature in region.get('features', []):
                # Skip deleted/corrupted features
                if feature.get('featureStartTime') is None or feature.get('featureEndTime') is None:
                    continue
                if feature.get('featureStartTime') == feature.get('featureEndTime'):
                    continue

                # Apply frequency correction if needed
                if not session['uses_corrected']:
                    feature = correct_feature_frequencies(feature, session['uses_corrected'])

                rows.append({
                    "Participant": "Expert",
                    "ParticipantID": LEIF_ID,
                    "SessionNumber": session_num,
                    "SessionDate": session['date'],
                    "Volcano": session['volcano'],
                    "Station": session['station'],
                    "DataDuration_hrs": session['duration'] or "",
                    "RegionNumber": region.get("regionNumber", ""),
                    "RegionStartTime": region.get("regionStartTime", ""),
                    "RegionEndTime": region.get("regionEndTime", ""),
                    "FeatureNumber": feature.get("featureNumber", ""),
                    "FeatureStartTime": feature.get("featureStartTime", ""),
                    "FeatureEndTime": feature.get("featureEndTime", ""),
                    "LowFreq_Hz": feature.get("lowFreq", ""),
                    "HighFreq_Hz": feature.get("highFreq", ""),
                    "Type": feature.get("type", ""),
                    "Repetition": feature.get("repetition", ""),
                    "SpeedFactor": feature.get("speedFactor", ""),
                    "NumberOfEvents": feature.get("numberOfEvents", ""),
                    "Notes": feature.get("notes", ""),
                    "FrequencyCorrected": feature.get("frequency_corrected", False),
                    "LowFreq_Original": feature.get("lowFreq_original", ""),
                    "HighFreq_Original": feature.get("highFreq_original", ""),
                })
    return rows


def write_csv(rows, filepath):
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows, label):
    if not rows:
        print(f"  {label}: 0 features")
        return
    participants = sorted(set(r["Participant"] for r in rows))
    volcanoes = sorted(set(r["Volcano"] for r in rows))
    print(f"\n  {label}: {len(rows)} features")
    print(f"  Participants: {participants}")
    print(f"  Volcanoes: {volcanoes}")
    for p in participants:
        p_rows = [r for r in rows if r["Participant"] == p]
        p_volcanoes = sorted(set(r["Volcano"] for r in p_rows))
        sessions = len(set(r['SessionNumber'] for r in p_rows))
        print(f"    {p}: {len(p_rows)} features, {sessions} sessions, volcanoes: {p_volcanoes}")


def main():
    # --- Participants ---
    participant_data = load_json(os.path.join(SCRIPT_DIR, "participant_sessions.json"))
    participant_rows = flatten_participant_data(participant_data)

    out_participants = os.path.join(SCRIPT_DIR, "master_event_catalog_participants.csv")
    write_csv(participant_rows, out_participants)
    print(f"Written: {out_participants}")
    print_summary(participant_rows, "Participants")

    # --- Expert (Leif) ---
    # Use most recent Qualtrics export
    qualtrics_dir = os.path.join(SCRIPT_DIR, '..', 'Qualtrics', 'Downloaded_Data')
    export_file = os.path.join(qualtrics_dir, 'qualtrics_export_2025-12-12_10-20-36.json')

    if os.path.exists(export_file):
        expert_rows = extract_expert_from_qualtrics(export_file)
        out_expert = os.path.join(SCRIPT_DIR, "master_event_catalog_expert.csv")
        write_csv(expert_rows, out_expert)
        print(f"\nWritten: {out_expert}")
        print_summary(expert_rows, "Expert")
    else:
        print(f"\nQualtrics export not found: {export_file}")
        print("  Skipping expert extraction")
        expert_rows = []

    # --- Combined ---
    if expert_rows:
        combined = participant_rows + expert_rows
        out_combined = os.path.join(SCRIPT_DIR, "master_event_catalog_combined.csv")
        write_csv(combined, out_combined)
        print(f"\nWritten: {out_combined}")
        print_summary(combined, "Combined")


if __name__ == "__main__":
    main()
