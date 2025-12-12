# Complete Fix: Frequency Scale Not Propagating on Zoom Out

**Date Fixed:** November 25, 2025  
**Version:** v2.70  
**Affected Scenario:** Changing frequency scale while zoomed into a region

## Problem Description

When changing the frequency scale (linear/sqrt/logarithmic) while zoomed into a region, the zoomed-in view would update correctly with a smooth fade animation. However, when zooming out to full view, the main canvas would still show the **OLD frequency scale** instead of the new one.

**Symptoms:**
- User zooms into a region
- User changes frequency scale (e.g., linear → logarithmic)
- Region view updates correctly with new scale ✅
- User zooms out to full view
- Full view still shows OLD frequency scale ❌

## Root Cause

The spectrogram system uses a cached full-view canvas called the **"elastic friend"** (`cachedFullSpectrogramCanvas`) that is created when the full spectrogram is first rendered. This cache is used during zoom transitions for smooth animations.

**The problem:** When frequency scale changed while zoomed in:
1. Only the **region spectrogram** was re-rendered (visible to user)
2. The **cached full spectrogram** (elastic friend) was **never updated**
3. When zooming out, `restoreInfiniteCanvasFromCache()` restored from the stale cache
4. Result: Full view showed the old frequency scale

## The Complete Fix

The fix uses a **proactive background rendering approach**: After the region frequency scale change completes, immediately re-render the full spectrogram in the background so the elastic friend is ready with the new scale when the user zooms out.

### Step 1: Add Tracking Variable

**File:** `js/spectrogram-complete-renderer.js`

Add a variable to track which frequency scale the elastic friend was rendered with:

```javascript
// 🏠 THE ELASTIC FRIEND - our source of truth during transitions
let cachedFullSpectrogramCanvas = null;
let cachedFullFrequencyScale = null;  // Track which scale the elastic friend was rendered with
```

### Step 2: Track Scale When Caching

**File:** `js/spectrogram-complete-renderer.js` (around line 493)

When storing the elastic friend, also store the frequency scale:

```javascript
// 🏠 STORE AS ELASTIC FRIEND (our source of truth for transitions!)
cachedFullSpectrogramCanvas = tempCanvas;
cachedFullFrequencyScale = State.frequencyScale;  // Remember which scale we rendered with
```

### Step 3: Add `forceFullView` Parameter

**File:** `js/spectrogram-complete-renderer.js` (function signature around line 254)

Modify `renderCompleteSpectrogram()` to accept a `forceFullView` parameter that bypasses the region check:

```javascript
/**
 * Render complete spectrogram (full dataset)
 * This becomes our ELASTIC FRIEND 🏠
 * @param {boolean} skipViewportUpdate - Don't update the display canvas
 * @param {boolean} forceFullView - Bypass region check (for background elastic friend update)
 */
export async function renderCompleteSpectrogram(skipViewportUpdate = false, forceFullView = false) {
    // ... existing code ...
    
    // If inside a region, render that instead (unless forceFullView is set)
    if (!forceFullView && zoomState.isInRegion()) {
        // ... render region instead ...
        return await renderCompleteSpectrogramForRegion(startSeconds, endSeconds);
    }
    
    // Skip "already rendered" check when forcing full view update
    if (!forceFullView && completeSpectrogramRendered) {
        // ... skip if already rendered ...
        return;
    }
    
    // ... rest of rendering logic ...
}
```

### Step 4: Create Background Update Function

**File:** `js/spectrogram-complete-renderer.js` (around line 760)

Add a new function that updates the elastic friend in the background:

```javascript
/**
 * 🏠 Update elastic friend in background (after frequency scale change while zoomed in)
 * Re-renders the full spectrogram so it's ready with the new scale when user zooms out
 * Does NOT touch the current display - purely background update
 */
export async function updateElasticFriendInBackground() {
    if (!isStudyMode()) {
        console.log(`🏠 Updating elastic friend in background with ${State.frequencyScale} scale...`);
    }
    const startTime = performance.now();
    
    try {
        // Use existing render function with forceFullView=true to bypass region check
        // skipViewportUpdate=true so we don't touch the display
        await renderCompleteSpectrogram(true, true);
        
        if (!isStudyMode()) {
            const elapsed = performance.now() - startTime;
            console.log(`🏠 Elastic friend updated in background (${elapsed.toFixed(0)}ms) - ready for zoom out!`);
        }
        
    } catch (error) {
        console.error('❌ Error updating elastic friend in background:', error);
    }
}
```

### Step 5: Export the Function

**File:** `js/spectrogram-complete-renderer.js` (export statement)

Make sure `updateElasticFriendInBackground` is exported:

