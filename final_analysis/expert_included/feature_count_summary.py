#!/usr/bin/env python3
"""
Calculate total features identified across all participants + expert
"""

print("=" * 80)
print("FEATURE IDENTIFICATION SUMMARY: Participants + Expert")
print("=" * 80)
print()

# From Volcano_Audio_Meta_Analysis.md
participants = {
    'P1': {'sessions': 5, 'features': 114},
    'P2': {'sessions': 4, 'features': 29},
    'P3': {'sessions': 4, 'features': 65},
    'P4': {'sessions': 2, 'features': 15},
    'P5': {'sessions': 1, 'features': 3},
    'P6': {'sessions': 1, 'features': 2},
}

leif = {'sessions': 17, 'features': 160}

print("PARTICIPANTS (P1-P6)")
print("-" * 80)
for p_id, data in participants.items():
    features_per_session = data['features'] / data['sessions']
    print(f"{p_id:4} {data['sessions']:2} sessions, {data['features']:3} features ({features_per_session:5.1f} per session)")

total_p_sessions = sum(p['sessions'] for p in participants.values())
total_p_features = sum(p['features'] for p in participants.values())
avg_p_per_session = total_p_features / total_p_sessions

print("-" * 80)
print(f"TOTAL: {total_p_sessions} sessions, {total_p_features} features ({avg_p_per_session:.1f} per session avg)")
print()

print("EXPERT (Leif)")
print("-" * 80)
leif_per_session = leif['features'] / leif['sessions']
print(f"Leif: {leif['sessions']} sessions, {leif['features']} features ({leif_per_session:.1f} per session)")
print()

print("=" * 80)
print("COMBINED TOTALS")
print("=" * 80)
combined_sessions = total_p_sessions + leif['sessions']
combined_features = total_p_features + leif['features']
combined_avg = combined_features / combined_sessions

print(f"Total sessions:  {combined_sessions}")
print(f"Total features:  {combined_features}")
print(f"Average per session: {combined_avg:.1f}")
print()

print(f"Participants contributed: {total_p_features}/{combined_features} ({100*total_p_features/combined_features:.1f}%)")
print(f"Expert contributed:       {leif['features']}/{combined_features} ({100*leif['features']/combined_features:.1f}%)")
print()

# Compare engagement
print("=" * 80)
print("ENGAGEMENT COMPARISON")
print("=" * 80)
print(f"Participants average: {avg_p_per_session:.1f} features per session")
print(f"Expert (Leif):        {leif_per_session:.1f} features per session")
print(f"Expert is {leif_per_session/avg_p_per_session:.1f}x participant average")
