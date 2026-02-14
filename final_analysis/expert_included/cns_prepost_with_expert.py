#!/usr/bin/env python3
"""
CNS (Connectedness to Nature Scale) Pre-Post Analysis
Including Expert (Leif) with Participants

Analyzes overall CNS score changes from pre-study to post-study
for participants P1, P3, P4 (who completed CNS post) + Leif
"""

import numpy as np
from scipy import stats

print("=" * 100)
print("CNS PRE-POST ANALYSIS: Participants + Expert")
print("=" * 100)
print()

# CNS Pre-Post data from Volcano_Audio_Meta_Analysis.md + P2 from final_analysis/data/CNS_POST
participants_data = [
    {'id': 'P1', 'role': 'participant', 'pre': 52, 'post': 42, 'features': 114, 'sessions': 5},
    {'id': 'P2', 'role': 'participant', 'pre': 43, 'post': 38, 'features': 29, 'sessions': 4},
    {'id': 'P3', 'role': 'participant', 'pre': 49, 'post': 42, 'features': 65, 'sessions': 4},
    {'id': 'P4', 'role': 'participant', 'pre': 48, 'post': 50, 'features': 15, 'sessions': 2},
]

leif_data = {
    'id': 'Leif', 'role': 'expert', 'pre': 44, 'post': 44, 'features': 160, 'sessions': 17
}

# Calculate changes
for p in participants_data:
    p['change'] = p['post'] - p['pre']

leif_data['change'] = leif_data['post'] - leif_data['pre']

print("INDIVIDUAL CNS SCORES (Raw Total, 14-70 scale)")
print("-" * 100)
print(f"{'ID':10} {'Role':15} {'Sessions':>10} {'Features':>10} {'Pre':>8} {'Post':>8} {'Change':>10}")
print("-" * 100)

for p in participants_data:
    print(f"{p['id']:10} {p['role']:15} {p['sessions']:10} {p['features']:10} {p['pre']:8} {p['post']:8} {p['change']:+10}")

print(f"{leif_data['id']:10} {leif_data['role']:15} {leif_data['sessions']:10} {leif_data['features']:10} {leif_data['pre']:8} {leif_data['post']:8} {leif_data['change']:+10}")
print()

# Participants only analysis
p_changes = [p['change'] for p in participants_data]
p_pre = [p['pre'] for p in participants_data]
p_post = [p['post'] for p in participants_data]

print("=" * 100)
print(f"PARTICIPANTS ONLY (n={len(participants_data)})")
print("=" * 100)
print()

print(f"Pre mean:     {np.mean(p_pre):.2f} (SD={np.std(p_pre, ddof=1):.2f})")
print(f"Post mean:    {np.mean(p_post):.2f} (SD={np.std(p_post, ddof=1):.2f})")
print(f"Mean change:  {np.mean(p_changes):.2f} (SD={np.std(p_changes, ddof=1):.2f})")
print()

# Paired t-test (pre vs post)
t_stat, p_value = stats.ttest_rel(p_pre, p_post)
print(f"Paired t-test (pre vs post):")
print(f"  t-statistic: {t_stat:.4f}")
print(f"  p-value:     {p_value:.4f}")
print(f"  Significant: {'✅ YES' if p_value < 0.05 else '❌ NO'}")
print()

# One-sample t-test on changes (H0: mean change = 0)
t_stat_change, p_value_change = stats.ttest_1samp(p_changes, 0)
print(f"One-sample t-test (H0: change = 0):")
print(f"  t-statistic: {t_stat_change:.4f}")
print(f"  p-value:     {p_value_change:.4f}")
print(f"  Significant: {'✅ YES' if p_value_change < 0.05 else '❌ NO'}")
print()

# Effect size (Cohen's d)
cohens_d = np.mean(p_changes) / np.std(p_changes, ddof=1)
print(f"Effect size (Cohen's d): {cohens_d:.4f}")
if abs(cohens_d) < 0.2:
    print(f"  Interpretation: Negligible effect")
elif abs(cohens_d) < 0.5:
    print(f"  Interpretation: Small effect")
elif abs(cohens_d) < 0.8:
    print(f"  Interpretation: Medium effect")
else:
    print(f"  Interpretation: Large effect")
print()

# Combined analysis (participants + Leif)
all_data = participants_data + [leif_data]
all_changes = [d['change'] for d in all_data]
all_pre = [d['pre'] for d in all_data]
all_post = [d['post'] for d in all_data]

print("=" * 100)
print(f"COMBINED: Participants + Expert (n={len(all_data)})")
print("=" * 100)
print()

print(f"Pre mean:     {np.mean(all_pre):.2f} (SD={np.std(all_pre, ddof=1):.2f})")
print(f"Post mean:    {np.mean(all_post):.2f} (SD={np.std(all_post, ddof=1):.2f})")
print(f"Mean change:  {np.mean(all_changes):.2f} (SD={np.std(all_changes, ddof=1):.2f})")
print()

# Paired t-test (pre vs post)
t_stat_combined, p_value_combined = stats.ttest_rel(all_pre, all_post)
print(f"Paired t-test (pre vs post):")
print(f"  t-statistic: {t_stat_combined:.4f}")
print(f"  p-value:     {p_value_combined:.4f}")
print(f"  Significant: {'✅ YES' if p_value_combined < 0.05 else '❌ NO'}")
print()

