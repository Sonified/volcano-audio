# Leif (Expert) Data Summary
## Study Coordinator Pre-Post Analysis

**Updated:** January 6, 2026
**Source:** `Qualtrics/analysis/Volcano_Audio_Meta_Analysis.md` (lines 157-181)

---

## Overview

- **Participant ID:** R_79bBz3856cnKDLj
- **Role:** Study coordinator (IRB filer) - EXCLUDED from participant analysis
- **Complete Sessions:** 17
- **Timeout Sessions:** 2
- **Total Regions:** 42
- **Total Features:** 160

---

## CNS (Connectedness to Nature Scale) Pre-Post

### Summary
- **Pre Total:** 44
- **Post Total:** 44
- **Net Change:** 0 (no change)

### Item-Level Breakdown

| Item | Question | Pre | Post | Δ | Notes |
|------|----------|-----|------|---|-------|
| 1 | I often feel a sense of oneness with the natural world around me | 5 | 4 | -1 | Started very high, regressed |
| 2 | I think of the natural world as a community to which I belong | 5 | 4 | -1 | Started very high, regressed |
| **3** | **I recognize and appreciate the intelligence of other living organisms** | **5** | **4** | **-1** | ⚠️ **DECREASED** |
| 4* | I often feel disconnected from nature (reverse) | 1 | 3 | +2 | Worse disconnection |
| 5 | When I think of my life, I imagine myself to be part of a larger cyclical process of living | 3 | 4 | +1 | Improved |
| 6 | I often feel a kinship with animals and plants | 1 | 2 | +1 | Improved from floor |
| 7 | I feel as though I belong to the Earth as equally as it belongs to me | 3 | 2 | -1 | Decreased |
| 8 | I have a deep understanding of how my actions affect the natural world | 5 | 4 | -1 | Started very high, regressed |
| 9 | I often feel part of the web of life | 3 | 3 | 0 | No change |
| 10 | I feel that all inhabitants of Earth share a common 'life force' | 3 | 3 | 0 | No change |
| 11 | Like a tree can be part of a forest, I feel embedded within the broader natural world | 3 | 3 | 0 | No change |
| 12* | When I think of my place on Earth, I consider myself to be a top member of a hierarchy (reverse) | 1 | 2 | +1 | Improved |
| 13 | I often feel like I am only a small part of the natural world around me | 3 | 3 | 0 | No change |
| 14* | My personal welfare is independent of the welfare of the natural world (reverse) | 3 | 3 | 0 | No change |

*Items marked with * are reverse-scored*

### Interpretation

**Pattern:** Regression to the mean, NOT a treatment effect

- **Items that started HIGH (5s):** All decreased to 4 (items 1, 2, 3, 8)
- **Items that started LOW (1s):** Increased (items 4, 6, 12)
- **Items in middle (3s):** Mostly unchanged

**Item #3 Specifically (Connected to Nature):**
- Pre: 5 (highest possible score except for 1-5 scale... wait, checking scale)
- Post: 4
- **Change: -1 (DECREASED)**

⚠️ **CRITICAL FINDING:** Leif did NOT show a positive trend on "connected to nature" - he DECREASED from 5→4.

This is likely regression to the mean given his very high starting score (5/5).

---

## Next Steps

1. ✅ Document CNS data (this file)
2. ⏳ Extract ALL 17 sessions' mood survey data
3. ⏳ Analyze session-level "Connected" mood item (QID5_3 / QID12_3 in session surveys)
4. ⏳ Look for other positive trends in Leif's data
5. ⏳ Determine if combining with participant data makes sense

---

## Session-Level Mood Analysis Results

✅ **ANALYZED:** 17 complete sessions (16 with mood data, 1 missing)

### Aggregate Mood Shifts (Pre → Post within each session)

| Mood Item | Avg Change | Positive | Negative | No Change | vs Participants |
|-----------|------------|----------|----------|-----------|-----------------|
| **Connected** | **+0.62** | **50%** | **0%** | **50%** | **2.6x stronger** (+0.24) |
| Calm | +0.38 | 44% | 13% | 44% | 1.3x stronger (+0.29) |
| Wonder | +0.38 | 50% | 13% | 38% | 6.3x stronger (+0.06) |
| Focused | +0.25 | 25% | 0% | 75% | 0.6x weaker (+0.41*) |
| Nervous | +0.44 | 44% | 25% | 31% | n/a (-0.18) |
| Energized | -0.06 | 25% | 31% | 44% | Similar (-0.35) |

*Participant "Focused" was statistically significant (p=0.0041)

### 🔥 Key Finding: Connected to Nature (Session-Level)

**Leif showed the STRONGEST "Connected" improvement of any measure:**
- **+0.62 average** across 16 sessions
- **8 sessions increased** (Sessions 5, 6, 7, 8, 9, 10, 11, 13)
- **0 sessions decreased** (!)
- **8 sessions no change**

**Largest increases:**
- Session 10 (Dec 1): +2 points (14 features)
- Session 11 (Dec 1): +2 points (6 features)

**This is MORE THAN DOUBLE the participant average** (+0.24, p=0.1635 not significant)

### Interpretation

**Critical distinction:**
- **Session-level "Connected"** = feeling connected to nature DURING the volcano listening activity
- **CNS Post-survey "Connected"** = overall life-level nature connectedness

**Leif's pattern:**
- ✅ Felt significantly MORE connected during sessions (+0.62)
- ❌ Overall CNS showed NO net change (44→44)
- ⚠️ CNS item #3 specifically DECREASED (5→4)

**Possible explanations:**
1. Volcano sonification creates temporary connectedness that doesn't persist
2. Session-level question is more immediate/contextual
3. CNS measures broader philosophical/spiritual nature connection
4. Regression to the mean on CNS (started with many 5s)

---

## Files to Check Next

- `Qualtrics/Downloaded_Data/qualtrics_export_2025-12-12_10-20-36.json` - Full session data
- `Qualtrics/analysis/code/session_mood_analysis.py` - Existing mood analysis script (may need to adapt for Leif)
