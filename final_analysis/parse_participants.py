#!/usr/bin/env python3
"""
Parse participant data from Volcano_Audio_Meta_Analysis.md

Extracts:
- 6 real participants (P1-P6) with their IDs and session counts
- Leif (study coordinator) from expert pool
"""

import re
from pathlib import Path
from typing import List, Dict

def parse_participants(meta_file_path: str) -> Dict[str, List[Dict]]:
    """
    Parse participants from meta analysis markdown file

    Returns:
        dict with 'participants' (P1-P6) and 'expert' (Leif) lists
    """
    with open(meta_file_path, 'r') as f:
        content = f.read()

    participants = []
    expert = None

    # Parse the "The 6 Real Participants" table
    # Format: | P# | Participant ID | Complete | Timeout | Regions* | Features* | AWE | CNS Pre |
    participant_pattern = r'\| P(\d+) \| (R_\w+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (.+?) \|'

    for match in re.finditer(participant_pattern, content):
        p_num = int(match.group(1))
        participant_id = match.group(2)
        complete_sessions = int(match.group(3))
        timeout_sessions = int(match.group(4))
        regions = int(match.group(5))
        features = int(match.group(6))
        awe_sessions = int(match.group(7))
        cns_pre = match.group(8).strip()

        participants.append({
            'p_number': p_num,
            'participant_id': participant_id,
            'complete_sessions': complete_sessions,
            'timeout_sessions': timeout_sessions,
            'total_sessions': complete_sessions + timeout_sessions,
            'regions': regions,
            'features': features,
            'awe_sessions': awe_sessions,
            'cns_pre': cns_pre,
            'display_name': f"P{p_num} - {participant_id}"
        })

    # Parse Leif (Study Coordinator)
    # Format: | R_79bBz3856cnKDLj | 17 | 2 | 42 | 160 | Leif (collaborator...) |
    leif_pattern = r'\| (R_\w+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \| Leif'
    leif_match = re.search(leif_pattern, content)

    if leif_match:
        expert = {
            'p_number': 'Expert',
            'participant_id': leif_match.group(1),
            'complete_sessions': int(leif_match.group(2)),
            'timeout_sessions': int(leif_match.group(3)),
            'total_sessions': int(leif_match.group(2)) + int(leif_match.group(3)),
            'regions': int(leif_match.group(4)),
            'features': int(leif_match.group(5)),
            'display_name': f"Leif (Expert) - {leif_match.group(1)}"
        }

    return {
        'participants': participants,
        'expert': expert
    }

def main():
    """Test the parser"""
    # Get the meta analysis file path
    script_dir = Path(__file__).parent
    meta_file = script_dir.parent / 'Qualtrics' / 'analysis' / 'Volcano_Audio_Meta_Analysis.md'

    print(f"Parsing: {meta_file}\n")

    result = parse_participants(str(meta_file))

    # Print participants
    print("=" * 80)
    print("THE 6 REAL PARTICIPANTS")
    print("=" * 80)
    for p in result['participants']:
        print(f"\n{p['display_name']}")
        print(f"  Complete Sessions: {p['complete_sessions']}")
        print(f"  Timeout Sessions:  {p['timeout_sessions']}")
        print(f"  Total Sessions:    {p['total_sessions']}")
        print(f"  Regions:           {p['regions']}")
        print(f"  Features:          {p['features']}")
        print(f"  AWE Sessions:      {p['awe_sessions']}")
        print(f"  CNS Pre:           {p['cns_pre']}")

    # Print expert
    print("\n" + "=" * 80)
    print("EXPERT POOL")
    print("=" * 80)
    if result['expert']:
        e = result['expert']
        print(f"\n{e['display_name']}")
        print(f"  Complete Sessions: {e['complete_sessions']}")
        print(f"  Timeout Sessions:  {e['timeout_sessions']}")
        print(f"  Total Sessions:    {e['total_sessions']}")
        print(f"  Regions:           {e['regions']}")
        print(f"  Features:          {e['features']}")

    print("\n" + "=" * 80)
    print(f"TOTAL: {len(result['participants'])} participants + 1 expert")
    print("=" * 80)

if __name__ == '__main__':
    main()
