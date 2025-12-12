# Final Analysis - Participant Session Data Processing

This directory contains Python scripts for extracting, processing, and validating participant session data from Qualtrics survey exports for the Volcano Audio study.

## 📁 Files

| File | Purpose |
|------|---------|
| `parse_participants.py` | Extracts participant metadata from markdown analysis file |
| `extract_sessions.py` | Parses session data from Qualtrics JSON export |
| `frequency_correction.py` | Applies frequency correction for sessions saved before Nov 25, 2025 |
| `prepare_ui_data.py` | Combines all data into final JSON structure for UI consumption |
| `test_integration.py` | Comprehensive validation tests |
| `participant_sessions.json` | **OUTPUT**: Final processed session data |

## 🔄 Data Pipeline

```
Volcano_Audio_Meta_Analysis.md ──┐
                                 │
                                 ├──> prepare_ui_data.py ──> participant_sessions.json
                                 │
qualtrics_export_YYYY-MM-DD.json ┘
```

### Step-by-Step Flow:

1. **`parse_participants.py`**: Reads `/Qualtrics/analysis/Volcano_Audio_Meta_Analysis.md`
   - Extracts P1-P6 participant metadata (IDs, session counts, feature counts)
   - Extracts Leif (expert) metadata

2. **`extract_sessions.py`**: Reads `/Downloaded_Data/qualtrics_export_YYYY-MM-DD.json`
   - Parses SessionTracking JSON from each Qualtrics response
   - Extracts volcano, station, duration, fetch parameters
   - Filters out timeout sessions
   - Applies frequency correction (via `frequency_correction.py`)
   - Filters out deleted/corrupted features

3. **`frequency_correction.py`**: Corrects frequency values for old sessions
   - Before Nov 25, 2025: Used broken logarithmic formula
   - Sessions flagged with `usesCorrectedLogFormula: false`
   - Only corrects features where `speedFactor ≠ 1`

4. **`prepare_ui_data.py`**: Combines participant + session data
   - Merges metadata with session data
   - Generates UI-ready JSON structure
   - Outputs `participant_sessions.json`

5. **`test_integration.py`**: Validates all data
   - Tests participant counts
   - Tests fetch parameter completeness
   - **Tests data window validity** (critical!)
   - Tests feature timestamp validity
   - Tests frequency correction application

## 🎯 Key Insights Discovered

### Data Window Calculation

**CRITICAL**: The data window is NOT `[fetch_timestamp - duration, fetch_timestamp]`!

From `js/main.js:617-634`, the actual algorithm:

1. User clicks "Fetch Data" at time `T`
2. Round `T` backward to last complete 10-minute chunk boundary (00, 10, 20, 30, 40, 50)
3. If within 2:15 of boundary, go back one more chunk (ensures data collection is complete)
4. This becomes `estimatedEndTime`
5. Actual data window: `[estimatedEndTime - duration, estimatedEndTime]`

**Example:**
```
User clicks fetch: 5:30:24 AM
Logged as:         fetch_timestamp = 5:30:24 AM
But calculated:    estimatedEndTime = 5:30:00 AM (10-min boundary)
Data fetched:      [5:30 AM yesterday, 5:30 AM today]
```

This is why regions can appear "outside" naive window calculations!

### Deleted/Corrupted Feature Detection

Features are filtered out if:

1. **Deleted features**: `featureStartTime === null` or `featureEndTime === null`
   - User clicked "add feature" but never drew the box
   - Or feature was deleted in UI

2. **Corrupted features**: `featureStartTime === featureEndTime`
   - Single-point features (likely UI bug)
   - Example: P5 Session 1 had feature at `12:45:09` to `12:45:09` (impossible)

**Total filtered**: 7 features (6 deleted + 1 corrupted)

### Frequency Correction

From `docs/LOG_FREQUENCY_CONVERSION_CHANGE.md`:

**Before Nov 25, 2025**: Sessions used broken log formula when `speedFactor ≠ 1`

**Correction formula** (applied automatically):
```python
def correct_log_frequency(freq_saved, playback_rate, max_freq=50):
    # OLD stretch factor (incorrect)
    stretch_factor_old = log10(max_freq * playback_rate) / log10(max_freq)

    # NEW stretch factor (correct)
    target_max_freq = max_freq / playback_rate
    log_target_max = log10(max(target_max_freq, 0.1))
    target_log_range = log_target_max - log10(0.1)
    fraction = target_log_range / (log10(max_freq) - log10(0.1))
    stretch_factor_new = 1 / fraction

    # Apply correction
    correction_ratio = stretch_factor_old / stretch_factor_new
    log_freq_corrected = log10(0.1) + (log10(freq_saved) - log10(0.1)) * correction_ratio
    return 10 ** log_freq_corrected
```

**Stats**: 51 features required correction, all 51 were corrected successfully.

