# Complete Fix: Spectrogram Box Jumping Bug

**Date Fixed:** November 25, 2025  
**Affected Mode:** Logarithmic frequency scale only  
**Affected Condition:** Only when playbackRate ≠ 1.0

## Problem Description

When drawing feature boxes on the spectrogram in logarithmic frequency mode, boxes would "jump" to incorrect positions immediately after being drawn - but **ONLY** when playback speed was not 1x. At 1x playback, boxes appeared correctly.

**Symptoms:**
- User draws a box at a specific frequency range
- Box appears to jump to a different frequency range after mouse release
- Error increases as playbackRate deviates further from 1.0
- Most severe at slow playback speeds (< 1x)
- No issue at playbackRate = 1.0

## Root Cause

The bug was caused by a **mismatch between two inverse functions**:

1. **`getFrequencyFromY()`** - Converts Y pixel position → frequency (used when saving a drawn box)
2. **`getYPositionForFrequencyScaled()`** - Converts frequency → Y pixel position (used when displaying saved boxes)

These functions **MUST be mathematical inverses** - if you convert Y→freq→Y, you should get back the original Y position. They were correctly inverse for linear and sqrt scales, but **NOT for logarithmic**.

### The Broken Formula

The old `getFrequencyFromY()` used this incorrect stretch factor:

```javascript
// ❌ OLD (BROKEN) - Used MULTIPLICATION
const effectiveNyquist = maxFreq * playbackRate;
const stretchFactor = Math.log10(effectiveNyquist) / Math.log10(maxFreq);
```

### The Correct Formula

The display function `getYPositionForFrequencyScaled()` was already using the correct formula:

```javascript
// ✅ NEW (CORRECT) - Uses DIVISION
const targetMaxFreq = maxFreq / playbackRate;  // DIVISION, not multiplication!
const logMin = Math.log10(0.1);
const logMax = Math.log10(maxFreq);
const logRange = logMax - logMin;
const logTargetMax = Math.log10(Math.max(targetMaxFreq, minFreq));
const targetLogRange = logTargetMax - logMin;
const fraction = targetLogRange / logRange;
const stretchFactor = 1 / fraction;
```

**Why the difference matters:**
- At playbackRate = 1.0, both formulas give identical results (1.0)
- At other speeds, they diverge significantly:
  - 0.1x playback: 43.6% formula difference
  - 0.5x playback: 8.5% formula difference
  - 2.0x playback: 4.6% formula difference

## The Complete Fix

### Step 1: Fix `getFrequencyFromY()` in `js/region-tracker.js`

Replace the logarithmic case to use the **same stretch factor calculation** as `calculateStretchFactorForLog()`:

```javascript
function getFrequencyFromY(y, maxFreq, canvasHeight, scaleType, playbackRate = 1.0) {
    if (scaleType === 'logarithmic') {
        // 🦋 LOGARITHMIC: Must use SAME stretch factor as getYPositionForFrequencyScaled!
        // Forward: heightFromBottom_scaled = heightFromBottom_1x * stretchFactor
        // Inverse: heightFromBottom_1x = heightFromBottom_scaled / stretchFactor
        
        const minFreq = 0.1;
        const logMin = Math.log10(minFreq);
        const logMax = Math.log10(maxFreq);
        const logRange = logMax - logMin;

        // Calculate stretch factor using SAME formula as calculateStretchFactorForLog
        const targetMaxFreq = maxFreq / playbackRate;  // DIVISION, not multiplication!
        const logTargetMax = Math.log10(Math.max(targetMaxFreq, minFreq));
        const targetLogRange = logTargetMax - logMin;
        const fraction = targetLogRange / logRange;
        const stretchFactor = 1 / fraction;

        // Reverse: heightFromBottom_scaled → heightFromBottom_1x
        const heightFromBottom_scaled = canvasHeight - y;
        const heightFromBottom_1x = heightFromBottom_scaled / stretchFactor;

        // Convert heightFromBottom_1x back to frequency (in ORIGINAL scale, no playback!)
        const normalizedLog = heightFromBottom_1x / canvasHeight;
        const logFreq = logMin + (normalizedLog * (logMax - logMin));
        const freq = Math.pow(10, logFreq);

        // CLAMP to valid range [minFreq, maxFreq]
        return Math.max(minFreq, Math.min(maxFreq, freq));
    } else {
        // Linear and sqrt cases remain unchanged (they were already correct)
        // ... existing code ...
    }
}
```

