#!/usr/bin/env python3
"""
Prepare participant and session data for UI dropdowns

Combines participant metadata from meta analysis with session data from Qualtrics export.
Outputs JSON structure ready for frontend consumption.
"""

import json
from pathlib import Path
from parse_participants import parse_participants
from extract_sessions import extract_sessions_by_participant

def prepare_ui_data(meta_file_path: str, export_file_path: str) -> dict:
    """
    Prepare structured data for UI dropdowns

    Returns:
        dict with structure:
        {
            "participants": [
                {
                    "value": "R_xxxxx",
                    "label": "P1 - R_xxxxx",
                    "sessions": [
                        {
                            "value": "response_id",
                            "label": "Session 1 (2025-11-21) [10 features]",
                            "session_number": 1,
                            "date": "2025-11-21",
                            "timed_out": false,
                            "feature_count": 10,
                            "regions": [...],
                            "volcano_code": "REF"
                        },
                        ...
                    ]
                },
                ...
            ],
            "expert": { same structure as participants },
            "metadata": {
                "total_participants": 6,
                "total_sessions": 41,
                "generated_at": "2025-12-11T..."
            }
        }
    """
    from datetime import datetime

    # Load participant metadata
    participant_meta = parse_participants(meta_file_path)

    # Load session data
    sessions_by_id = extract_sessions_by_participant(export_file_path)

    # Build UI data structure
    ui_participants = []

    # Process the 6 real participants
    for p in participant_meta['participants']:
        pid = p['participant_id']
        sessions_data = sessions_by_id.get(pid, [])

        # Build session list for this participant (complete sessions only)
        session_list = []
        for session in sessions_data:
            volcano_display = f" - {session['volcano']}" if session['volcano'] else ""
            session_list.append({
                'value': session['response_id'],
                'session_id': session['session_id'],
                'label': f"Session {session['session_number']} ({session['date_display']}){volcano_display} - {session['feature_count']} features",
                'session_number': session['session_number'],
                'date': session['date_display'],
                'feature_count': session['feature_count'],
                'region_count': len(session['regions']),
                # Data fetch parameters (everything needed to reconstruct the session)
                'volcano': session['volcano'],
                'station': session['station'],
                'duration': session['duration'],
                'fetch_timestamp': session['fetch_timestamp'],
                'highpass_freq': session['highpass_freq'],
                'enable_normalize': session['enable_normalize'],
                'uses_corrected_formula': session['uses_corrected_formula'],
                # Region and feature data
                'regions': session['regions']
            })

        ui_participants.append({
            'value': pid,
            'label': p['display_name'],
            'p_number': p['p_number'],
            'complete_sessions': p['complete_sessions'],
            'timeout_sessions': p['timeout_sessions'],
            'total_sessions': p['total_sessions'],
            'features': p['features'],
            'regions': p['regions'],
            'sessions': session_list
        })

    # Process expert (Leif)
    expert = None
    if participant_meta['expert']:
        e = participant_meta['expert']
        pid = e['participant_id']
        sessions_data = sessions_by_id.get(pid, [])

        session_list = []
        for session in sessions_data:
            volcano_display = f" - {session['volcano']}" if session['volcano'] else ""
            session_list.append({
                'value': session['response_id'],
                'session_id': session['session_id'],
                'label': f"Session {session['session_number']} ({session['date_display']}){volcano_display} - {session['feature_count']} features",
                'session_number': session['session_number'],
                'date': session['date_display'],
                'feature_count': session['feature_count'],
                'region_count': len(session['regions']),
                # Data fetch parameters
                'volcano': session['volcano'],
                'station': session['station'],
                'duration': session['duration'],
                'fetch_timestamp': session['fetch_timestamp'],
                'highpass_freq': session['highpass_freq'],
                'enable_normalize': session['enable_normalize'],
                'uses_corrected_formula': session['uses_corrected_formula'],
                # Region and feature data
                'regions': session['regions']
            })

        expert = {
            'value': pid,
            'label': e['display_name'],
            'complete_sessions': e['complete_sessions'],
            'timeout_sessions': e['timeout_sessions'],
            'total_sessions': e['total_sessions'],
            'features': e['features'],
            'regions': e['regions'],
            'sessions': session_list
        }

    # Metadata
    total_sessions = sum(len(p['sessions']) for p in ui_participants)
    if expert:
        total_sessions += len(expert['sessions'])

    result = {
        'participants': ui_participants,
        'expert': expert,
        'metadata': {
            'total_participants': len(ui_participants),
            'total_sessions': total_sessions,
            'generated_at': datetime.utcnow().isoformat() + 'Z'
        }
    }

    return result

def main():
    """Test and output UI data"""
    script_dir = Path(__file__).parent
    meta_file = script_dir.parent / 'Qualtrics' / 'analysis' / 'Volcano_Audio_Meta_Analysis.md'
    export_file = script_dir.parent / 'Downloaded_Data' / 'qualtrics_export_2025-12-11_22-01-51.json'

    print(f"Preparing UI data...\n")
    print(f"  Meta file:   {meta_file}")
    print(f"  Export file: {export_file}\n")

    ui_data = prepare_ui_data(str(meta_file), str(export_file))

    # Print summary
    print("=" * 80)
    print("UI DATA SUMMARY")
    print("=" * 80)

    print(f"\nParticipants: {ui_data['metadata']['total_participants']}")
    print(f"Total Sessions: {ui_data['metadata']['total_sessions']}")

    # Print each participant
    print("\n" + "=" * 80)
    print("PARTICIPANTS")
    print("=" * 80)
    for p in ui_data['participants']:
        print(f"\n{p['label']}")
        print(f"  Sessions: {len(p['sessions'])}")
        for session in p['sessions'][:3]:  # Show first 3 sessions
            print(f"    - {session['label']}")
        if len(p['sessions']) > 3:
            print(f"    ... and {len(p['sessions']) - 3} more")

    # Print expert
    if ui_data['expert']:
        print("\n" + "=" * 80)
        print("EXPERT POOL")
        print("=" * 80)
        e = ui_data['expert']
        print(f"\n{e['label']}")
        print(f"  Sessions: {len(e['sessions'])}")
        for session in e['sessions'][:3]:
            print(f"    - {session['label']}")
        if len(e['sessions']) > 3:
            print(f"    ... and {len(e['sessions']) - 3} more")

    # Save to JSON file
    output_file = script_dir / 'participant_sessions.json'
    with open(output_file, 'w') as f:
        json.dump(ui_data, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✅ Saved to: {output_file}")
    print("=" * 80)

if __name__ == '__main__':
    main()