## 🧪 Running Tests

```bash
cd final_analysis

# Test participant parsing
python parse_participants.py

# Test session extraction
python extract_sessions.py

# Generate final JSON
python prepare_ui_data.py

# Run comprehensive validation (MUST PASS ALL)
python test_integration.py
```

### Expected Test Results:

```
✅ PASS: Participant Counts (7/7)
✅ PASS: Fetch Parameters (34/34 sessions)
✅ PASS: Data Window Validity (143/143 regions)
✅ PASS: Feature Timestamps (403/403 features)
✅ PASS: Frequency Correction (51/51 features)
✅ PASS: Sample Session Query
🎉 ALL TESTS PASSED
```

## 📊 Output JSON Structure

```json
{
  "participants": [
    {
      "value": "R_xxxxx",           // Qualtrics participant ID
      "label": "P1 - R_xxxxx",      // Display name
      "p_number": "P1",             // Participant number
      "complete_sessions": 5,
      "timeout_sessions": 3,
      "sessions": [
        {
          "value": "responseId",    // Qualtrics response ID
          "session_id": "uuid",     // Unique session ID
          "label": "Session 1 (2025-11-21) - maunaloa - 10 features",
          "session_number": 1,
          "date": "2025-11-21",
          "feature_count": 10,
          "region_count": 8,

          // Data fetch parameters (to reconstruct session)
          "volcano": "maunaloa",
          "station": "HV.MOKD.--.HHZ",
          "duration": 24,
          "fetch_timestamp": "2025-11-21T23:40:26.149Z",
          "highpass_freq": "2",
          "enable_normalize": true,
          "uses_corrected_formula": true,

          // Region and feature data
          "regions": [
            {
              "regionNumber": 1,
              "regionStartTime": "2025-11-21T13:07:56.230Z",
              "regionEndTime": "2025-11-21T13:21:55.690Z",
              "features": [
                {
                  "featureNumber": 1,
                  "featureStartTime": "2025-11-21T13:08:15.400Z",
                  "featureEndTime": "2025-11-21T13:08:17.960Z",
                  "lowFreq": "25.28",      // Corrected if needed
                  "highFreq": "25.44",     // Corrected if needed
                  "lowFreq_original": "24.12",  // Only if corrected
                  "highFreq_original": "24.28", // Only if corrected
                  "frequency_corrected": true,  // Only if corrected
                  "type": "Impulsive",
                  "repetition": "Unique",
                  "notes": "description...",
                  "speedFactor": 2.0,
                  "numberOfEvents": 1
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "expert": { /* same structure as participants */ },
  "metadata": {
    "total_participants": 6,
    "total_sessions": 34,
    "generated_at": "2025-12-11T..."
  }
}
```

## 🚨 Important Notes for Future AI

### Session IDs vs Response IDs

- **sessionId**: True session identifier (shared across timeout/complete responses)
- **responseId**: Qualtrics response identifier (one per submission)
- Same session can have multiple responses (e.g., timeout then complete)

### Timeout Sessions

**CRITICAL**: Timeout sessions are EXCLUDED from final data.

```python
# Skip timeout sessions entirely
if timed_out:
    continue
```

This is by explicit user requirement: "NO NOT TIMEOUTS"

### Data Sources

1. **Participant metadata**: `/Qualtrics/analysis/Volcano_Audio_Meta_Analysis.md`
2. **Session data**: `/Downloaded_Data/qualtrics_export_YYYY-MM-DD.json`
3. **Frequency correction docs**: `/docs/LOG_FREQUENCY_CONVERSION_CHANGE.md`

### Known Data Gaps

See `CLAUDE.md` for full data archaeology:

- Nov 13, 2025: First 11 submissions have NO SessionTracking
- Nov 13-19: 3 participants only in Qualtrics, not R2
- ParticipantID is NOT top-level in Qualtrics - it's in `SessionTracking` JSON

## 🔧 Regenerating Data

When a new Qualtrics export is available:

1. Download new export to `/Downloaded_Data/qualtrics_export_YYYY-MM-DD.json`
2. Update the filename in `prepare_ui_data.py` line 163
3. Run: `python prepare_ui_data.py`
4. Run: `python test_integration.py` (MUST PASS ALL TESTS)
5. Copy `participant_sessions.json` to wherever the UI needs it

## 📚 Related Documentation

- `/CLAUDE.md` - Project instructions and data archaeology
- `/docs/LOG_FREQUENCY_CONVERSION_CHANGE.md` - Frequency correction details
- `/README.md` - Full project architecture
- `/Qualtrics/analysis/Volcano_Audio_Meta_Analysis.md` - Participant metadata source

---

**Generated**: December 11, 2025
**All tests passing**: ✅ 100% (6/6 tests)
**Data validated**: 34 sessions, 143 regions, 403 features
