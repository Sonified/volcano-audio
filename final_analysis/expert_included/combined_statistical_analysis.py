#!/usr/bin/env python3
"""
Combined Statistical Analysis: Participants + Expert (Leif)

Tests whether including Leif's data (17 sessions) with participant data (17 sessions)
changes statistical significance for:
1. Session-level "Connected" mood shifts
2. Session-level "Focused" mood shifts (already significant for participants alone)
3. Other mood dimensions

Also performs paired t-tests to determine if shifts are statistically significant.
"""

import json
from pathlib import Path
from scipy import stats
import numpy as np

# Load participant data (from existing analysis)
# This replicates the data from Volcano_Audio_Meta_Analysis.md
PARTICIPANT_SESSIONS = [
    # P1 - 5 sessions
    {'participant': 'P1', 'session': 1, 'date': '2025-11-21', 'features': 10, 'calm': 0, 'energized': -1, 'connected': 1, 'nervous': 0, 'focused': 0, 'wonder': -1},
    {'participant': 'P1', 'session': 2, 'date': '2025-11-29', 'features': 18, 'calm': -1, 'energized': -1, 'connected': 1, 'nervous': 0, 'focused': 1, 'wonder': 0},
    {'participant': 'P1', 'session': 3, 'date': '2025-12-01', 'features': 4, 'calm': 0, 'energized': 0, 'connected': 0, 'nervous': 0, 'focused': 0, 'wonder': 0},
    {'participant': 'P1', 'session': 4, 'date': '2025-12-05', 'features': 16, 'calm': 0, 'energized': 0, 'connected': 0, 'nervous': 0, 'focused': 1, 'wonder': 0},
    {'participant': 'P1', 'session': 5, 'date': '2025-12-10', 'features': 66, 'calm': 0, 'energized': 0, 'connected': -1, 'nervous': 0, 'focused': 0, 'wonder': 0},

    # P2 - 4 sessions
    {'participant': 'P2', 'session': 1, 'date': '2025-11-19', 'features': 7, 'calm': 0, 'energized': 0, 'connected': 0, 'nervous': 1, 'focused': 0, 'wonder': 0},
    {'participant': 'P2', 'session': 2, 'date': '2025-11-27', 'features': 5, 'calm': 0, 'energized': 0, 'connected': 0, 'nervous': 0, 'focused': 0, 'wonder': 0},
    {'participant': 'P2', 'session': 3, 'date': '2025-11-28', 'features': 14, 'calm': 0, 'energized': 1, 'connected': 0, 'nervous': 0, 'focused': 0, 'wonder': 0},
    {'participant': 'P2', 'session': 4, 'date': '2025-12-02', 'features': 3, 'calm': 0, 'energized': 0, 'connected': 0, 'nervous': 0, 'focused': 1, 'wonder': 0},

    # P3 - 4 sessions
    {'participant': 'P3', 'session': 1, 'date': '2025-11-21', 'features': 11, 'calm': 2, 'energized': -1, 'connected': 0, 'nervous': 0, 'focused': 1, 'wonder': -1},
    {'participant': 'P3', 'session': 2, 'date': '2025-11-27', 'features': 31, 'calm': 1, 'energized': -1, 'connected': 1, 'nervous': 0, 'focused': 1, 'wonder': 0},
    {'participant': 'P3', 'session': 3, 'date': '2025-12-03', 'features': 10, 'calm': 1, 'energized': 0, 'connected': 0, 'nervous': -3, 'focused': 0, 'wonder': 1},
    {'participant': 'P3', 'session': 4, 'date': '2025-12-11', 'features': 17, 'calm': 0, 'energized': -2, 'connected': 0, 'nervous': 0, 'focused': 0, 'wonder': 0},

    # P4 - 2 sessions
    {'participant': 'P4', 'session': 1, 'date': '2025-11-21', 'features': 8, 'calm': 0, 'energized': -1, 'connected': -1, 'nervous': -1, 'focused': 0, 'wonder': 0},
    {'participant': 'P4', 'session': 2, 'date': '2025-12-09', 'features': 7, 'calm': 1, 'energized': -1, 'connected': 1, 'nervous': 0, 'focused': 1, 'wonder': 1},

    # P5 - 1 session
    {'participant': 'P5', 'session': 1, 'date': '2025-11-26', 'features': 3, 'calm': 1, 'energized': 1, 'connected': 1, 'nervous': 0, 'focused': 1, 'wonder': 1},

    # P6 - 1 session
    {'participant': 'P6', 'session': 1, 'date': '2025-11-24', 'features': 2, 'calm': 0, 'energized': 0, 'connected': 1, 'nervous': 0, 'focused': 0, 'wonder': 0},
]

