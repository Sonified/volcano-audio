#!/usr/bin/env python3
"""
Check ALL participants to see who has CNS pre and post data
"""

import json
from pathlib import Path

# All 6 official participants
PARTICIPANTS = {
    'P1': 'R_5JaVr26m73u2RY5',
    'P2': 'R_2TyCD0zFdqv1FpW',
    'P3': 'R_8BBUYM1zn3wSIb7',
    'P4': 'R_6GB2MdyhKnNXJl1',
    'P5': 'R_7iEa5eUCZyYib15',
    'P6': 'R_3AKHxZD5uNa4XOF'
}

LEIF_ID = 'R_79bBz3856cnKDLj'

# Load CNS pre-survey export
cns_pre_path = Path(__file__).parent.parent.parent / 'Qualtrics' / 'Downloaded_Data' / 'cns_survey_export_2025-12-08_09-15-53.json'

print("=" * 100)
print("CHECKING CNS PRE-SURVEY DATA")
print("=" * 100)
print()

cns_pre_scores = {}

with open(cns_pre_path, 'r') as f:
    cns_data = json.load(f)

for response in cns_data['responses']:
    response_id = response.get('responseId')
    values = response.get('values', {})

    # Check if this is one of our participants or Leif
    participant = None
    for p_num, p_id in PARTICIPANTS.items():
        if response_id == p_id:
            participant = p_num
            break
    if response_id == LEIF_ID:
        participant = 'Leif'

    if participant:
        # Extract CNS scores (QID5_1 through QID5_14)
        scores = []
        for i in range(1, 15):
            score = values.get(f'QID5_{i}')
            if score is not None:
                scores.append(int(score))

        if len(scores) == 14:
            total = sum(scores)
            cns_pre_scores[participant] = {
                'id': response_id,
                'items': scores,
                'total': total
            }
            print(f"{participant:6} {response_id:20} Total: {total:3} Items: {scores}")

print()
print(f"Found {len(cns_pre_scores)} participants with CNS PRE data")
print()

# Load CNS post-survey data from R2 downloads
cns_post_path = Path(__file__).parent.parent.parent / 'Qualtrics' / 'Downloaded_Data' / 'cns_post_surveys'

print("=" * 100)
print("CHECKING CNS POST-SURVEY DATA (from R2)")
print("=" * 100)
print()

cns_post_scores = {}

if cns_post_path.exists():
    for file in cns_post_path.glob('*.json'):
        with open(file, 'r') as f:
            data = json.load(f)

        participant_id = data.get('participantId')

        # Find which participant this is
        participant = None
        for p_num, p_id in PARTICIPANTS.items():
            if participant_id == p_id:
                participant = p_num
                break
        if participant_id == LEIF_ID:
            participant = 'Leif'

        if participant:
            responses = data.get('responses', {})
            # Extract CNS scores (cns1 through cns14)
            scores = []
            for i in range(1, 15):
                score = responses.get(f'cns{i}')
                if score is not None:
                    scores.append(int(score))

            if len(scores) == 14:
                total = data.get('rawTotal', sum(scores))
                cns_post_scores[participant] = {
                    'id': participant_id,
                    'items': scores,
                    'total': total,
                    'file': file.name
                }
                print(f"{participant:6} {participant_id:20} Total: {total:3} Items: {scores}")
                print(f"       Source: {file.name}")
                print()

print(f"Found {len(cns_post_scores)} participants with CNS POST data")
print()

# Compare
print("=" * 100)
print("COMPLETE CNS DATA (PRE + POST)")
print("=" * 100)
print()

all_participants = sorted(set(list(cns_pre_scores.keys()) + list(cns_post_scores.keys())))

for p in all_participants:
    has_pre = '✅' if p in cns_pre_scores else '❌'
    has_post = '✅' if p in cns_post_scores else '❌'

    if p in cns_pre_scores and p in cns_post_scores:
        pre_total = cns_pre_scores[p]['total']
        post_total = cns_post_scores[p]['total']
        change = post_total - pre_total
        print(f"{p:6} Pre: {has_pre} Post: {has_post}  Scores: {pre_total:3} → {post_total:3} ({change:+3})")
    else:
        print(f"{p:6} Pre: {has_pre} Post: {has_post}  INCOMPLETE")

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)
print()

complete = [p for p in all_participants if p in cns_pre_scores and p in cns_post_scores]
print(f"Participants with COMPLETE CNS data: {len(complete)}")
print(f"  {', '.join(complete)}")
print()

missing_post = [p for p in PARTICIPANTS.keys() if p in cns_pre_scores and p not in cns_post_scores]
if missing_post:
    print(f"Participants with PRE but NO POST: {len(missing_post)}")
    print(f"  {', '.join(missing_post)}")