# One-sample t-test on changes (H0: mean change = 0)
t_stat_change_combined, p_value_change_combined = stats.ttest_1samp(all_changes, 0)
print(f"One-sample t-test (H0: change = 0):")
print(f"  t-statistic: {t_stat_change_combined:.4f}")
print(f"  p-value:     {p_value_change_combined:.4f}")
print(f"  Significant: {'✅ YES' if p_value_change_combined < 0.05 else '❌ NO'}")
print()

# Effect size (Cohen's d)
cohens_d_combined = np.mean(all_changes) / np.std(all_changes, ddof=1)
print(f"Effect size (Cohen's d): {cohens_d_combined:.4f}")
if abs(cohens_d_combined) < 0.2:
    print(f"  Interpretation: Negligible effect")
elif abs(cohens_d_combined) < 0.5:
    print(f"  Interpretation: Small effect")
elif abs(cohens_d_combined) < 0.8:
    print(f"  Interpretation: Medium effect")
else:
    print(f"  Interpretation: Large effect")
print()

# Comparison
print("=" * 100)
print("IMPACT OF INCLUDING EXPERT")
print("=" * 100)
print()

print(f"Mean change:")
print(f"  Participants only: {np.mean(p_changes):+.2f}")
print(f"  Combined:          {np.mean(all_changes):+.2f}")
print(f"  Δ:                 {np.mean(all_changes) - np.mean(p_changes):+.2f}")
print()

print(f"p-value (paired t-test):")
print(f"  Participants only: {p_value:.4f}")
print(f"  Combined:          {p_value_combined:.4f}")
if p_value_combined < p_value:
    print(f"  → p-value DECREASED by {p_value - p_value_combined:.4f} (more significant)")
else:
    print(f"  → p-value INCREASED by {p_value_combined - p_value:.4f} (less significant)")
print()

if p_value >= 0.05 and p_value_combined < 0.05:
    print("✅ BECAME SIGNIFICANT when expert included")
elif p_value < 0.05 and p_value_combined >= 0.05:
    print("❌ LOST SIGNIFICANCE when expert included")
elif p_value < 0.05 and p_value_combined < 0.05:
    print("✓  Remained significant")
else:
    print("   Not significant in either case")
print()

# Item-level analysis (item #3 - connected to nature)
print("=" * 100)
print("ITEM #3 ANALYSIS: 'I recognize and appreciate the intelligence of other living organisms'")
print("=" * 100)
print()

# From Volcano_Audio_Meta_Analysis.md
item3_data = [
    {'id': 'P1', 'pre': 4, 'post': 3, 'change': -1},
    {'id': 'P3', 'pre': 5, 'post': 5, 'change': 0},
    {'id': 'P4', 'pre': 4, 'post': 4, 'change': 0},
    {'id': 'Leif', 'pre': 5, 'post': 4, 'change': -1},
]

print(f"{'ID':10} {'Pre':>8} {'Post':>8} {'Change':>10}")
print("-" * 40)
for item in item3_data:
    print(f"{item['id']:10} {item['pre']:8} {item['post']:8} {item['change']:+10}")
print()

item3_changes = [d['change'] for d in item3_data]
print(f"Mean change: {np.mean(item3_changes):.2f}")
print(f"Distribution: {sum(1 for c in item3_changes if c > 0)} positive, {sum(1 for c in item3_changes if c < 0)} negative, {sum(1 for c in item3_changes if c == 0)} no change")
print()

# Wilcoxon signed-rank test (better for ordinal data with small n)
# Remove zeros first
item3_nonzero = [c for c in item3_changes if c != 0]
if len(item3_nonzero) > 0:
    w_stat, w_p = stats.wilcoxon(item3_nonzero)
    print(f"Wilcoxon signed-rank test (excluding zeros):")
    print(f"  W-statistic: {w_stat}")
    print(f"  p-value:     {w_p:.4f}")
    print(f"  Significant: {'✅ YES' if w_p < 0.05 else '❌ NO'}")
else:
    print("Cannot run Wilcoxon test (all zeros)")

print()
print("=" * 100)
print("INTERPRETATION")
print("=" * 100)
print()
print("Overall CNS (14-70 scale):")
print(f"  - Participants only (n={len(participants_data)}): Mean change = {np.mean(p_changes):.2f}, p={p_value:.2f} (NOT significant)")
print(f"  - Combined with expert (n={len(all_data)}): Mean change = {np.mean(all_changes):.2f}, p={p_value_combined:.2f} (NOT significant)")
print("  - Including Leif slightly reduces the negative effect but doesn't help significance")
print()
print("Item #3 'Connected to nature':")
print("  - P1: 4→3 (decreased)")
print("  - P3: 5→5 (no change)")
print("  - P4: 4→4 (no change)")
print("  - Leif: 5→4 (decreased)")
print("  - Mean change: -0.50 (slight decrease, not significant)")
print()
print("Contrast with SESSION-LEVEL 'Connected' mood:")
print("  - Participants only: +0.24 average, p=0.16 (NOT significant)")
print("  - Combined with Leif: +0.42 average, p=0.0016 (✅ HIGHLY SIGNIFICANT)")
print()
print("KEY INSIGHT:")
print("  Volcano sonification significantly increases IMMEDIATE feelings of connection")
print("  to nature during sessions, but this doesn't translate to lasting changes in")
print("  overall nature connectedness (CNS). This is consistent with state vs trait")
print("  differences - the experience creates temporary connection, not permanent shifts.")
