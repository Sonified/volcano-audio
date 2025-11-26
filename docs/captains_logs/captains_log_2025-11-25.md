# Captain's Log - November 25, 2025

## Critical Bug Fix: R2 Backup for Successful Sessions

### Discovery
Through testing with collaborator Leif at UOregon, discovered that R2 was only capturing timeout/incomplete sessions, not successful completions. Leif's Qualtrics data showed complete, rich participant responses with features and annotations, but R2 backup was nearly empty or only had timeout failures.

### Root Cause
The `attemptSubmission()` function (used for all successful study completions) was missing the R2 upload step entirely. Only the timeout path in `session-management.js` was uploading to R2.

Additionally, found dead code: `checkAndSubmitIfComplete()` function that attempted to upload to R2 but referenced an undefined variable (`jsonDump`), causing silent failures. This function was never called anywhere in the codebase.

### The Fix
**Commit:** `6e25190` - "Fix: Enable R2 backup for successful session completions"

**Changes:**
1. Added R2 upload step in `attemptSubmission()` immediately after successful Qualtrics submission
2. Upload wrapped in try-catch to ensure it's non-blocking (Qualtrics is primary, R2 is backup)
3. Removed 57 lines of dead code (`checkAndSubmitIfComplete()` function)

**Files Modified:**
- `js/ui-controls.js` (+11 lines, -63 lines)

### Testing Results
Created test submission `TEST_ROBERT_11_25_25` with:
- ✅ 3 regions with full metadata
- ✅ 4 features with types, frequencies, notes, timestamps
- ✅ All 4 survey responses (pre, post, awesf, activityLevel)
- ✅ 10 tracking events
- ✅ 6,192 bytes of complete JSON data on R2

### Impact
- **Before:** R2 only captured incomplete/timeout sessions with minimal data
- **After:** R2 now captures complete participant data for successful completions
- **Primary submission (Qualtrics):** Unaffected - was working perfectly all along
- **Benefit:** Full backup of rich participant data now available on R2 for monitoring and redundancy

### Key Insight
The main study functionality was working perfectly - Leif was receiving complete data. The bug only affected our internal monitoring/backup system. This is why it went undetected - the primary feature (Qualtrics submission) never failed.

---

**Status:** ✅ Fixed and deployed  
**Tested:** ✅ Verified with live submission to R2  
**Pushed:** ✅ Commit 6e25190 to main branch


---

## v2.69 - Tutorial Flow Fixes

### Changes Made
1. **Fixed `waitForRegionCreation()`** - Now accepts `expectedCount` parameter to properly wait for second region (was immediately resolving because first region existed)
2. **Fixed `waitForFeatureSelection()`** - Same pattern: now counts complete features and waits for count > expected
3. **Timing adjustments in `runFeatureSelectionTutorial()`:**
   - Repetition dropdown pause: 1s → 3s
   - Type dropdown pause: 1s → 3s
   - "Feel free to change the playback speed!" duration: 10s → 5s
   - "Pick a scaling that works well..." duration: 5s → 4s
   - "Have a look and listen..." duration: 8s → 7s
4. **CSS adjustment:** Made repetition and type dropdowns 10px wider each (description box 20px shorter)
5. **Removed redundant message:** "Continue your analysis and hit Submit when you are done" - now just says "This Tutorial is now complete!"
6. **Fixed post-tutorial zoom out message:** Now shows "Press the Complete button when you are ready to share your findings."

**Pushed:** v2.69 Tutorial: Fixed second feature/region flow, timing adjustments, removed redundant message

---

## Critical Bug Fix: Logarithmic Frequency Conversion

### Discovery
While testing feature box drawing in logarithmic mode, discovered that boxes would "jump" to a different location after being drawn - but ONLY when playback speed was not 1x.

### Root Cause
The Y-to-frequency conversion function (`getFrequencyFromY` in `region-tracker.js`) was using a DIFFERENT stretch factor formula than the frequency-to-Y display function (`getYPositionForFrequencyScaled` in `spectrogram-axis-renderer.js`).

**OLD (broken) formula:**
```javascript
stretchFactor = log10(maxFreq * playbackRate) / log10(maxFreq)
```

**NEW (correct) formula:**
```javascript
targetMaxFreq = maxFreq / playbackRate  // DIVISION not multiplication!
fraction = (log10(targetMaxFreq) - log10(0.1)) / (log10(maxFreq) - log10(0.1))
stretchFactor = 1 / fraction
```

At playbackRate = 1.0, both formulas give 1.0 (no error). But at other speeds they diverge:
- 0.1x playback: 43.6% formula difference
- 0.5x playback: 8.5% formula difference  
- 2.0x playback: 4.6% formula difference

