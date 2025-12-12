#!/usr/bin/env python3
"""
Comprehensive integration test for participant session data

Tests:
1. Parse participant sessions from JSON
2. Verify session counts match expected values
3. For each session, verify:
   - All fetch parameters are present
   - Data window can be calculated from fetch_timestamp
   - All region timestamps fall within the data window
   - All feature timestamps fall within their regions
4. Verify frequency correction was applied correctly
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

def load_participant_data() -> dict:
    """Load the participant_sessions.json"""
    json_path = Path(__file__).parent / 'participant_sessions.json'
    with open(json_path, 'r') as f:
        return json.load(f)

def parse_iso_timestamp(ts: str) -> datetime:
    """Parse ISO timestamp string to datetime"""
    # Handle both formats: with and without microseconds
    if '.' in ts:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    else:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))

def test_participant_counts(data: dict) -> bool:
    """Test that participant counts match expected values"""
    print("\n" + "="*70)
    print("TEST 1: Participant Session Counts")
    print("="*70)

    expected_counts = {
        'R_5JaVr26m73u2RY5': 5,  # P1
        'R_2TyCD0zFdqv1FpW': 4,  # P2
        'R_8BBUYM1zn3wSIb7': 4,  # P3
        'R_6GB2MdyhKnNXJl1': 2,  # P4
        'R_7iEa5eUCZyYib15': 1,  # P5
        'R_3AKHxZD5uNa4XOF': 1,  # P6
        'R_79bBz3856cnKDLj': 17, # Leif (expert)
    }

    all_passed = True

    for p in data['participants']:
        pid = p['value']
        actual = len(p['sessions'])
        expected = expected_counts.get(pid, 0)

        if actual == expected:
            print(f"✅ {p['label']}: {actual} sessions (expected {expected})")
        else:
            print(f"❌ {p['label']}: {actual} sessions (expected {expected})")
            all_passed = False

    if data.get('expert'):
        e = data['expert']
        pid = e['value']
        actual = len(e['sessions'])
        expected = expected_counts.get(pid, 0)

        if actual == expected:
            print(f"✅ {e['label']}: {actual} sessions (expected {expected})")
        else:
            print(f"❌ {e['label']}: {actual} sessions (expected {expected})")
            all_passed = False

    return all_passed

def test_fetch_parameters(data: dict) -> bool:
    """Test that all sessions have required fetch parameters"""
    print("\n" + "="*70)
    print("TEST 2: Fetch Parameters Completeness")
    print("="*70)

    required_params = [
        'volcano', 'station', 'duration', 'fetch_timestamp',
        'highpass_freq', 'enable_normalize'
    ]

    all_passed = True
    total_sessions = 0
    sessions_with_all_params = 0

    all_participants = data['participants'] + ([data['expert']] if data.get('expert') else [])

    for p in all_participants:
        for session in p['sessions']:
            total_sessions += 1
            missing_params = []

            for param in required_params:
                if session.get(param) is None:
                    missing_params.append(param)

            if not missing_params:
                sessions_with_all_params += 1
            else:
                print(f"❌ Session {session['session_number']} ({p['label'][:10]}): Missing {missing_params}")
                all_passed = False

    if all_passed:
        print(f"✅ All {total_sessions} sessions have complete fetch parameters")
    else:
        print(f"❌ {total_sessions - sessions_with_all_params}/{total_sessions} sessions missing parameters")

    return all_passed

def test_data_window_validity(data: dict) -> bool:
    """Test that all regions fall within the fetched data window"""
    print("\n" + "="*70)
    print("TEST 3: Data Window Validity")
    print("="*70)

    all_passed = True
    total_regions_tested = 0
    regions_within_window = 0

    all_participants = data['participants'] + ([data['expert']] if data.get('expert') else [])

    for p in all_participants:
        for session in p['sessions']:
            fetch_ts = session.get('fetch_timestamp')
            duration_hours = session.get('duration', 24)

            if not fetch_ts:
                continue

            # Replicate the JavaScript logic from main.js:617-634
            # The data window is NOT [fetch_timestamp - duration, fetch_timestamp]!
            # It's calculated by rounding fetch_timestamp back to the last complete 10-minute chunk

            fetch_time = parse_iso_timestamp(fetch_ts)
            current_minute = fetch_time.minute
            current_second = fetch_time.second

            # Round to 10-minute boundary
            current_period_start = (current_minute // 10) * 10
            minutes_since_period_start = current_minute - current_period_start
            seconds_since_period_start = minutes_since_period_start * 60 + current_second

            # Determine estimatedEndTime (matches main.js logic)
            if seconds_since_period_start >= 135:  # 2 min 15 sec
                # Use current boundary
                estimated_end_time = fetch_time.replace(minute=current_period_start, second=0, microsecond=0)
            else:
                # Use previous boundary
                estimated_end_time = fetch_time.replace(minute=current_period_start, second=0, microsecond=0) - timedelta(minutes=10)

            # Calculate actual data window
            window_end = estimated_end_time
            window_start = window_end - timedelta(hours=duration_hours)

            # Check all regions in this session
            for region in session.get('regions', []):
                total_regions_tested += 1
                region_start_str = region.get('regionStartTime')
                region_end_str = region.get('regionEndTime')

                if not region_start_str or not region_end_str:
                    print(f"❌ Region {region.get('regionNumber')} missing timestamps")
                    all_passed = False
                    continue

                region_start = parse_iso_timestamp(region_start_str)
                region_end = parse_iso_timestamp(region_end_str)

                # Check if region falls within data window
                if region_start >= window_start and region_end <= window_end:
                    regions_within_window += 1
                else:
                    print(f"❌ {p['label'][:10]} Session {session['session_number']} Region {region.get('regionNumber')}: OUT OF BOUNDS")
                    print(f"    Fetch timestamp: {fetch_time}")
                    print(f"    Estimated end:   {estimated_end_time}")
                    print(f"    Data window:     {window_start} to {window_end}")
                    print(f"    Region:          {region_start} to {region_end}")
                    all_passed = False

    if all_passed:
        print(f"✅ All {total_regions_tested} regions fall within their data windows")
    else:
        print(f"❌ {regions_within_window}/{total_regions_tested} regions within window")

    return all_passed

def test_feature_timestamps(data: dict) -> bool:
    """Test that all features fall within their parent regions"""
    print("\n" + "="*70)
    print("TEST 4: Feature Timestamp Validity")
    print("="*70)

    all_passed = True
    total_features_tested = 0
    features_within_region = 0

    all_participants = data['participants'] + ([data['expert']] if data.get('expert') else [])

    for p in all_participants:
        for session in p['sessions']:
            for region in session.get('regions', []):
                region_start = parse_iso_timestamp(region.get('regionStartTime'))
                region_end = parse_iso_timestamp(region.get('regionEndTime'))

                for feature in region.get('features', []):
                    total_features_tested += 1
                    feat_start_str = feature.get('featureStartTime')
                    feat_end_str = feature.get('featureEndTime')

                    if not feat_start_str or not feat_end_str:
                        print(f"❌ {p['label'][:20]} Session {session['session_number']} Region {region.get('regionNumber')} Feature {feature.get('featureNumber')}: MISSING TIMESTAMPS")
                        print(f"    Feature data: {feature}")
                        all_passed = False
                        continue

                    feat_start = parse_iso_timestamp(feat_start_str)
                    feat_end = parse_iso_timestamp(feat_end_str)

                    # Check if feature falls within region
                    if feat_start >= region_start and feat_end <= region_end:
                        features_within_region += 1
                    else:
                        print(f"❌ {p['label'][:20]} Session {session['session_number']} Region {region.get('regionNumber')} Feature {feature.get('featureNumber')}: OUTSIDE REGION BOUNDS")
                        print(f"    Region: {region_start} to {region_end}")
                        print(f"    Feature: {feat_start} to {feat_end}")
                        print(f"    Feature data: {feature}")
                        all_passed = False

    if all_passed:
        print(f"✅ All {total_features_tested} features fall within their regions")
    else:
        print(f"❌ {features_within_region}/{total_features_tested} features within regions")

    return all_passed

def test_frequency_correction(data: dict) -> bool:
    """Test that frequency correction was applied correctly"""
    print("\n" + "="*70)
    print("TEST 5: Frequency Correction")
    print("="*70)

    sessions_without_flag = 0
    features_needing_correction = 0
    features_corrected = 0

    all_participants = data['participants'] + ([data['expert']] if data.get('expert') else [])

    for p in all_participants:
        for session in p['sessions']:
            uses_corrected = session.get('uses_corrected_formula', False)

            if not uses_corrected:
                sessions_without_flag += 1

                for region in session.get('regions', []):
                    for feature in region.get('features', []):
                        speed = feature.get('speedFactor', 1)

                        if speed != 1:
                            features_needing_correction += 1

                            if feature.get('frequency_corrected'):
                                features_corrected += 1

    all_passed = features_needing_correction == features_corrected

    print(f"  Sessions without corrected formula flag: {sessions_without_flag}")
    print(f"  Features requiring correction (speedFactor ≠ 1): {features_needing_correction}")
    print(f"  Features actually corrected: {features_corrected}")

    if all_passed:
        print(f"✅ All {features_needing_correction} features were corrected")
    else:
        print(f"❌ {features_needing_correction - features_corrected} features missing correction")

    return all_passed

def test_sample_session_query(data: dict) -> bool:
    """Test querying a specific participant's session"""
    print("\n" + "="*70)
    print("TEST 6: Sample Session Query")
    print("="*70)

    # Query P1's first session
    p1 = next((p for p in data['participants'] if 'P1' in p['label']), None)

    if not p1:
        print("❌ Could not find P1")
        return False

    if not p1['sessions']:
        print("❌ P1 has no sessions")
        return False

    session = p1['sessions'][0]

    print(f"  Participant: {p1['label']}")
    print(f"  Session: {session['session_number']}")
    print(f"  Date: {session['date']}")
    print(f"  Volcano: {session['volcano']}")
    print(f"  Station: {session['station']}")
    print(f"  Duration: {session['duration']} hours")
    print(f"  Fetch timestamp: {session['fetch_timestamp']}")

    # Calculate data window
    window_end = parse_iso_timestamp(session['fetch_timestamp'])
    window_start = window_end - timedelta(hours=session['duration'])

    print(f"\n  Data window:")
    print(f"    Start: {window_start}")
    print(f"    End:   {window_end}")

    print(f"\n  Regions: {session['region_count']}")
    print(f"  Features: {session['feature_count']}")

    if session['regions']:
        r1 = session['regions'][0]
        print(f"\n  First region:")
        print(f"    Start: {r1.get('regionStartTime')}")
        print(f"    End:   {r1.get('regionEndTime')}")
        print(f"    Features: {len(r1.get('features', []))}")

        if r1.get('features'):
            f1 = r1['features'][0]
            print(f"\n  First feature:")
            print(f"    Freq: {f1.get('lowFreq')} - {f1.get('highFreq')} Hz")
            print(f"    Type: {f1.get('type')}")
            print(f"    Notes: {f1.get('notes', '')[:50]}")
            if f1.get('frequency_corrected'):
                print(f"    ✅ Corrected (original: {f1.get('lowFreq_original')} - {f1.get('highFreq_original')})")

    print("\n✅ Session query successful")
    return True

def main():
    """Run all integration tests"""
    print("="*70)
    print("COMPREHENSIVE INTEGRATION TEST")
    print("="*70)

    # Load data
    try:
        data = load_participant_data()
        print(f"✅ Loaded participant_sessions.json")
        print(f"   Participants: {len(data['participants'])}")
        print(f"   Expert: {'Yes' if data.get('expert') else 'No'}")
        print(f"   Total sessions: {data['metadata']['total_sessions']}")
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        return False

    # Run tests
    results = []
    results.append(("Participant Counts", test_participant_counts(data)))
    results.append(("Fetch Parameters", test_fetch_parameters(data)))
    results.append(("Data Window Validity", test_data_window_validity(data)))
    results.append(("Feature Timestamps", test_feature_timestamps(data)))
    results.append(("Frequency Correction", test_frequency_correction(data)))
    results.append(("Sample Session Query", test_sample_session_query(data)))

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*70)

    return all_passed

if __name__ == '__main__':
    import sys
    sys.exit(0 if main() else 1)