# Load Leif's data
leif_data_path = Path(__file__).parent / 'leif_sessions.json'
with open(leif_data_path, 'r') as f:
    leif_sessions_raw = json.load(f)

# Convert Leif's data to same format
leif_sessions = []
for i, session in enumerate(leif_sessions_raw, 1):
    # Skip first session (missing mood data)
    if i == 1:
        continue

    leif_sessions.append({
        'participant': 'Leif',
        'session': i,
        'date': session['date'][:10],
        'features': session['feature_count'],
        'calm': session['mood_changes']['calm'],
        'energized': session['mood_changes']['energized'],
        'connected': session['mood_changes']['connected'],
        'nervous': session['mood_changes']['nervous'],
        'focused': session['mood_changes']['focused'],
        'wonder': session['mood_changes']['wonder']
    })

print("=" * 100)
print("COMBINED STATISTICAL ANALYSIS: Participants + Expert")
print("=" * 100)
print()

print(f"Participants: {len(PARTICIPANT_SESSIONS)} sessions (P1-P6)")
print(f"Expert (Leif): {len(leif_sessions)} sessions")
print(f"Combined Total: {len(PARTICIPANT_SESSIONS) + len(leif_sessions)} sessions")
print()

# Run analyses for each mood dimension
mood_items = ['calm', 'energized', 'connected', 'nervous', 'focused', 'wonder']

def analyze_mood_item(item_name, participants_only, combined):
    """
    Run paired t-test and descriptive statistics for a mood item
    """
    # Participants only
    p_values = [s[item_name] for s in participants_only if s[item_name] is not None]
    p_mean = np.mean(p_values)
    p_positive = sum(1 for v in p_values if v > 0)
    p_negative = sum(1 for v in p_values if v < 0)
    p_zero = sum(1 for v in p_values if v == 0)

    # One-sample t-test (H0: mean = 0)
    if len(p_values) > 1:
        p_t_stat, p_p_value = stats.ttest_1samp(p_values, 0)
    else:
        p_t_stat, p_p_value = None, None

    # Combined
    c_values = [s[item_name] for s in combined if s[item_name] is not None]
    c_mean = np.mean(c_values)
    c_positive = sum(1 for v in c_values if v > 0)
    c_negative = sum(1 for v in c_values if v < 0)
    c_zero = sum(1 for v in c_values if v == 0)

    # One-sample t-test (H0: mean = 0)
    if len(c_values) > 1:
        c_t_stat, c_p_value = stats.ttest_1samp(c_values, 0)
    else:
        c_t_stat, c_p_value = None, None

    return {
        'participants': {
            'n': len(p_values),
            'mean': p_mean,
            'positive_pct': 100 * p_positive / len(p_values) if p_values else 0,
            'negative_pct': 100 * p_negative / len(p_values) if p_values else 0,
            'zero_pct': 100 * p_zero / len(p_values) if p_values else 0,
            't_stat': p_t_stat,
            'p_value': p_p_value
        },
        'combined': {
            'n': len(c_values),
            'mean': c_mean,
            'positive_pct': 100 * c_positive / len(c_values) if c_values else 0,
            'negative_pct': 100 * c_negative / len(c_values) if c_values else 0,
            'zero_pct': 100 * c_zero / len(c_values) if c_values else 0,
            't_stat': c_t_stat,
            'p_value': c_p_value
        }
    }