### Step 2: Ensure `calculateStretchFactorForLog()` exists in `js/spectrogram-axis-renderer.js`

This function should already exist, but verify it matches:

```javascript
function calculateStretchFactorForLog(playbackRate, originalNyquist) {
    const minFreq = 0.1; // Match tick positioning (avoid log(0))
    const logMin = Math.log10(minFreq);
    const logMax = Math.log10(originalNyquist);
    const logRange = logMax - logMin;
    
    // Adapted from spectrogram stretch factor: targetMaxFreq = originalNyquist / playbackRate
    // At higher playbackRate, we show a smaller portion (zooming in on lower frequencies)
    const targetMaxFreq = originalNyquist / playbackRate;
    const logTargetMax = Math.log10(Math.max(targetMaxFreq, minFreq));
    const targetLogRange = logTargetMax - logMin;
    const fraction = targetLogRange / logRange;
    
    // Stretch to fill viewport: if showing fraction of log space, stretch by 1/fraction
    return 1 / fraction;
}
```

### Step 3: Add data provenance flag (optional but recommended)

Add a flag to newly saved features to indicate they use the corrected formula:

```javascript
// In handleSpectrogramSelection() or wherever features are saved:
feature.usesCorrectedLogFormula = true;
```

And add a global flag to JSON dumps:

```javascript
// In JSON dump creation:
jsonDump.usesCorrectedLogFormula = true;
```

## Files Modified

1. **`js/region-tracker.js`** - Fix `getFrequencyFromY()` logarithmic case (lines ~1784-1811)
2. **`js/ui-controls.js`** - Add `usesCorrectedLogFormula: true` flag to JSON dump (optional)

## Testing

Test the fix by:

1. **Set frequency scale to logarithmic**
2. **Set playback rate to non-1x** (e.g., 0.5x, 2x, 4x)
3. **Draw a feature box** on the spectrogram
4. **Verify the box stays in the correct position** after mouse release
5. **Change playback rate** - box should remain correctly positioned
6. **Zoom in/out** - box should remain correctly positioned
7. **Refresh page** - saved box should load in correct position

### Test Cases

| Playback Rate | Expected Behavior |
|---------------|-------------------|
| 0.1x | Box stays exactly where drawn (was most broken before) |
| 0.25x | Box stays exactly where drawn |
| 0.5x | Box stays exactly where drawn |
| 1.0x | Box stays exactly where drawn (was already working) |
| 2.0x | Box stays exactly where drawn |
| 4.0x | Box stays exactly where drawn |
| 8.0x | Box stays exactly where drawn |
| 15.0x | Box stays exactly where drawn |

## Key Principles

1. **Inverse functions must match**: `getFrequencyFromY()` and `getYPositionForFrequencyScaled()` must be exact mathematical inverses
2. **Use division, not multiplication**: `targetMaxFreq = maxFreq / playbackRate` (not `maxFreq * playbackRate`)
3. **Calculate stretch factor consistently**: Both functions must use the same `calculateStretchFactorForLog()` logic
4. **Test at non-1x speeds**: The bug only manifests when playbackRate ≠ 1.0

## Impact on Existing Data

Features saved **before this fix** in logarithmic mode at non-1x playback speeds have **incorrect frequency values** stored. See `docs/LOG_FREQUENCY_CONVERSION_CHANGE.md` for data correction formulas if you need to fix historical data.

## References

- **Full documentation**: `docs/LOG_FREQUENCY_CONVERSION_CHANGE.md`
- **Captain's log entry**: `docs/captains_logs/captains_log_2025-11-25.md` (lines 69-114)
- **Commit**: `15687c3` - "Fix logarithmic mode box jump bug - use matching stretch factor formula"