### Impact on Saved Data
**Features saved in logarithmic mode at non-1x playback speeds have incorrect `lowFreq` and `highFreq` values.** The stored frequencies don't match what the user actually selected.

### The Fix
1. Fixed `getFrequencyFromY()` to use the same stretch factor calculation as `calculateStretchFactorForLog()`
2. Added `usesCorrectedLogFormula: true` flag to all newly saved features for data provenance
3. Created comprehensive documentation with data correction formula

### Files Modified
- `js/region-tracker.js` - Fixed logarithmic case + added flag
- `docs/LOG_FREQUENCY_CONVERSION_CHANGE.md` - Full documentation with Python/JS correction formulas
- `tests/test_log_frequency_correction.py` - Validates correction formula works for 0.1x to 15x playback

### Commits
1. `15687c3` - "Fix logarithmic mode box jump bug - use matching stretch factor formula"
2. (pending) - Documentation, flag, and test additions

**Status:** ✅ Fixed  
**Documentation:** ✅ Complete with data correction formulas  
**Tests:** ✅ All passing for 0.1x to 15x playback range

---

## Bug Fix: Frequency Scale Not Propagating on Zoom Out

### Discovery
When changing the frequency scale (linear/sqrt/log) while zoomed into a region, the zoomed-in view would update correctly. However, when zooming out to full view, the main canvas would still show the OLD frequency scale.

### Root Cause
The `cachedFullSpectrogramCanvas` (nicknamed the "elastic friend") is cached when the full spectrogram is first rendered. When zooming out, `restoreInfiniteCanvasFromCache()` restores from this cached canvas. 

**The problem:** When frequency scale changed while zoomed in, only the region spectrogram was re-rendered. The cached full spectrogram was never updated, so zooming out would restore the stale cache with the old frequency scale.

### The Fix
**Proactive approach:** Re-render the full spectrogram in the background immediately after the region frequency scale change completes.

**Changes:**
1. Added `cachedFullFrequencyScale` variable to track which scale the elastic friend was rendered with
2. Added `forceFullView` parameter to `renderCompleteSpectrogram()` - bypasses region check and "already rendered" check
3. Created `updateElasticFriendInBackground()` - calls `renderCompleteSpectrogram(true, true)` after region scale change
4. After region frequency scale fade completes, kicks off background re-render of full spectrogram

**Files Modified:**
- `js/spectrogram-complete-renderer.js` - Added `forceFullView` param, tracking variable, and background update function
- `js/spectrogram-renderer.js` - Call `updateElasticFriendInBackground()` after region scale transition completes

### Flow After Fix
```
Change frequency scale (while zoomed in)
    ↓
Region re-renders + fades in (visible to user)
    ↓
Background: Full spectrogram re-renders (invisible)
    ↓
Elastic friend updated with new scale ✅
    ↓
User zooms out → elastic friend has correct scale! 🎯
```

**Status:** ✅ Fixed  
**Version:** v2.70

---

## Critical Bug Fix: Session Timeout Ignoring User Activity

### Discovery
User was actively interacting with the display for 21 minutes, refreshed the page, and immediately got the timeout screen. Console showed:
```
⏰ Session timeout detected: 21.1 minutes elapsed
```

### Root Cause
The on-reload timeout check in `study-workflow.js` was comparing against `sessionStartTime` instead of actual last activity time:

```javascript
// BROKEN - using session START time, not last ACTIVITY time!
const lastActivityTime = new Date(sessionStartTime).getTime();
const inactiveTime = now - lastActivityTime;
```

Meanwhile, `session-management.js` was correctly tracking activity in memory via mousemove/click/keydown events, BUT that in-memory `lastActivityTime` was never persisted to localStorage. On page refresh, the in-memory value was lost, and the reload check fell back to session start time.

### The Fix

1. **Added `LAST_ACTIVITY_TIME` storage key** - Persists last activity timestamp to localStorage
2. **Throttled activity detection to 1 second** - Prevents running localStorage.setItem() hundreds of times per second on mousemove
3. **Fixed reload check to use persisted activity time** - Now reads `LAST_ACTIVITY_TIME` instead of `CURRENT_SESSION_START`
4. **Added inactivity debug logging** - Console shows `⏱️ Inactivity: Xm Ys` every minute

**Files Modified:**
- `js/session-management.js` - Activity throttling + localStorage persistence
- `js/study-workflow.js` - Added storage key + fixed reload check

### How Activity Tracking Now Works
1. User moves mouse/clicks/types → `resetActivityTimer()` called
2. Throttle check: Has 1 second passed since last check? No → return early
3. Yes → Update in-memory time + write to localStorage
4. On page reload → Read persisted activity time, not session start
5. Debug log every 60s: `⏱️ Inactivity: 0m 45s`

**Status:** ✅ Fixed  
**Version:** v2.70