```javascript
export { 
    // ... other exports ...
    updateElasticFriendInBackground 
};
```

### Step 6: Call After Region Scale Transition

**File:** `js/spectrogram-renderer.js` (around line 585)

After the region frequency scale fade animation completes, kick off the background update:

```javascript
// In changeFrequencyScale() function, after region fade completes:

if (progress < 1.0) {
    requestAnimationFrame(fadeStep);
} else {
    // Fade complete - lock in new spectrogram
    updateSpectrogramViewport(playbackRate);

    // Update feature box positions for new frequency scale
    updateAllFeatureBoxPositions();
    redrawAllCanvasFeatureBoxes(); // Update canvas boxes too!

    // Resume playhead
    if (playbackWasActive) {
        startPlaybackIndicator();
    }

    if (!isStudyMode()) console.log('✅ Region scale transition complete (with fade)');
    
    // 🏠 PROACTIVE FIX: Re-render full spectrogram in background
    // So elastic friend is ready with new frequency scale when user zooms out
    if (!isStudyMode()) console.log('🏠 Starting background render of full spectrogram for elastic friend...');
    updateElasticFriendInBackground();
}
```

### Step 7: Import the Function

**File:** `js/spectrogram-renderer.js` (import statement at top)

Make sure to import the function:

```javascript
import { 
    renderCompleteSpectrogram, 
    clearCompleteSpectrogram, 
    isCompleteSpectrogramRendered, 
    renderCompleteSpectrogramForRegion, 
    updateSpectrogramViewport, 
    getSpectrogramViewport, 
    resetSpectrogramState, 
    getInfiniteCanvasStatus, 
    updateElasticFriendInBackground  // ← Add this import
} from './spectrogram-complete-renderer.js';
```

## Flow After Fix

```
User changes frequency scale (while zoomed in)
    ↓
Region re-renders with new scale
    ↓
Fade animation plays (old → new)
    ↓
Fade completes → updateElasticFriendInBackground() called
    ↓
Background: Full spectrogram re-renders (invisible to user)
    ↓
Elastic friend updated with new scale ✅
    ↓
User zooms out → elastic friend has correct scale! 🎯
```

## Files Modified

1. **`js/spectrogram-complete-renderer.js`**
   - Added `cachedFullFrequencyScale` tracking variable (line ~43)
   - Track scale when caching elastic friend (line ~493)
   - Added `forceFullView` parameter to `renderCompleteSpectrogram()` (line ~254)
   - Created `updateElasticFriendInBackground()` function (line ~760)
   - Export `updateElasticFriendInBackground`

2. **`js/spectrogram-renderer.js`**
   - Import `updateElasticFriendInBackground` (top of file)
   - Call `updateElasticFriendInBackground()` after region scale fade completes (line ~585)

## Key Design Decisions

1. **Background rendering**: The full spectrogram re-renders in the background (non-blocking) so it doesn't affect the user's current view
2. **Proactive approach**: Update the cache immediately after scale change, not lazily when zooming out
3. **Non-intrusive**: Uses `skipViewportUpdate=true` so the background render doesn't touch the display
4. **Bypass checks**: Uses `forceFullView=true` to bypass region check and "already rendered" check

## Testing

Test the fix by:

1. **Load a file** and wait for full spectrogram to render
2. **Zoom into a region**
3. **Change frequency scale** (e.g., linear → logarithmic)
4. **Verify region view updates** with smooth fade ✅
5. **Zoom out to full view**
6. **Verify full view shows NEW frequency scale** ✅

### Test Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Change scale while zoomed in → zoom out | Full view shows new scale ✅ |
| Change scale while zoomed in → change scale again → zoom out | Full view shows latest scale ✅ |
| Change scale at full view | Full view updates immediately ✅ |
| Change scale while zoomed in → zoom in deeper → zoom out | Full view shows new scale ✅ |

## Performance Considerations

- Background rendering happens **asynchronously** and doesn't block the UI
- Rendering time varies by dataset size (typically 100-500ms)
- The user can continue working while the background render completes
- If user zooms out before background render completes, they'll see the old scale briefly, then it updates when render finishes

## Related Concepts

- **Elastic Friend**: The cached full-view spectrogram canvas used for smooth zoom transitions
- **Region Rendering**: High-quality render of just the zoomed-in region
- **Force Full View**: Parameter that bypasses region checks to render full view even when zoomed in

## References

- **Captain's log entry**: `docs/captains_logs/captains_log_2025-11-25.md` (lines 117-154)
- **Version**: v2.70
- **Related fix**: See `docs/SPECTROGRAM_BOX_JUMP_FIX_COMPLETE.md` for the logarithmic frequency conversion bug fix



