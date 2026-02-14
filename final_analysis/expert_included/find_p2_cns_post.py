#!/usr/bin/env python3
"""
Find P2's CNS post data - must be in the main Qualtrics export
"""

import json
from pathlib import Path

P2_ID = 'R_2TyCD0zFdqv1FpW'

# Check main Qualtrics export
export_path = Path(__file__).parent.parent.parent / 'Qualtrics' / 'Downloaded_Data' / 'qualtrics_export_2025-12-12_10-20-36.json'

print(f"Searching for P2's CNS post data in: {export_path}")
print(f"P2 ID: {P2_ID}")
print()

with open(export_path, 'r') as f:
    data = json.load(f)

p2_responses = []

for response in data['responses']:
    values = response.get('values', {})
    session_tracking = values.get('SessionTracking')

    if session_tracking:
        try:
            st_data = json.loads(session_tracking)
            participant_id = st_data.get('participantId')

            if participant_id == P2_ID:
                # Check if this response has CNS post data
                # CNS items might be in different QID fields

                # Look for any CNS-like data (14 items)
                qid_fields = {k: v for k, v in values.items() if k.startswith('QID')}

                response_info = {
                    'responseId': response.get('responseId'),
                    'date': values.get('startDate', '')[:10],
                    'qid_fields': qid_fields
                }

                p2_responses.append(response_info)
        except:
            pass

print(f"Found {len(p2_responses)} responses from P2")
print()

for i, resp in enumerate(p2_responses, 1):
    print(f"Response {i}: {resp['date']} ({resp['responseId']})")
    print(f"  QID fields: {list(resp['qid_fields'].keys())}")
    print()

# Look specifically for CNS post pattern
# From the meta analysis, P2 CNS post = 38
# CNS items are 1-5 scale, so 38/14 = 2.71 average

print("=" * 80)
print("CHECKING FOR CNS POST DATA (looking for 14-item sets that sum to ~38)")
print("=" * 80)
print()

for i, resp in enumerate(p2_responses, 1):
    qids = resp['qid_fields']

    # Try different QID patterns
    for base_qid in ['QID12', 'QID14', 'QID15', 'QID16']:
        items = []
        for j in range(1, 15):
            key = f'{base_qid}_{j}'
            if key in qids and qids[key] is not None:
                items.append(int(qids[key]))

        if len(items) == 14:
            total = sum(items)
            print(f"Response {i} ({resp['date']}): Found {base_qid}_1-14")
            print(f"  Items: {items}")
            print(f"  Total: {total}")
            if total == 38:
                print(f"  ✅ MATCHES P2's expected CNS post score!")
            print()
