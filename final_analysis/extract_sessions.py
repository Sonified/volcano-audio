#!/usr/bin/env python3
"""
Extract session data from Qualtrics export
Groups sessions by participant for UI dropdown loading
"""

import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
from datetime import datetime
from frequency_correction import correct_feature_frequencies

def load_qualtrics_export(export_path: str) -> dict:
    """Load the Qualtrics JSON export"""
    with open(export_path, 'r') as f:
        return json.load(f)

def extract_sessions_by_participant(export_path: str) -> Dict[str, List[Dict]]:
    """
    Extract all sessions grouped by participant ID

    Returns:
        dict mapping participant_id -> list of session dicts
        Each session dict contains:
            - session_number: 1-based session number for this participant
            - response_id: Qualtrics response ID
            - date: ISO date string
            - timed_out: bool
            - regions: list of regions with features
            - feature_count: total features in session
            - volcano_code: volcano code
            - session_id: unique session ID
    """
    data = load_qualtrics_export(export_path)

    # Group responses by participant
    sessions_by_participant = defaultdict(list)

    for response in data.get('responses', []):
        values = response.get('values', {})
        st = values.get('SessionTracking')

        if not st:
            continue

        # Parse SessionTracking JSON string
        try:
            st_data = json.loads(st)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse SessionTracking for response {response.get('responseId')}")
            continue

        participant_id = st_data.get('participantId')
        if not participant_id:
            continue

        # Extract session info
        regions = st_data.get('regions', [])
        feature_count = sum(len(region.get('features', [])) for region in regions)

        # Extract fetch data event details (everything needed to reconstruct the session)
        # IMPORTANT: Take the LAST fetch_data event, not the first!
        # Sessions can have multiple fetches if user changes volcano
        volcano = None
        station = None
        duration = None
        fetch_timestamp = None
        highpass_freq = None
        enable_normalize = None

        tracking_events = st_data.get('tracking', {}).get('events', [])
        for event in tracking_events:
            if event.get('type') == 'volcano_selected':
                volcano = event.get('data', {}).get('volcano')
            elif event.get('type') == 'fetch_data':
                # Don't break - keep going to get the LAST fetch event
                fetch_event = event.get('data', {})
                volcano = fetch_event.get('volcano')
                station = fetch_event.get('station')
                duration = fetch_event.get('duration')
                highpass_freq = fetch_event.get('highpassFreq')
                enable_normalize = fetch_event.get('enableNormalize')
                fetch_timestamp = event.get('timestamp')

        # Check for timeout in multiple places (format changed over time)
        timed_out = (
            st_data.get('sessionTimedOut', False) or  # Old format (top-level)
            st_data.get('workflowFlags', {}).get('study_session_timed_out', False)  # New format
        )

        # Skip timeout sessions entirely
        if timed_out:
            continue

        # Check if session uses corrected log formula
        uses_corrected_formula = st_data.get('usesCorrectedLogFormula', False)

        # Apply frequency correction to features if needed
        # Also filter out deleted/incomplete features (null timestamps)
        corrected_regions = regions
        if not uses_corrected_formula:
            corrected_regions = []
            for region in regions:
                corrected_region = region.copy()
                corrected_features = []
                for feature in region.get('features', []):
                    # Skip deleted/incomplete features (no timestamps = never drawn)
                    if feature.get('featureStartTime') is None or feature.get('featureEndTime') is None:
                        continue
                    # Skip corrupted features (start = end = single point, likely UI bug)
                    if feature.get('featureStartTime') == feature.get('featureEndTime'):
                        continue
                    corrected_feature = correct_feature_frequencies(feature, uses_corrected_formula)
                    corrected_features.append(corrected_feature)
                corrected_region['features'] = corrected_features
                corrected_regions.append(corrected_region)
        else:
            # Still need to filter deleted features even if no frequency correction needed
            corrected_regions = []
            for region in regions:
                corrected_region = region.copy()
                corrected_features = []
                for feature in region.get('features', []):
                    # Skip deleted/incomplete features (no timestamps = never drawn)
                    if feature.get('featureStartTime') is None or feature.get('featureEndTime') is None:
                        continue
                    # Skip corrupted features (start = end = single point, likely UI bug)
                    if feature.get('featureStartTime') == feature.get('featureEndTime'):
                        continue
                    corrected_features.append(feature)
                corrected_region['features'] = corrected_features
                corrected_regions.append(corrected_region)

        session_data = {
            'response_id': response.get('responseId'),
            'session_id': st_data.get('sessionId'),
            'date': values.get('startDate', ''),
            'date_display': values.get('startDate', '')[:10] if values.get('startDate') else 'Unknown',
            'volcano': volcano,
            'station': station,
            'duration': duration,
            'fetch_timestamp': fetch_timestamp,
            'highpass_freq': highpass_freq,
            'enable_normalize': enable_normalize,
            'uses_corrected_formula': uses_corrected_formula,
            'regions': corrected_regions,
            'feature_count': feature_count,
            'raw_st_data': st_data  # Keep full SessionTracking for later use
        }

        sessions_by_participant[participant_id].append(session_data)

    # Sort sessions by date and assign session numbers
    for participant_id in sessions_by_participant:
        # Sort by date
        sessions_by_participant[participant_id].sort(key=lambda s: s['date'])

        # Assign session numbers
        for i, session in enumerate(sessions_by_participant[participant_id], 1):
            session['session_number'] = i

    return dict(sessions_by_participant)

