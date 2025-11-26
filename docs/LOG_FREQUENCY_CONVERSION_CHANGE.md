# Logarithmic Frequency Conversion Bug Fix

**Date Fixed:** 2025-11-25  
**Affected Mode:** Logarithmic frequency scale only  
**Affected Condition:** Only when playbackRate ≠ 1.0

## Summary

A bug was discovered where feature boxes drawn in logarithmic mode at non-1x playback speeds would "jump" to incorrect positions. Investigation revealed the Y-to-frequency conversion was using a different stretch factor formula than the frequency-to-Y display function, causing frequency values to be saved incorrectly.

## The Bug

When a user draws a feature box, `getFrequencyFromY()` converts the Y pixel position to a frequency value that gets saved. When displaying the box, `getYPositionForFrequencyScaled()` converts that frequency back to a Y position.

**These two functions MUST be mathematical inverses.** They were for linear and sqrt scales, but NOT for logarithmic.

## The Formulas

### OLD (Broken) Stretch Factor in `getFrequencyFromY`:
```javascript
const effectiveNyquist = maxFreq * playbackRate;  // MULTIPLICATION
const stretchFactor_OLD = Math.log10(effectiveNyquist) / Math.log10(maxFreq);
// Simplified: log10(N * p) / log10(N)
```

### NEW (Correct) Stretch Factor (matches `calculateStretchFactorForLog`):
```javascript
const minFreq = 0.1;
const logMin = Math.log10(minFreq);  // = -1
const logMax = Math.log10(maxFreq);  // = log10(50) ≈ 1.699 for 50 Hz Nyquist
const logRange = logMax - logMin;

const targetMaxFreq = maxFreq / playbackRate;  // DIVISION (not multiplication!)
const logTargetMax = Math.log10(targetMaxFreq);
const targetLogRange = logTargetMax - logMin;
const fraction = targetLogRange / logRange;
const stretchFactor_NEW = 1 / fraction;
```

### Example Values (Nyquist = 50 Hz)

| playbackRate | Formula Difference | Impact |
|--------------|-------------------|--------|
| 0.1x         | 43.6%             | Severe - frequencies WAY off |
| 0.25x        | 21.0%             | Significant |
| 0.5x         | 8.5%              | Noticeable |
| 1.0x         | 0.0%              | ✓ No error |
| 2.0x         | 4.6%              | Moderate |
| 4.0x         | 5.2%              | Moderate |
| 8.0x         | 1.9%              | Minor |
| 15.0x        | 4.5%              | Moderate |

**At playbackRate = 1.0, both formulas give identical results.** This is why the bug only manifests when playback speed is changed. The error is most severe at slow playback speeds (< 1x).

## Impact on Saved Data

Features saved in logarithmic mode at non-1x playback rates have **incorrect frequency values** stored in `lowFreq` and `highFreq` fields. The error increases as playbackRate deviates further from 1.0.

## How to Identify Affected Data

Submissions after this fix include a global flag in the JSON dump:
```javascript
jsonDump.usesCorrectedLogFormula = true
```

Submissions WITHOUT this flag that were captured:
1. In logarithmic mode
2. At playbackRate ≠ 1.0

...may have incorrect frequency values.

## Data Correction Formula

To convert OLD (incorrectly saved) frequency values to CORRECT values:

```javascript
/**
 * Correct frequency values saved with the old broken logarithmic formula
 * 
 * @param {number} freq_saved - The incorrectly saved frequency value
 * @param {number} playbackRate - The playback rate when the feature was captured
 * @param {number} maxFreq - Nyquist frequency (typically 50 Hz)
 * @returns {number} The corrected frequency value
 */
function correctLogFrequency(freq_saved, playbackRate, maxFreq = 50) {
    // Constants
    const minFreq = 0.1;
    const logMin = Math.log10(minFreq);  // -1
    const logMax = Math.log10(maxFreq);
    const logRange = logMax - logMin;
    
    // OLD (broken) stretch factor
    const stretchFactor_OLD = Math.log10(maxFreq * playbackRate) / Math.log10(maxFreq);
    
    // NEW (correct) stretch factor
    const targetMaxFreq = maxFreq / playbackRate;
    const logTargetMax = Math.log10(Math.max(targetMaxFreq, minFreq));
    const targetLogRange = logTargetMax - logMin;
    const fraction = targetLogRange / logRange;
    const stretchFactor_NEW = 1 / fraction;
    
    // Correction ratio
    const correctionRatio = stretchFactor_OLD / stretchFactor_NEW;
    
    // Apply correction in log space
    const logFreq_saved = Math.log10(Math.max(freq_saved, minFreq));
    const logFreq_corrected = logMin + (logFreq_saved - logMin) * correctionRatio;
    
    return Math.pow(10, logFreq_corrected);
}

// Example usage:
// If a feature was saved at 2x playback with lowFreq = 5.0 Hz:
// const corrected = correctLogFrequency(5.0, 2.0, 50);
// console.log(corrected);  // Will give the actual frequency that was selected
```

### Python Version:

```python
import math

def correct_log_frequency(freq_saved, playback_rate, max_freq=50):
    """
    Correct frequency values saved with the old broken logarithmic formula.
    
    Args:
        freq_saved: The incorrectly saved frequency value
        playback_rate: The playback rate when the feature was captured  
        max_freq: Nyquist frequency (typically 50 Hz)
    
    Returns:
        The corrected frequency value
    """
    min_freq = 0.1
    log_min = math.log10(min_freq)  # -1
    log_max = math.log10(max_freq)
    log_range = log_max - log_min
    
    # OLD (broken) stretch factor
    stretch_factor_old = math.log10(max_freq * playback_rate) / math.log10(max_freq)
    
    # NEW (correct) stretch factor  
    target_max_freq = max_freq / playback_rate
    log_target_max = math.log10(max(target_max_freq, min_freq))
    target_log_range = log_target_max - log_min
    fraction = target_log_range / log_range
    stretch_factor_new = 1 / fraction
    
    # Correction ratio
    correction_ratio = stretch_factor_old / stretch_factor_new
    
    # Apply correction in log space
    log_freq_saved = math.log10(max(freq_saved, min_freq))
    log_freq_corrected = log_min + (log_freq_saved - log_min) * correction_ratio
    
    return 10 ** log_freq_corrected
```

## Important Notes

1. **Linear and sqrt modes were NOT affected** - they correctly used inverse formulas
2. **playbackRate = 1.0 was NOT affected** - both formulas give identical results at 1x
3. **The correction requires knowing the playbackRate** at the time of capture (which may not be stored in older data)
4. **If playbackRate is unknown**, frequency data for log-mode features should be treated as approximate

## Files Modified

- `js/region-tracker.js` - Fixed `getFrequencyFromY()` logarithmic case
- `js/ui-controls.js` - Added `usesCorrectedLogFormula: true` global flag to JSON dump