print("=" * 100)
print("MOOD SHIFTS: PARTICIPANTS vs COMBINED (Participants + Expert)")
print("=" * 100)
print()

for item in mood_items:
    results = analyze_mood_item(item, PARTICIPANT_SESSIONS, PARTICIPANT_SESSIONS + leif_sessions)

    p = results['participants']
    c = results['combined']

    print(f"{item.upper()}")
    print("-" * 100)
    print(f"{'':20} {'N':>8} {'Mean Δ':>10} {'Positive':>10} {'t-stat':>10} {'p-value':>10} {'Significant?':>15}")
    print(f"{'Participants Only':20} {p['n']:8d} {p['mean']:10.2f} {p['positive_pct']:9.1f}% {p['t_stat']:10.2f} {p['p_value']:10.4f} {('✅ YES' if p['p_value'] and p['p_value'] < 0.05 else '')}")
    print(f"{'Combined (+ Leif)':20} {c['n']:8d} {c['mean']:10.2f} {c['positive_pct']:9.1f}% {c['t_stat']:10.2f} {c['p_value']:10.4f} {('✅ YES' if c['p_value'] and c['p_value'] < 0.05 else '')}")

    # Show change in significance
    if p['p_value'] and c['p_value']:
        change = c['p_value'] - p['p_value']
        if change < 0:
            print(f"{'':20} → p-value DECREASED by {abs(change):.4f} (more significant)")
        else:
            print(f"{'':20} → p-value INCREASED by {abs(change):.4f} (less significant)")

    print()

# Summary table
print("=" * 100)
print("SUMMARY: Did including Leif change statistical significance?")
print("=" * 100)
print()

for item in mood_items:
    results = analyze_mood_item(item, PARTICIPANT_SESSIONS, PARTICIPANT_SESSIONS + leif_sessions)

    p_sig = results['participants']['p_value'] and results['participants']['p_value'] < 0.05
    c_sig = results['combined']['p_value'] and results['combined']['p_value'] < 0.05

    if not p_sig and c_sig:
        print(f"✅ {item.upper():12} BECAME SIGNIFICANT when Leif included (p={results['combined']['p_value']:.4f})")
    elif p_sig and not c_sig:
        print(f"❌ {item.upper():12} LOST SIGNIFICANCE when Leif included (p={results['combined']['p_value']:.4f})")
    elif p_sig and c_sig:
        print(f"✓  {item.upper():12} Remained significant (participants: p={results['participants']['p_value']:.4f}, combined: p={results['combined']['p_value']:.4f})")
    else:
        p_val = results['participants']['p_value'] if results['participants']['p_value'] else float('inf')
        c_val = results['combined']['p_value'] if results['combined']['p_value'] else float('inf')
        trend = "↓ improved" if c_val < p_val else "↑ worse"
        print(f"   {item.upper():12} Not significant (participants: p={p_val:.4f}, combined: p={c_val:.4f}) {trend}")

print()
print("=" * 100)
print("INTERPRETATION NOTES")
print("=" * 100)
print()
print("Statistical test: One-sample t-test (H0: mean change = 0)")
print("Significance threshold: p < 0.05")
print()
print("Participant data alone (n=17):")
print("  - FOCUSED was significant (p=0.0041) in original analysis")
print("  - CALM was trending (p=0.0962)")
print("  - CONNECTED was not significant (p=0.1635)")
print()
print("Leif's contribution:")
print("  - CONNECTED: +0.62 average (vs participants +0.24)")
print("  - CALM: +0.38 average (vs participants +0.29)")
print("  - FOCUSED: +0.25 average (vs participants +0.41)")
print()
print("Expected impact of including Leif:")
print("  - CONNECTED: Should become MORE significant (Leif's +0.62 boosts average)")
print("  - FOCUSED: May become LESS significant (Leif's +0.25 dilutes participants' +0.41)")
print("  - CALM: Uncertain (Leif similar to participants)")