def get_session_summary(sessions_by_participant: Dict[str, List[Dict]]) -> Dict[str, Dict]:
    """
    Get summary stats for each participant

    Returns:
        dict mapping participant_id -> summary dict with:
            - total_sessions: total number of sessions
            - complete_sessions: number of complete (non-timeout) sessions
            - timeout_sessions: number of timeout sessions
            - total_features: total features across all sessions
            - total_regions: total regions across all sessions
    """
    summary = {}

    for participant_id, sessions in sessions_by_participant.items():
        complete = [s for s in sessions if not s['timed_out']]
        timeouts = [s for s in sessions if s['timed_out']]

        summary[participant_id] = {
            'total_sessions': len(sessions),
            'complete_sessions': len(complete),
            'timeout_sessions': len(timeouts),
            'total_features': sum(s['feature_count'] for s in sessions),
            'total_regions': sum(len(s['regions']) for s in sessions)
        }

    return summary

def main():
    """Test the session extractor"""
    # Get the Qualtrics export path
    script_dir = Path(__file__).parent
    export_file = script_dir.parent / 'Downloaded_Data' / 'qualtrics_export_2025-12-11_22-01-51.json'

    print(f"Loading: {export_file}\n")

    sessions_by_participant = extract_sessions_by_participant(str(export_file))
    summary = get_session_summary(sessions_by_participant)

    # Print summary
    print("=" * 80)
    print("SESSION DATA BY PARTICIPANT")
    print("=" * 80)

    for participant_id in sorted(sessions_by_participant.keys()):
        sessions = sessions_by_participant[participant_id]
        stats = summary[participant_id]

        print(f"\n{participant_id}")
        print(f"  Total Sessions:    {stats['total_sessions']}")
        print(f"  Complete:          {stats['complete_sessions']}")
        print(f"  Timeouts:          {stats['timeout_sessions']}")
        print(f"  Total Features:    {stats['total_features']}")
        print(f"  Total Regions:     {stats['total_regions']}")

        # Show each session
        print(f"\n  Sessions:")
        for session in sessions:
            timeout_marker = " [TIMEOUT]" if session['timed_out'] else ""
            print(f"    Session {session['session_number']}: {session['date_display']}{timeout_marker}")
            print(f"      Volcano: {session['volcano']}")
            print(f"      Features: {session['feature_count']}, Regions: {len(session['regions'])}")

    print("\n" + "=" * 80)
    print(f"TOTAL: {len(sessions_by_participant)} participants")
    print("=" * 80)

if __name__ == '__main__':
    main()
