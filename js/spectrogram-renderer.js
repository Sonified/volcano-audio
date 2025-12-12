/**
 * spectrogram-renderer.js
 * Spectrogram visualization
 */

import * as State from './audio-state.js';
import { PlaybackState } from './audio-state.js';
import { drawFrequencyAxis, positionAxisCanvas, resizeAxisCanvas, initializeAxisPlaybackRate, getYPositionForFrequencyScaled, getScaleTransitionState } from './spectrogram-axis-renderer.js';
import { handleSpectrogramSelection, isInFrequencySelectionMode, getCurrentRegions, startFrequencySelection } from './region-tracker.js';
import { renderCompleteSpectrogram, clearCompleteSpectrogram, isCompleteSpectrogramRendered, renderCompleteSpectrogramForRegion, updateSpectrogramViewport, getSpectrogramViewport, resetSpectrogramState, getInfiniteCanvasStatus, updateElasticFriendInBackground } from './spectrogram-complete-renderer.js';
import { zoomState } from './zoom-state.js';
import { isStudyMode } from './master-modes.js';
import { getInterpolatedTimeRange } from './waveform-x-axis-renderer.js';
import { updateAllFeatureBoxPositions } from './spectrogram-feature-boxes.js';
import { animateScaleTransition } from './spectrogram-axis-renderer.js';
import { startPlaybackIndicator } from './waveform-renderer.js';

// Spectrogram selection state (pure canvas - separate overlay layer!)
let spectrogramSelectionActive = false;
let spectrogramStartX = null;
let spectrogramStartY = null;
let spectrogramCurrentX = null;  // Current drag position (for canvas rendering)
let spectrogramCurrentY = null;  // Current drag position (for canvas rendering)
export let spectrogramSelectionBox = null;  // DEPRECATED - kept for compatibility during transition

// Overlay canvas for selection box (separate layer - no conflicts!)
let spectrogramOverlayCanvas = null;
let spectrogramOverlayCtx = null;

// Store completed boxes to redraw them all (replaces orange DOM boxes!)
// NOTE: We rebuild this from actual feature data, so it stays in sync!
let completedSelectionBoxes = [];

/**
 * Add a feature box to the canvas overlay
 * NOTE: Actually rebuilds from source - ensures sync with feature array!
 */
export function addCanvasFeatureBox(regionIndex, featureIndex, featureData) {
    // Rebuild from source to ensure sync (handles renumbering automatically!)
    rebuildCanvasBoxesFromFeatures();
}

/**
 * Remove a feature box from the canvas overlay
 * NOTE: Actually rebuilds from source - ensures sync with feature array!
 */
export function removeCanvasFeatureBox(regionIndex, featureIndex) {
    // Rebuild from source to ensure sync (handles renumbering automatically!)
    rebuildCanvasBoxesFromFeatures();
}

/**
 * Clear all feature boxes from the canvas overlay
 */
export function clearAllCanvasFeatureBoxes() {
    completedSelectionBoxes = [];
    
    if (spectrogramOverlayCtx && spectrogramOverlayCanvas) {
        spectrogramOverlayCtx.clearRect(0, 0, spectrogramOverlayCanvas.width, spectrogramOverlayCanvas.height);
    }
    
    console.log('🧹 Cleared all canvas feature boxes');
}

/**
 * Show safeguard message when stuck state is detected
 */
function showStuckStateMessage() {
    const statusEl = document.getElementById('status');
    if (statusEl) {
        statusEl.textContent = 'Difficulty Creating Regions? Please refresh your page to continue. Thanks!';
        statusEl.style.color = '#ffa500'; // Orange color for warning (less alarming than red)
        statusEl.style.fontWeight = '600';
        console.warn('⚠️ [SAFEGUARD] Stuck state detected - showing safeguard message');
    }
}

/**
 * Hide safeguard message when state is restored
 */
function hideStuckStateMessage() {
    const statusEl = document.getElementById('status');
    if (statusEl) {
        // Only clear if it's our safeguard message (don't clear other status messages)
        if (statusEl.textContent.includes('Difficulty Creating Regions')) {
            statusEl.textContent = '';
            statusEl.style.color = ''; // Reset to default
            statusEl.style.fontWeight = '';
            console.log('✅ [SAFEGUARD] Stuck state resolved - hiding safeguard message');
        }
    }
}

/**
 * Check if a click point is within any canvas feature box
 * Returns {regionIndex, featureIndex} if clicked, null otherwise
 */
function getClickedBox(x, y) {
    if (!State.dataStartTime || !State.dataEndTime || !zoomState.isInitialized()) {
        return null;
    }
    
    const canvas = document.getElementById('spectrogram');
    if (!canvas) return null;
    
    // Convert click coordinates to device pixels
    const scaleX = canvas.width / canvas.offsetWidth;
    const scaleY = canvas.height / canvas.offsetHeight;
    const x_device = x * scaleX;
    const y_device = y * scaleY;
    
    // Check each box
    for (const box of completedSelectionBoxes) {
        // Convert box coordinates to device pixels (same logic as drawSavedBox)
        const originalSampleRate = State.currentMetadata?.original_sample_rate || 100;
        const originalNyquist = originalSampleRate / 2;
        const playbackRate = State.currentPlaybackRate || 1.0;
        
        // Get Y positions
        const scaleTransition = getScaleTransitionState();
        let lowFreqY_device, highFreqY_device;
        
        if (scaleTransition.inProgress && scaleTransition.oldScaleType) {
            const oldLowY = getYPositionForFrequencyScaled(box.lowFreq, originalNyquist, canvas.height, scaleTransition.oldScaleType, playbackRate);
            const newLowY = getYPositionForFrequencyScaled(box.lowFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
            const oldHighY = getYPositionForFrequencyScaled(box.highFreq, originalNyquist, canvas.height, scaleTransition.oldScaleType, playbackRate);
            const newHighY = getYPositionForFrequencyScaled(box.highFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
            
            lowFreqY_device = oldLowY + (newLowY - oldLowY) * scaleTransition.interpolationFactor;
            highFreqY_device = oldHighY + (newHighY - oldHighY) * scaleTransition.interpolationFactor;
        } else {
            lowFreqY_device = getYPositionForFrequencyScaled(box.lowFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
            highFreqY_device = getYPositionForFrequencyScaled(box.highFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
        }
        
        // Get X positions
        const interpolatedRange = getInterpolatedTimeRange();
        const displayStartMs = interpolatedRange.startTime.getTime();
        const displayEndMs = interpolatedRange.endTime.getTime();
        const displaySpanMs = displayEndMs - displayStartMs;
        
        const startTimestamp = new Date(box.startTime);
        const endTimestamp = new Date(box.endTime);
        const startMs = startTimestamp.getTime();
        const endMs = endTimestamp.getTime();
        
        const startProgress = (startMs - displayStartMs) / displaySpanMs;
        const endProgress = (endMs - displayStartMs) / displaySpanMs;
        
        const startX_device = startProgress * canvas.width;
        const endX_device = endProgress * canvas.width;
        
        // Check if click is within box bounds
        const boxX = Math.min(startX_device, endX_device);
        const boxY = Math.min(highFreqY_device, lowFreqY_device);
        const boxWidth = Math.abs(endX_device - startX_device);
        const boxHeight = Math.abs(lowFreqY_device - highFreqY_device);
        
        if (x_device >= boxX && x_device <= boxX + boxWidth &&
            y_device >= boxY && y_device <= boxY + boxHeight) {
            return { regionIndex: box.regionIndex, featureIndex: box.featureIndex };
        }
    }
    
    return null;
}

/**
 * Rebuild canvas boxes from actual feature data (keeps them in sync!)
 * Uses same logic as orange boxes - rebuilds from source of truth
 * This ensures boxes match the actual feature array (no orphans, numbers shift correctly)
 */
function rebuildCanvasBoxesFromFeatures() {
    const regions = getCurrentRegions();
    if (!regions) return;
    
    completedSelectionBoxes = [];
    
    // Rebuild boxes from actual feature data (always in sync!)
    regions.forEach((region, regionIndex) => {
        if (!region.features) return;
        
        region.features.forEach((feature, featureIndex) => {
            // Only add boxes for complete features
            if (feature.lowFreq && feature.highFreq && feature.startTime && feature.endTime) {
                completedSelectionBoxes.push({
                    regionIndex,
                    featureIndex,
                    startTime: feature.startTime,
                    endTime: feature.endTime,
                    lowFreq: parseFloat(feature.lowFreq),
                    highFreq: parseFloat(feature.highFreq),
                    notes: feature.notes || '' // Add notes for annotations
                });
            }
        });
    });
    
    // Redraw with rebuilt boxes
    redrawCanvasBoxes();
}

/**
 * Check if we're in results2025 mode (annotations should be shown)
 */
function isResults2025Mode() {
    const participantId = localStorage.getItem('participantId');
    return participantId && participantId.toLowerCase() === 'results2025';
}

/**
 * Redraw canvas boxes (internal - clears and draws all boxes)
 * Uses two-pass rendering: boxes first, then annotations on top
 */
function redrawCanvasBoxes() {
    if (spectrogramOverlayCtx && spectrogramOverlayCanvas) {
        const canvas = document.getElementById('spectrogram');
        if (!canvas) return;

        spectrogramOverlayCtx.clearRect(0, 0, spectrogramOverlayCanvas.width, spectrogramOverlayCanvas.height);

        // PASS 1: Draw all feature boxes (no annotations yet)
        for (const savedBox of completedSelectionBoxes) {
            drawSavedBox(spectrogramOverlayCtx, savedBox);
        }

        // PASS 2: Draw annotations on top (only in results2025 mode)
        if (isResults2025Mode()) {
            const placedAnnotations = []; // Track placed annotations for collision detection
            for (const savedBox of completedSelectionBoxes) {
                if (savedBox.notes) {
                    drawAnnotation(spectrogramOverlayCtx, canvas, savedBox, placedAnnotations, completedSelectionBoxes);
                }
            }
        }
    }
}

/**
 * Redraw all canvas feature boxes (called after zoom, speed change, deletion, etc.)
 * Rebuilds from source of truth to stay in sync!
 */
export function redrawAllCanvasFeatureBoxes() {
    rebuildCanvasBoxesFromFeatures();
}

// 🔥 FIX: Track event listeners for cleanup to prevent memory leaks
let spectrogramMouseUpHandler = null;
let spectrogramKeyDownHandler = null;
let spectrogramSelectionSetup = false;
let spectrogramFocusBlurHandler = null;
let spectrogramVisibilityHandler = null;
let spectrogramFocusHandler = null;
let spectrogramBlurHandler = null;
let spectrogramResizeObserver = null;
let spectrogramRepositionOnVisibility = null;

// 🔥 FIX: Safety timeout to auto-cancel if mouseup never fires
let spectrogramSelectionTimeout = null;

export function drawSpectrogram() {
    console.log(`📺 [spectrogram-renderer.js] drawSpectrogram CALLED`);
    console.trace('📍 Call stack:');
    
    // 🔥 FIX: Copy State values to local variables IMMEDIATELY to break closure chain
    // This prevents RAF callbacks from capturing the entire State module
    // Access State only once at the start, then use local variables throughout
    const currentRAF = State.spectrogramRAF;
    const analyserNode = State.analyserNode;
    const playbackState = State.playbackState;
    const frequencyScale = State.frequencyScale;
    const spectrogramInitialized = State.spectrogramInitialized;
    
    // Clear RAF ID immediately to prevent duplicate scheduling
    // This must happen FIRST before any early returns to prevent accumulation
    State.setSpectrogramRAF(null);
    if (currentRAF !== null) {
        cancelAnimationFrame(currentRAF);
    }
    
    // 🔥 FIX: Check if document is still connected (not detached) before proceeding
    // This prevents RAF callbacks from retaining references to detached documents
    if (!document.body || !document.body.isConnected) {
        return; // Document is detached, stop the loop
    }
    
    // Early exit: no analyser - stop the loop completely
    if (!analyserNode) return;
    
    // Early exit: not playing - schedule next frame to keep checking
    if (playbackState !== PlaybackState.PLAYING) {
        // 🔥 FIX: Only schedule RAF if document is still connected and not already scheduled
        if (document.body && document.body.isConnected && State.spectrogramRAF === null) {
        State.setSpectrogramRAF(requestAnimationFrame(drawSpectrogram));
        }
        return;
    }
    
    const canvas = document.getElementById('spectrogram');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Clear entire canvas only on first initialization
    if (!spectrogramInitialized) {
        ctx.clearRect(0, 0, width, height);
        State.setSpectrogramInitialized(true);
    }
    
    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyserNode.getByteFrequencyData(dataArray);
    
    // Helper function to calculate y position based on frequency scale
    const getYPosition = (binIndex, totalBins, canvasHeight) => {
        if (frequencyScale === 'logarithmic') {
            // Logarithmic scale: strong emphasis on lower frequencies
            // Map bin index to log scale (avoiding log(0))
            const minFreq = 1; // Minimum frequency bin (avoid log(0))
            const maxFreq = totalBins;
            const logMin = Math.log10(minFreq);
            const logMax = Math.log10(maxFreq);
            const logFreq = Math.log10(Math.max(binIndex + 1, minFreq));
            const normalizedLog = (logFreq - logMin) / (logMax - logMin);
            return canvasHeight - (normalizedLog * canvasHeight);
        } else if (frequencyScale === 'sqrt') {
            // Square root scale: gentle emphasis on lower frequencies (good middle ground)
            const normalized = binIndex / totalBins;
            const sqrtNormalized = Math.sqrt(normalized);
            return canvasHeight - (sqrtNormalized * canvasHeight);
        } else {
            // Linear scale (default) - even spacing
            return canvasHeight - (binIndex / totalBins) * canvasHeight;
        }
    };
    
    // Scroll 1 pixel per frame (standard scrolling behavior)
            ctx.drawImage(canvas, -1, 0);
            ctx.clearRect(width - 1, 0, 1, height);
            
            // Draw new column
            for (let i = 0; i < bufferLength; i++) {
                const value = dataArray[i];
                const percent = value / 255;
                const hue = percent * 60;
                const saturation = 100;
                const lightness = 10 + (percent * 60);
                const y = getYPosition(i, bufferLength, height);
                const nextY = getYPosition(i + 1, bufferLength, height);
                const barHeight = Math.max(1, Math.abs(y - nextY));
                ctx.fillStyle = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
                ctx.fillRect(width - 1, nextY, 1, barHeight);
    }
    
    // 🔥 FIX: Store RAF ID for proper cleanup
    // Only schedule if document is still connected and not already scheduled
    // This prevents creating multiple RAF callbacks that accumulate
    if (document.body && document.body.isConnected && State.spectrogramRAF === null) {
    State.setSpectrogramRAF(requestAnimationFrame(drawSpectrogram));
    } else {
        // Document is detached or already scheduled - stop the loop
        State.setSpectrogramRAF(null);
            }
}


/**
 * Load frequency scale from localStorage and apply it
 * Called on page load to restore user's preferred frequency scale
 */
export function loadFrequencyScale() {
    const select = document.getElementById('frequencyScale');
    if (!select) return;
    
    // Load saved value from localStorage (default: 'sqrt')
    const savedValue = localStorage.getItem('frequencyScale');
    if (savedValue !== null) {
        // Validate value is one of the allowed options
        const validValues = ['linear', 'sqrt', 'logarithmic'];
        if (validValues.includes(savedValue)) {
            select.value = savedValue;
            State.setFrequencyScale(savedValue);
            console.log(`📊 Loaded saved frequency scale: ${savedValue}`);
        }
    } else {
        // No saved value, use default and save it
        const defaultValue = 'sqrt';
        select.value = defaultValue;
        State.setFrequencyScale(defaultValue);
        localStorage.setItem('frequencyScale', defaultValue);
    }
}

export async function changeFrequencyScale() {
    const select = document.getElementById('frequencyScale');
    const value = select.value; // 'linear', 'sqrt', or 'logarithmic'

    // If already on this scale, don't process again
    if (State.frequencyScale === value) {
        console.log(`📊 Already on ${value} scale - skipping change`);
        return;
    }

    // Save to localStorage for persistence
    localStorage.setItem('frequencyScale', value);

    // Store old scale for animation
    const oldScale = State.frequencyScale;

    State.setFrequencyScale(value);

    // Use statically imported function (no dynamic import needed)
    
    // 🎓 Tutorial: Resolve promise if waiting for frequency scale change
    if (State.waitingForFrequencyScaleChange && State._frequencyScaleChangeResolve) {
        State.setWaitingForFrequencyScaleChange(false);
        const resolve = State._frequencyScaleChangeResolve;
        State.setFrequencyScaleChangeResolve(null);
        resolve();
    }
    
    // Blur dropdown so spacebar can toggle play/pause
    select.blur();
    
    if (!isStudyMode()) {
        console.log(`📊 Frequency scale changed to: ${value}`);
    }
    
    // 🔍 Diagnostic: Check state before animation decision
    if (!isStudyMode()) {
        console.log(`🎨 [changeFrequencyScale] Checking if we should animate:`, {
            hasComplete: isCompleteSpectrogramRendered(),
            oldScale: oldScale,
            newScale: value,
            inRegion: zoomState.isInRegion()
        });
    }
    
    // If complete spectrogram is rendered, animate transition
    if (isCompleteSpectrogramRendered()) {
        // console.log('✅ Animation path - have rendered spectrogram');
        if (!isStudyMode()) {
            console.log('🎨 Starting scale transition (axis + spectrogram in parallel)...');
        }
        
        // Start axis animation immediately (don't wait for it)
        // Use statically imported function
        const axisAnimationPromise = animateScaleTransition(oldScale);
        
        // Start spectrogram rendering immediately (in parallel with axis animation)
        if (!isStudyMode()) {
            console.log('🎨 Starting spectrogram re-render...');
        }
        
        // 🔥 PAUSE playhead updates during fade!
        const playbackWasActive = State.playbackState === State.PlaybackState.PLAYING;
        const originalRAF = State.playbackIndicatorRAF;
        if (originalRAF !== null) {
            cancelAnimationFrame(originalRAF);
            State.setPlaybackIndicatorRAF(null);
        }
        
        const canvas = document.getElementById('spectrogram');
        if (canvas) {
            if (!isStudyMode()) {
                console.log(`🎨 [spectrogram-renderer.js] changeFrequencyScale: Starting fade animation`);
            }
            console.trace('📍 Call stack:');
            
            const ctx = canvas.getContext('2d');
            const width = canvas.width;
            const height = canvas.height;
            
            // 🔧 FIX: Check if we're zoomed into a region - handle with fade animation!
            if (zoomState.isInitialized() && zoomState.isInRegion()) {
                const regionRange = zoomState.getRegionRange();
                console.log(`🔍 Inside region - animating scale transition`);
                
                // 🔥 FIX: Convert Date objects to seconds (renderCompleteSpectrogramForRegion expects seconds!)
                const dataStartMs = State.dataStartTime ? State.dataStartTime.getTime() : 0;
                const startSeconds = (regionRange.startTime.getTime() - dataStartMs) / 1000;
                const endSeconds = (regionRange.endTime.getTime() - dataStartMs) / 1000;
                
                // 🔥 Capture old spectrogram BEFORE re-rendering
                const oldSpectrogram = document.createElement('canvas');
                oldSpectrogram.width = width;
                oldSpectrogram.height = height;
                oldSpectrogram.getContext('2d').drawImage(canvas, 0, 0);
                
                // Re-render region with new frequency scale (in "background") - start immediately!
                resetSpectrogramState(); // Clear state so it will re-render
                
                // Start rendering immediately (don't await - let it run in parallel with axis animation)
                const spectrogramRenderPromise = renderCompleteSpectrogramForRegion(
                    startSeconds, 
                    endSeconds, 
                    true  // Skip viewport update - we'll fade manually
                );
                
                // Wait for spectrogram to finish rendering (may complete before or after axis animation)
                await spectrogramRenderPromise;

                console.log('🎨 Spectrogram render complete - getting viewport for crossfade');

                // Get the new spectrogram (without displaying it yet)
                const playbackRate = State.currentPlaybackRate || 1.0;
                
                // 🔥 DIAGNOSTIC: Check infinite canvas status before getting viewport
                const infiniteCanvasStatus = getInfiniteCanvasStatus();
                if (!isStudyMode()) {
                    console.log(`🔍 Infinite canvas status: ${infiniteCanvasStatus}`);
                }
                
                const newSpectrogram = getSpectrogramViewport(playbackRate);

                if (!newSpectrogram) {
                    console.warn('⚠️ getSpectrogramViewport returned null - falling back to direct viewport update');
                    // Fallback: just update normally
                    updateSpectrogramViewport(playbackRate);
                    if (playbackWasActive) {
                        startPlaybackIndicator();
                    }
                    if (!isStudyMode()) console.log('✅ Region scale transition complete (no fade)');
                    return;
                }

                // 🔥 DIAGNOSTIC: Verify the viewport canvas has content (not all black)
                const testCtx = newSpectrogram.getContext('2d');
                const imageData = testCtx.getImageData(0, 0, Math.min(100, newSpectrogram.width), Math.min(100, newSpectrogram.height));
                let hasContent = false;
                for (let i = 0; i < imageData.data.length; i += 4) {
                    // Check if pixel is not pure black (allow some tolerance)
                    if (imageData.data[i] > 5 || imageData.data[i + 1] > 5 || imageData.data[i + 2] > 5) {
                        hasContent = true;
                        break;
                    }
                }
                
                if (!hasContent && !isStudyMode()) {
                    console.warn('⚠️ getSpectrogramViewport returned canvas with no visible content (all black)');
                }

                if (!isStudyMode()) console.log('✅ Got new spectrogram viewport - starting crossfade');
                
                // 🎨 Crossfade old → new (300ms)
                const fadeDuration = 300;
                const fadeStart = performance.now();
                
                const fadeStep = () => {
                    if (!document.body || !document.body.isConnected) {
                        return;
                    }
                    
                    const elapsed = performance.now() - fadeStart;
                    const progress = Math.min(elapsed / fadeDuration, 1.0);
                    const alpha = 1 - Math.pow(1 - progress, 2); // Ease-out
                    
                    // Clear and draw blend
                    ctx.clearRect(0, 0, width, height);
                    
                    // Old fading OUT
                    ctx.globalAlpha = 1.0 - alpha;
                    ctx.drawImage(oldSpectrogram, 0, 0);
                    
                    // New fading IN
                    ctx.globalAlpha = alpha;
                    ctx.drawImage(newSpectrogram, 0, 0);
                    
                    // Playhead on top
                    ctx.globalAlpha = 1.0;
                    if (State.currentAudioPosition !== null && State.totalAudioDuration > 0) {
                        // Calculate playhead position relative to region
                        const regionDuration = endSeconds - startSeconds;
                        const positionInRegion = State.currentAudioPosition - startSeconds;
                        const playheadX = (positionInRegion / regionDuration) * width;
                        
                        ctx.strokeStyle = '#616161';
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.moveTo(playheadX, 0);
                        ctx.lineTo(playheadX, height);
                        ctx.stroke();
                    }
                    
                    ctx.globalAlpha = 1.0;
                    
                    // Redraw canvas feature boxes during transition (smooth interpolation!)
                    redrawAllCanvasFeatureBoxes();
                    
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
                        console.log('🏠 Starting background render of full spectrogram for elastic friend...');
                        updateElasticFriendInBackground();
                    }
                };
                
                fadeStep();
                return;
            }
            
            // OLD SPECTROGRAM IS ALREADY ON SCREEN - DON'T TOUCH IT!
            // Reset state flag so we can re-render (but don't clear the canvas!)
            resetSpectrogramState();
            
            // Just render new spectrogram in background (skip viewport update) - start immediately!
            // This runs in parallel with the axis animation
            const spectrogramRenderPromise = renderCompleteSpectrogram(true); // Skip viewport update - old stays visible!
            
            // Wait for spectrogram to finish rendering (may complete before or after axis animation)
            await spectrogramRenderPromise;
            
            // Get the new spectrogram viewport without updating display canvas
            // Use statically imported function
            const playbackRate = State.currentPlaybackRate || 1.0;
            const newSpectrogram = getSpectrogramViewport(playbackRate);
            
            if (!newSpectrogram) {
                // Fallback: just update normally
                updateSpectrogramViewport(playbackRate);
                // Resume playhead if it was active
                if (playbackWasActive) {
                    startPlaybackIndicator();
                }
                return;
            }
            
            // 🔥 Capture old spectrogram for crossfade (BEFORE we start fading)
            const oldSpectrogram = document.createElement('canvas');
            oldSpectrogram.width = width;
            oldSpectrogram.height = height;
            oldSpectrogram.getContext('2d').drawImage(canvas, 0, 0);
            
            // Old spectrogram is STILL visible on display canvas
            // Now fade in the new one on top (300ms)
            const fadeDuration = 300;
            const fadeStart = performance.now();
            
            const fadeStep = () => {
                // console.log(`🎬 [spectrogram-renderer.js] changeFrequencyScale fadeStep: Drawing frame`);
                // 🔥 FIX: Check document connection before executing RAF callback
                // This prevents RAF callbacks from retaining references to detached documents
                if (!document.body || !document.body.isConnected) {
                    return; // Document is detached, stop the fade animation
                }
                
                const elapsed = performance.now() - fadeStart;
                const progress = Math.min(elapsed / fadeDuration, 1.0);
                
                // Ease-out for smooth fade
                const alpha = 1 - Math.pow(1 - progress, 2);
                
                // 🔥 CLEAR CANVAS - start fresh each frame!
                ctx.clearRect(0, 0, width, height);
                
                // Draw old spectrogram fading OUT
                ctx.globalAlpha = 1.0 - alpha;
                ctx.drawImage(oldSpectrogram, 0, 0);
                
                // Draw new spectrogram fading IN
                ctx.globalAlpha = alpha;
                ctx.drawImage(newSpectrogram, 0, 0);
                
                // Draw playhead on top with full opacity
                ctx.globalAlpha = 1.0;
                
                // 🔥 Draw playhead as medium grey during transition (WE control it during fade)
                if (State.currentAudioPosition !== null && State.totalAudioDuration > 0) {
                    const playheadX = (State.currentAudioPosition / State.totalAudioDuration) * width;
                    
                    ctx.strokeStyle = '#616161'; // A little darker grey
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(playheadX, 0);
                    ctx.lineTo(playheadX, height);
                    ctx.stroke();
                }
                
                // Reset alpha after drawing playhead
                ctx.globalAlpha = 1.0;
                
                // Redraw canvas feature boxes during transition (smooth interpolation!)
                redrawAllCanvasFeatureBoxes();
                
                if (progress < 1.0) {
                    requestAnimationFrame(fadeStep);
                } else {
                    // 🔥 FADE COMPLETE - LOCK IN THE NEW SPECTROGRAM!
                    // This updates cachedSpectrogramCanvas with the new frequency scale
                    updateSpectrogramViewport(playbackRate);

                    // Update feature box positions for new frequency scale
                    updateAllFeatureBoxPositions();
                        redrawAllCanvasFeatureBoxes(); // Update canvas boxes too!

                    // 🔥 RESUME playhead updates!
                    if (playbackWasActive) {
                        startPlaybackIndicator();
                    }

                    console.log('✅ Scale transition complete, cache updated, playhead resumed');
                }
            };
            
            fadeStep();
        } else {
            // Fallback: just re-render without fade
            clearCompleteSpectrogram();
            await renderCompleteSpectrogram();

            // Update feature box positions for new frequency scale
            updateAllFeatureBoxPositions();
            redrawAllCanvasFeatureBoxes(); // Update canvas boxes too!
        }
    } else {
        console.log('⚠️ No animation - no rendered spectrogram');
        // No spectrogram yet, just update axis
        positionAxisCanvas();
        initializeAxisPlaybackRate();
        drawFrequencyAxis();

        // Update feature box positions for new frequency scale (even if no spectrogram yet)
        updateAllFeatureBoxPositions();
        redrawAllCanvasFeatureBoxes(); // Update canvas boxes too!
    }
}

export function startVisualization() {
    // Only start visualization once to prevent multiple animation loops
    if (State.visualizationStarted) {
        return;
    }
    State.setVisualizationStarted(true);
    
    // Initialize axis positioning and drawing
    positionAxisCanvas();
    // Draw initial axis (will use current playback rate)
    drawFrequencyAxis();
    
    drawSpectrogram();
}

/**
 * Setup spectrogram frequency selection
 * Called from main.js after DOM is ready
 */
export function setupSpectrogramSelection() {
    // 🔥 FIX: Only setup once to prevent duplicate event listeners
    if (spectrogramSelectionSetup) {
        console.warn('⚠️ [SETUP] setupSpectrogramSelection() called again but already setup - ignoring');
        return;
    }

    console.log('✅ [SETUP] Setting up spectrogram selection (first time)');

    const canvas = document.getElementById('spectrogram');
    if (!canvas) {
        console.warn('⚠️ [SETUP] Canvas not found - cannot setup selection');
        return;
    }

    // Use the panel as container (same as waveform selection)
    const container = canvas.closest('.panel');
    if (!container) return;
    
    // ✅ Create overlay canvas for selection box (separate layer - no conflicts!)
    spectrogramOverlayCanvas = document.createElement('canvas');
    spectrogramOverlayCanvas.id = 'spectrogram-selection-overlay';
    spectrogramOverlayCanvas.style.position = 'absolute';
    spectrogramOverlayCanvas.style.pointerEvents = 'none';  // Pass events through to main canvas
    spectrogramOverlayCanvas.style.zIndex = '20';  // Above spectrogram glow and other panels
    spectrogramOverlayCanvas.style.background = 'transparent';  // See through to spectrogram
    
    // Match main canvas size and position EXACTLY
    const canvasRect = canvas.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    spectrogramOverlayCanvas.style.left = (canvasRect.left - containerRect.left) + 'px';
    spectrogramOverlayCanvas.style.top = (canvasRect.top - containerRect.top) + 'px';
    
    // Use SAME dimensions as main canvas
    spectrogramOverlayCanvas.width = canvas.width;
    spectrogramOverlayCanvas.height = canvas.height;
    spectrogramOverlayCanvas.style.width = canvas.offsetWidth + 'px';
    spectrogramOverlayCanvas.style.height = canvas.offsetHeight + 'px';
    
    spectrogramOverlayCtx = spectrogramOverlayCanvas.getContext('2d');
    container.appendChild(spectrogramOverlayCanvas);
    
    // 🔥 SLEEP FIX: Update overlay position when canvas resizes or layout changes
    // After sleep, browser may recalculate layout causing misalignment
    // This ResizeObserver keeps overlay aligned with main canvas (like playhead overlay does)
    spectrogramResizeObserver = new ResizeObserver(() => {
        if (spectrogramOverlayCanvas && canvas) {
            const canvasRect = canvas.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            spectrogramOverlayCanvas.style.left = (canvasRect.left - containerRect.left) + 'px';
            spectrogramOverlayCanvas.style.top = (canvasRect.top - containerRect.top) + 'px';
            spectrogramOverlayCanvas.width = canvas.width;
            spectrogramOverlayCanvas.height = canvas.height;
            spectrogramOverlayCanvas.style.width = canvas.offsetWidth + 'px';
            spectrogramOverlayCanvas.style.height = canvas.offsetHeight + 'px';
            
            // Redraw boxes after repositioning to ensure they're still visible
            if (spectrogramOverlayCtx) {
                redrawCanvasBoxes();
            }
        }
    });
    spectrogramResizeObserver.observe(canvas);
    
    // Also reposition on visibility change (catches sleep/wake)
    spectrogramRepositionOnVisibility = () => {
        if (document.visibilityState === 'visible' && spectrogramOverlayCanvas && canvas) {
            const canvasRect = canvas.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            spectrogramOverlayCanvas.style.left = (canvasRect.left - containerRect.left) + 'px';
            spectrogramOverlayCanvas.style.top = (canvasRect.top - containerRect.top) + 'px';
            spectrogramOverlayCanvas.width = canvas.width;
            spectrogramOverlayCanvas.height = canvas.height;
            spectrogramOverlayCanvas.style.width = canvas.offsetWidth + 'px';
            spectrogramOverlayCanvas.style.height = canvas.offsetHeight + 'px';
            
            // Redraw boxes after repositioning
            if (spectrogramOverlayCtx) {
                redrawCanvasBoxes();
            }
        }
    };
    document.addEventListener('visibilitychange', spectrogramRepositionOnVisibility);
    
    console.log('✅ Created spectrogram selection overlay canvas:', {
        left: spectrogramOverlayCanvas.style.left,
        top: spectrogramOverlayCanvas.style.top,
        width: spectrogramOverlayCanvas.width,
        height: spectrogramOverlayCanvas.height,
        styleWidth: spectrogramOverlayCanvas.style.width,
        styleHeight: spectrogramOverlayCanvas.style.height,
        canvasWidth: canvas.width,
        canvasOffsetWidth: canvas.offsetWidth
    });

    // 🔥 SLEEP FIX: Clean up on visibility change (computer wake from sleep!)
    // This immediately cancels any stuck selection when page becomes visible again
    spectrogramVisibilityHandler = () => {
        if (document.visibilityState === 'visible') {
            // 🔍 DEBUG: Log zoom state after sleep/wake
            console.log('👁️ [SLEEP WAKE] Page visible again - checking zoom state:', {
                zoomStateInitialized: zoomState.isInitialized(),
                isInRegion: zoomState.isInitialized() ? zoomState.isInRegion() : 'N/A (not initialized)',
                zoomMode: zoomState.isInitialized() ? zoomState.mode : 'N/A',
                activeRegionId: zoomState.isInitialized() ? zoomState.activeRegionId : 'N/A',
                currentViewStartSample: zoomState.isInitialized() ? zoomState.currentViewStartSample : 'N/A'
            });
            
            // Just became visible (e.g., woke from sleep) - clean up immediately!
            if (spectrogramSelectionActive || spectrogramSelectionBox) {
                console.log('👁️ Page visible again - cleaning up any stuck selection state');
                cancelSpectrogramSelection();
            }
            // 🔥 SLEEP FIX: Also reset any stale mouse coordinates that might break tracking
            // After sleep, browser mouse events can be in a weird state
            if (!spectrogramSelectionActive && (spectrogramStartX !== null || spectrogramCurrentX !== null)) {
                console.log('👁️ Page visible again - resetting stale mouse coordinates after sleep');
                spectrogramStartX = null;
                spectrogramStartY = null;
                spectrogramCurrentX = null;
                spectrogramCurrentY = null;
            }
            // 🔥 FIX: Verify overlay context is ready after sleep - if not, show safeguard message
            if (!spectrogramOverlayCtx || !spectrogramOverlayCanvas) {
                console.warn('⚠️ [SLEEP WAKE] Overlay context missing after sleep - may need refresh');
                // Don't show message immediately - wait for user to try clicking first
                // The mousedown handler will detect and show the message if needed
            } else {
                // Overlay context is good - hide any existing safeguard message
                hideStuckStateMessage();
            }
        }
    };
    document.addEventListener('visibilitychange', spectrogramVisibilityHandler);

    // 🔥 SLEEP FIX: Also clean up on window focus (additional safety)
    spectrogramFocusHandler = () => {
        if (spectrogramSelectionActive || spectrogramSelectionBox) {
            console.log('🎯 Window focused - cleaning up any stuck selection state');
            cancelSpectrogramSelection();
        }
    };
    window.addEventListener('focus', spectrogramFocusHandler);

    // 🔥 BLUR FIX: Cancel active selections when window loses focus
    // This prevents stuck state when browser loses focus mid-drag (e.g., CMD+Tab)
    // Safe because it only cancels active drags, doesn't interfere with mousedown cleanup
    spectrogramBlurHandler = () => {
        if (spectrogramSelectionActive) {
            console.log('👋 Window blurred - canceling active selection to prevent stuck state');
            cancelSpectrogramSelection();
        }
    };
    window.addEventListener('blur', spectrogramBlurHandler);

    spectrogramSelectionSetup = true;

    canvas.addEventListener('mousedown', (e) => {
        // 🔍 DEBUG: Log zoom state when clicking on canvas
        if (!isStudyMode()) {
            console.log('🖱️ [MOUSEDOWN] Canvas clicked - checking zoom state:', {
                zoomStateInitialized: zoomState.isInitialized(),
                isInRegion: zoomState.isInitialized() ? zoomState.isInRegion() : 'N/A (not initialized)',
                zoomMode: zoomState.isInitialized() ? zoomState.mode : 'N/A',
                activeRegionId: zoomState.isInitialized() ? zoomState.activeRegionId : 'N/A'
            });
        }
        
        // 🎯 Check if region creation is enabled (requires "Begin Analysis" to be pressed)
        if (!State.isRegionCreationEnabled()) {
            // User clicked spectrogram before Begin Analysis - show helpful message (only if not in tutorial)
            import('./tutorial-state.js').then(({ isTutorialActive }) => {
                if (!isTutorialActive()) {
                    import('./tutorial-effects.js').then(({ setStatusText }) => {
                        setStatusText('Click Begin Analysis to create a region and interact with the spectrogram.', 'status info');
                    });
                }
            });
            return; // Don't allow spectrogram selection
        }
        
        // 🎯 NEW ARCHITECTURE: Allow drawing when zoomed into a region (no 'f' key needed!)
        // If not zoomed in, don't handle - user is looking at full view
        if (!zoomState.isInRegion()) {
            console.log('🖱️ [MOUSEDOWN] Not in region - returning early (zoom state says not zoomed in)');
            
            // Show helpful message - user needs to create a region first (only if not in tutorial)
            import('./tutorial-state.js').then(({ isTutorialActive }) => {
                if (!isTutorialActive()) {
                    import('./tutorial-effects.js').then(({ setStatusText }) => {
                        setStatusText('Create a new region to zoom in and select features.', 'status info');
                    });
                }
            });
            
            return;
        }
        
        // ✅ Check if clicking on an existing canvas box (click to re-draw feature)
        const canvasRect = canvas.getBoundingClientRect();
        const clickX = e.clientX - canvasRect.left;
        const clickY = e.clientY - canvasRect.top;
        
        const clickedBox = getClickedBox(clickX, clickY);
        if (clickedBox && !spectrogramSelectionActive) {
            // Clicked on a box - start frequency selection for that feature!
            startFrequencySelection(clickedBox.regionIndex, clickedBox.featureIndex);
            console.log(`🎯 Clicked canvas box - starting reselection for region ${clickedBox.regionIndex + 1}, feature ${clickedBox.featureIndex + 1}`);
            return; // Don't start new selection
        }

        // 🔥 FIX: ALWAYS force-reset state before starting new selection
        // Don't cancel and return - just clean up silently and start fresh
        let wasCleaningUp = false;
        if (spectrogramSelectionActive || spectrogramSelectionBox) {
            console.log('🧹 Cleaning up stale selection state before starting new one');
            wasCleaningUp = true;

            // Clear any existing timeout
            if (spectrogramSelectionTimeout) {
                clearTimeout(spectrogramSelectionTimeout);
                spectrogramSelectionTimeout = null;
            }

            // Delete any orphaned box (legacy DOM cleanup)
            if (spectrogramSelectionBox) {
                spectrogramSelectionBox.remove();
                spectrogramSelectionBox = null;
            }

            // 🔥 AGGRESSIVE RESET: Force reset ALL state variables to ensure clean slate
            spectrogramSelectionActive = false;
            spectrogramStartX = null;
            spectrogramStartY = null;
            spectrogramCurrentX = null;
            spectrogramCurrentY = null;
            
            // 🔥 FIX: Verify overlay context is ready - if not, we're in a stuck state!
            if (!spectrogramOverlayCtx || !spectrogramOverlayCanvas) {
                console.error('⚠️ [STUCK STATE DETECTED] Overlay context not ready after cleanup!');
                showStuckStateMessage();
                // Try to reinitialize overlay canvas
                const container = canvas.closest('.panel');
                if (container && !spectrogramOverlayCanvas) {
                    console.log('🔄 Attempting to reinitialize overlay canvas...');
                    // Recreate overlay canvas
                    spectrogramOverlayCanvas = document.createElement('canvas');
                    spectrogramOverlayCanvas.id = 'spectrogram-selection-overlay';
                    spectrogramOverlayCanvas.style.position = 'absolute';
                    spectrogramOverlayCanvas.style.pointerEvents = 'none';
                    spectrogramOverlayCanvas.style.zIndex = '20';  // Above spectrogram glow and other panels
                    spectrogramOverlayCanvas.style.background = 'transparent';
                    
                    const canvasRect = canvas.getBoundingClientRect();
                    const containerRect = container.getBoundingClientRect();
                    spectrogramOverlayCanvas.style.left = (canvasRect.left - containerRect.left) + 'px';
                    spectrogramOverlayCanvas.style.top = (canvasRect.top - containerRect.top) + 'px';
                    spectrogramOverlayCanvas.width = canvas.width;
                    spectrogramOverlayCanvas.height = canvas.height;
                    spectrogramOverlayCanvas.style.width = canvas.offsetWidth + 'px';
                    spectrogramOverlayCanvas.style.height = canvas.offsetHeight + 'px';
                    
                    container.appendChild(spectrogramOverlayCanvas);
                    spectrogramOverlayCtx = spectrogramOverlayCanvas.getContext('2d');
                    
                    if (spectrogramOverlayCtx) {
                        console.log('✅ Overlay canvas reinitialized successfully');
                        hideStuckStateMessage();
                    } else {
                        console.error('❌ Failed to reinitialize overlay canvas');
                        return; // Can't proceed without overlay context
                    }
                } else {
                    return; // Can't proceed without overlay context
                }
            }

            // DON'T return - continue to start new selection below!
        }
        
        // 🔥 VERIFY: After cleanup, ensure overlay context is still valid before proceeding
        if (!spectrogramOverlayCtx || !spectrogramOverlayCanvas) {
            console.error('⚠️ [STUCK STATE DETECTED] Overlay context missing before starting selection!');
            console.warn('🔄 Attempting emergency reinitialization of overlay canvas...');
            
            // EMERGENCY RECOVERY: Try to reinitialize the overlay canvas
            const canvas = document.getElementById('spectrogram-canvas');
            const container = document.getElementById('spectrogram-container');
            
            if (canvas && container) {
                // Remove any existing overlay canvas
                const existingOverlay = document.getElementById('spectrogram-selection-overlay');
                if (existingOverlay) {
                    existingOverlay.remove();
                }
                
                // Recreate overlay canvas
                spectrogramOverlayCanvas = document.createElement('canvas');
                spectrogramOverlayCanvas.id = 'spectrogram-selection-overlay';
                spectrogramOverlayCanvas.style.position = 'absolute';
                spectrogramOverlayCanvas.style.pointerEvents = 'none';
                spectrogramOverlayCanvas.style.zIndex = '20';
                spectrogramOverlayCanvas.style.background = 'transparent';
                
                const canvasRect = canvas.getBoundingClientRect();
                const containerRect = container.getBoundingClientRect();
                spectrogramOverlayCanvas.style.left = (canvasRect.left - containerRect.left) + 'px';
                spectrogramOverlayCanvas.style.top = (canvasRect.top - containerRect.top) + 'px';
                spectrogramOverlayCanvas.width = canvas.width;
                spectrogramOverlayCanvas.height = canvas.height;
                spectrogramOverlayCanvas.style.width = canvas.offsetWidth + 'px';
                spectrogramOverlayCanvas.style.height = canvas.offsetHeight + 'px';
                
                container.appendChild(spectrogramOverlayCanvas);
                spectrogramOverlayCtx = spectrogramOverlayCanvas.getContext('2d');
                
                if (spectrogramOverlayCtx) {
                    console.log('✅ Emergency overlay canvas reinitialization successful!');
                    hideStuckStateMessage();
                } else {
                    console.error('❌ Emergency reinitialization failed - showing safeguard message');
                    showStuckStateMessage();
                    return;
                }
            } else {
                console.error('❌ Cannot reinitialize - canvas or container not found');
                showStuckStateMessage();
                return;
            }
        }
        
        // Hide safeguard message if we got here successfully
        hideStuckStateMessage();
        
        spectrogramStartX = e.clientX - canvasRect.left;
        spectrogramStartY = e.clientY - canvasRect.top;
        spectrogramCurrentX = null;  // Reset - will be set on first mousemove
        spectrogramCurrentY = null;  // Reset - will be set on first mousemove
        spectrogramSelectionActive = true;

        // 🔥 FIX: Safety timeout - if mouseup never fires, auto-cancel after 5 seconds
        // This prevents stuck state when browser loses focus mid-drag
        if (spectrogramSelectionTimeout) {
            clearTimeout(spectrogramSelectionTimeout);
        }
        spectrogramSelectionTimeout = setTimeout(() => {
            if (spectrogramSelectionActive) {
                console.warn('⚠️ [SAFETY TIMEOUT] Mouseup never fired - auto-canceling selection');
                cancelSpectrogramSelection();
            }
        }, 5000); // 5 second safety timeout

        // 🔥 FIX: Don't create the box immediately - wait for drag to start
        // This prevents boxes from being created on every click when mouseup never fired
    });
    
    canvas.addEventListener('mousemove', (e) => {
        // 🔥 STUCK STATE DETECTION: If selection is active but overlay context is missing, we're stuck!
        if (spectrogramSelectionActive && !spectrogramOverlayCtx) {
            console.error('⚠️ [STUCK STATE DETECTED] Selection active but overlay context missing in mousemove!');
            showStuckStateMessage();
            // Force reset state
            spectrogramSelectionActive = false;
            spectrogramStartX = null;
            spectrogramStartY = null;
            spectrogramCurrentX = null;
            spectrogramCurrentY = null;
            return;
        }
        
        if (!spectrogramSelectionActive || !spectrogramOverlayCtx) return;
        
        const canvasRect = canvas.getBoundingClientRect();
        const currentX = e.clientX - canvasRect.left;
        const currentY = e.clientY - canvasRect.top;
        
        // ✅ PURE CANVAS: Update state
        spectrogramCurrentX = currentX;
        spectrogramCurrentY = currentY;
        
        // Draw ALL boxes (completed + current dragging)
        const width = spectrogramOverlayCanvas.width;
        const height = spectrogramOverlayCanvas.height;
        
        // Clear and redraw everything
        spectrogramOverlayCtx.clearRect(0, 0, width, height);
        
        // Redraw all completed boxes
        for (const box of completedSelectionBoxes) {
            drawSavedBox(spectrogramOverlayCtx, box);
        }
        
        // Draw current dragging box
        drawSpectrogramSelectionBox(spectrogramOverlayCtx, width, height);
    });
    
    // 🔥 FIX: Add mouseleave handler to cancel selection when mouse leaves canvas
    // This prevents stuck state when mouseup never fires (e.g., mouse leaves window)
    canvas.addEventListener('mouseleave', () => {
        if (spectrogramSelectionActive) {
            console.log('🖱️ Mouse left spectrogram canvas during selection - canceling');
            cancelSpectrogramSelection();
        }
    });
    
    // 🔥 SLEEP FIX: Reset mouse tracking state when mouse enters canvas after wake
    // This ensures mouse events work properly after computer sleep
    canvas.addEventListener('mouseenter', () => {
        // If we have stale state (coordinates but not active), reset everything
        // This handles the case where sleep broke mouse tracking
        if (!spectrogramSelectionActive && (spectrogramStartX !== null || spectrogramCurrentX !== null)) {
            console.log('🖱️ Mouse entered spectrogram canvas - resetting stale mouse state after sleep');
            spectrogramStartX = null;
            spectrogramStartY = null;
            spectrogramCurrentX = null;
            spectrogramCurrentY = null;
        }
    });
    
    // 🔥 FIX: Store handler reference so it can be removed
    spectrogramMouseUpHandler = async (e) => {
        if (!spectrogramSelectionActive) {
            return;
        }
        
        // Check if user actually dragged (minimum 5 pixels)
        if (spectrogramCurrentX === null || spectrogramCurrentY === null) {
            // User just clicked, didn't drag - cancel
            cancelSpectrogramSelection();
            return;
        }
        
        const dragDistanceX = Math.abs(spectrogramCurrentX - spectrogramStartX);
        const dragDistanceY = Math.abs(spectrogramCurrentY - spectrogramStartY);
        const dragDistance = Math.max(dragDistanceX, dragDistanceY);
        
        if (dragDistance < 5) {
            // Not enough drag - cancel
            cancelSpectrogramSelection();
            return;
        }
        
        const rect = canvas.getBoundingClientRect();
        const endY_css = spectrogramCurrentY;
        const endX_css = spectrogramCurrentX;

        // Convert CSS pixels to DEVICE pixels (same coordinate system as axis!)
        const scaleX = canvas.width / canvas.offsetWidth;
        const scaleY = canvas.height / canvas.offsetHeight;
        const startY_device = spectrogramStartY * scaleY;
        const endY_device = endY_css * scaleY;
        const startX_device = spectrogramStartX * scaleX;
        const endX_device = endX_css * scaleX;

        // 🔥 FIX: Clear safety timeout since mouseup fired successfully
        if (spectrogramSelectionTimeout) {
            clearTimeout(spectrogramSelectionTimeout);
            spectrogramSelectionTimeout = null;
        }
        
        // Stop accepting new mouse moves first
        spectrogramSelectionActive = false;
        
        // Call the handler (this creates the data for the feature and returns region/feature indices)
        const result = await handleSpectrogramSelection(
            startY_device, endY_device,
            canvas.height,  // ← DEVICE PIXELS (like axis)!
            startX_device, endX_device,
            canvas.width    // ← DEVICE PIXELS!
        );
        
        // ✅ Rebuild canvas boxes from feature data (ensures sync with array!)
        rebuildCanvasBoxesFromFeatures();
        
        // Reset coordinate state for next box
        spectrogramStartX = null;
        spectrogramStartY = null;
        spectrogramCurrentX = null;
        spectrogramCurrentY = null;
    };
    
    // 🔥 FIX: Use canvas instead of document for mouseup (like waveform does)
    // Canvas events survive browser focus changes better than document events
    canvas.addEventListener('mouseup', spectrogramMouseUpHandler);
    
    // 🔥 FIX: Store handler reference so it can be removed
    spectrogramKeyDownHandler = (e) => {
        if (e.key === 'Escape' && spectrogramSelectionActive) {
            // On escape, cancel the selection box
            cancelSpectrogramSelection();
        }
    };
    
    document.addEventListener('keydown', spectrogramKeyDownHandler);

    // 🔥 REMOVED: All blur/focus handlers - waveform doesn't have them and works perfectly!
    // The mousedown handler now cleans up stale state automatically when user clicks
    // The 5-second safety timeout still prevents infinite stuck states
    // User can press Escape to manually cancel if needed
    
    spectrogramSelectionSetup = true;
    if (!isStudyMode()) {
        console.log('🎯 Spectrogram frequency selection enabled');
    }
}

/**
 * Cancel active spectrogram selection (reset state)
 * Called when user presses Escape or exits feature selection mode
 * NOTE: Does NOT clear completed boxes - only cancels the current drag!
 */
export function cancelSpectrogramSelection() {
    // 🔥 FIX: Clear safety timeout when canceling
    if (spectrogramSelectionTimeout) {
        clearTimeout(spectrogramSelectionTimeout);
        spectrogramSelectionTimeout = null;
    }
    
    // ✅ PURE CANVAS: Just reset state
    spectrogramSelectionActive = false;
    spectrogramStartX = null;
    spectrogramStartY = null;
    spectrogramCurrentX = null;
    spectrogramCurrentY = null;
    
    // 🔥 FIX: Hide safeguard message when canceling (state is being reset)
    hideStuckStateMessage();
    
    // DON'T clear the overlay - that would delete all completed boxes!
    // Just redraw without the current incomplete drag
    if (spectrogramOverlayCtx) {
        spectrogramOverlayCtx.clearRect(0, 0, spectrogramOverlayCanvas.width, spectrogramOverlayCanvas.height);
        // Redraw all completed boxes
        for (const box of completedSelectionBoxes) {
            drawSavedBox(spectrogramOverlayCtx, box);
        }
        if (!isStudyMode()) console.log(`🧹 Canceled current drag, kept ${completedSelectionBoxes.length} completed boxes`);
    }
    
    // DEPRECATED: Legacy DOM box cleanup (kept for transition period)
    if (spectrogramSelectionBox) {
        spectrogramSelectionBox.remove();
        spectrogramSelectionBox = null;
    }
}

/**
 * Wrap text to fit within maxWidth
 * CRITICAL: ctx.font MUST be set before calling this function
 */
function wrapText(ctx, text, maxWidth) {
    if (!text) return [];

    const words = text.split(' ');
    const lines = [];
    let currentLine = '';

    for (let i = 0; i < words.length; i++) {
        const testLine = currentLine ? currentLine + ' ' + words[i] : words[i];
        const metrics = ctx.measureText(testLine);

        if (metrics.width > maxWidth && currentLine) {
            lines.push(currentLine);
            currentLine = words[i];
        } else {
            currentLine = testLine;
        }
    }

    if (currentLine) {
        lines.push(currentLine);
    }

    return lines.length > 0 ? lines : [text];
}

/**
 * Draw annotation text above a feature box with collision detection
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {HTMLCanvasElement} canvas - Canvas element
 * @param {Object} box - Feature box data (the box we're annotating)
 * @param {Array} placedAnnotations - Array tracking already placed annotations for collision detection
 * @param {Array} allBoxes - All feature boxes to check for collisions
 */
function drawAnnotation(ctx, canvas, box, placedAnnotations, allBoxes) {
    // Only draw annotations if box has notes
    if (!box.notes || box.notes.trim() === '') {
        return;
    }

    // Need zoom state and data times
    if (!State.dataStartTime || !State.dataEndTime || !zoomState.isInitialized()) {
        return;
    }

    // Calculate box position (same logic as drawSavedBox)
    const lowFreq = box.lowFreq;
    const highFreq = box.highFreq;

    const originalSampleRate = State.currentMetadata?.original_sample_rate || 100;
    const originalNyquist = originalSampleRate / 2;
    const playbackRate = State.currentPlaybackRate || 1.0;

    const scaleTransition = getScaleTransitionState();

    let lowFreqY_device, highFreqY_device;

    if (scaleTransition.inProgress && scaleTransition.oldScaleType) {
        const oldLowY = getYPositionForFrequencyScaled(lowFreq, originalNyquist, canvas.height, scaleTransition.oldScaleType, playbackRate);
        const newLowY = getYPositionForFrequencyScaled(lowFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
        const oldHighY = getYPositionForFrequencyScaled(highFreq, originalNyquist, canvas.height, scaleTransition.oldScaleType, playbackRate);
        const newHighY = getYPositionForFrequencyScaled(highFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);

        lowFreqY_device = oldLowY + (newLowY - oldLowY) * scaleTransition.interpolationFactor;
        highFreqY_device = oldHighY + (newHighY - oldHighY) * scaleTransition.interpolationFactor;
    } else {
        lowFreqY_device = getYPositionForFrequencyScaled(lowFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
        highFreqY_device = getYPositionForFrequencyScaled(highFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
    }

    const startTimestamp = new Date(box.startTime);
    const endTimestamp = new Date(box.endTime);

    // Use EXACT same interpolated time range as spectrogram elastic stretching!
    const interpolatedRange = getInterpolatedTimeRange();
    const displayStartMs = interpolatedRange.startTime.getTime();
    const displayEndMs = interpolatedRange.endTime.getTime();
    const displaySpanMs = displayEndMs - displayStartMs;

    const startMs = startTimestamp.getTime();
    const endMs = endTimestamp.getTime();

    const startProgress = (startMs - displayStartMs) / displaySpanMs;
    const endProgress = (endMs - displayStartMs) / displaySpanMs;

    const startX_device = startProgress * canvas.width;
    const endX_device = endProgress * canvas.width;

    // Check if box is off-screen
    if (endX_device < 0 || startX_device > canvas.width) {
        return;
    }

    const topY = Math.min(highFreqY_device, lowFreqY_device);
    const bottomY = Math.max(highFreqY_device, lowFreqY_device);
    if (bottomY < 0 || topY > canvas.height) {
        return;
    }

    const boxX = Math.min(startX_device, endX_device);
    const boxY = Math.min(highFreqY_device, lowFreqY_device);
    const boxWidth = Math.abs(endX_device - startX_device);
    const boxHeight = Math.abs(lowFreqY_device - highFreqY_device);

    // Text positioning
    ctx.save();
    ctx.font = '600 13px Arial, sans-serif';

    const maxWidth = 325; // Device pixels
    const lines = wrapText(ctx, box.notes, maxWidth);
    const lineHeight = 16; // Device pixels
    const totalTextHeight = lines.length * lineHeight;

    // Measure actual text width
    const textWidth = Math.max(...lines.map(line => ctx.measureText(line).width));
    const halfWidth = textWidth / 2;

    const padding = 10;
    const sideOffset = 30;

    // Helper function to check if text rect collides with anything
    const checkCollision = (textCenterX, textCenterY) => {
        const textLeft = textCenterX - halfWidth - padding;
        const textRight = textCenterX + halfWidth + padding;
        const textTop = textCenterY - totalTextHeight / 2 - padding;
        const textBottom = textCenterY + totalTextHeight / 2 + padding;

        // Check collision with all feature boxes (except the one we're annotating)
        for (const otherBox of allBoxes) {
            if (otherBox === box) continue; // Skip the box we're annotating

            // Calculate other box position (same logic as above)
            const otherOriginalSampleRate = State.currentMetadata?.original_sample_rate || 100;
            const otherOriginalNyquist = otherOriginalSampleRate / 2;
            const otherPlaybackRate = State.currentPlaybackRate || 1.0;
            const otherScaleTransition = getScaleTransitionState();

            let otherLowFreqY, otherHighFreqY;
            if (otherScaleTransition.inProgress && otherScaleTransition.oldScaleType) {
                const oldLowY = getYPositionForFrequencyScaled(otherBox.lowFreq, otherOriginalNyquist, canvas.height, otherScaleTransition.oldScaleType, otherPlaybackRate);
                const newLowY = getYPositionForFrequencyScaled(otherBox.lowFreq, otherOriginalNyquist, canvas.height, State.frequencyScale, otherPlaybackRate);
                const oldHighY = getYPositionForFrequencyScaled(otherBox.highFreq, otherOriginalNyquist, canvas.height, otherScaleTransition.oldScaleType, otherPlaybackRate);
                const newHighY = getYPositionForFrequencyScaled(otherBox.highFreq, otherOriginalNyquist, canvas.height, State.frequencyScale, otherPlaybackRate);
                otherLowFreqY = oldLowY + (newLowY - oldLowY) * otherScaleTransition.interpolationFactor;
                otherHighFreqY = oldHighY + (newHighY - oldHighY) * otherScaleTransition.interpolationFactor;
            } else {
                otherLowFreqY = getYPositionForFrequencyScaled(otherBox.lowFreq, otherOriginalNyquist, canvas.height, State.frequencyScale, otherPlaybackRate);
                otherHighFreqY = getYPositionForFrequencyScaled(otherBox.highFreq, otherOriginalNyquist, canvas.height, State.frequencyScale, otherPlaybackRate);
            }

            const otherStartTimestamp = new Date(otherBox.startTime);
            const otherEndTimestamp = new Date(otherBox.endTime);
            const otherInterpolatedRange = getInterpolatedTimeRange();
            const otherDisplayStartMs = otherInterpolatedRange.startTime.getTime();
            const otherDisplayEndMs = otherInterpolatedRange.endTime.getTime();
            const otherDisplaySpanMs = otherDisplayEndMs - otherDisplayStartMs;
            const otherStartMs = otherStartTimestamp.getTime();
            const otherEndMs = otherEndTimestamp.getTime();
            const otherStartProgress = (otherStartMs - otherDisplayStartMs) / otherDisplaySpanMs;
            const otherEndProgress = (otherEndMs - otherDisplayStartMs) / otherDisplaySpanMs;
            const otherStartX = otherStartProgress * canvas.width;
            const otherEndX = otherEndProgress * canvas.width;

            const otherBoxX = Math.min(otherStartX, otherEndX);
            const otherBoxY = Math.min(otherHighFreqY, otherLowFreqY);
            const otherBoxWidth = Math.abs(otherEndX - otherStartX);
            const otherBoxHeight = Math.abs(otherLowFreqY - otherHighFreqY);

            // Check rectangle overlap
            if (!(textRight < otherBoxX || textLeft > otherBoxX + otherBoxWidth ||
                  textBottom < otherBoxY || textTop > otherBoxY + otherBoxHeight)) {
                return true; // Collision!
            }
        }

        // Check collision with already placed annotations
        for (const placed of placedAnnotations) {
            const placedLeft = placed.x - placed.halfWidth - padding;
            const placedRight = placed.x + placed.halfWidth + padding;
            const placedTop = placed.y - placed.height / 2 - padding;
            const placedBottom = placed.y + placed.height / 2 + padding;

            if (!(textRight < placedLeft || textLeft > placedRight ||
                  textBottom < placedTop || textTop > placedBottom)) {
                return true; // Collision!
            }
        }

        return false; // No collision
    };

    // Try positions in order: above → below → left → right
    let finalTextX, finalTextY;
    let drawToSide = null;

    // Position 1: Above (default)
    let aboveX = boxX + (boxWidth / 2);
    let aboveY = boxY - 20 - totalTextHeight / 2;

    if (aboveY - totalTextHeight / 2 >= 10 && !checkCollision(aboveX, aboveY)) {
        // Above works!
        finalTextX = aboveX;
        finalTextY = aboveY;
    } else {
        // Position 2: Below
        let belowX = boxX + (boxWidth / 2);
        let belowY = boxY + boxHeight + 20 + totalTextHeight / 2;

        if (belowY + totalTextHeight / 2 <= canvas.height - 10 && !checkCollision(belowX, belowY)) {
            // Below works!
            finalTextX = belowX;
            finalTextY = belowY;
        } else {
            // Position 3: Left
            let leftX = boxX - halfWidth - sideOffset;
            let leftY = boxY + (boxHeight / 2);

            if (leftX - halfWidth >= 10 && !checkCollision(leftX, leftY)) {
                // Left works!
                finalTextX = leftX;
                finalTextY = leftY;
                drawToSide = 'left';
            } else {
                // Position 4: Right (fallback)
                let rightX = boxX + boxWidth + halfWidth + sideOffset;
                let rightY = boxY + (boxHeight / 2);
                finalTextX = rightX;
                finalTextY = rightY;
                drawToSide = 'right';
            }
        }
    }

    // Edge detection - keep text on-screen horizontally
    if (finalTextX - halfWidth < 10) {
        finalTextX = 10 + halfWidth;
    }
    if (finalTextX + halfWidth > canvas.width - 10) {
        finalTextX = canvas.width - 10 - halfWidth;
    }

    // Bottom guard - clamp to canvas if it would go off the bottom
    if (finalTextY + totalTextHeight > canvas.height - 10) {
        finalTextY = canvas.height - 10 - totalTextHeight;
    }

    // Top guard (final check after collision detection)
    if (finalTextY < 10) {
        finalTextY = 10;
    }

    // Record this annotation's position for future collision checks
    placedAnnotations.push({
        x: finalTextX,
        y: finalTextY,
        halfWidth: halfWidth,
        height: totalTextHeight
    });

    // Draw connecting line
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.lineWidth = 2;
    ctx.setLineDash([3, 3]);

    ctx.beginPath();
    if (drawToSide === 'left') {
        // Line from right side of text to left side of box
        ctx.moveTo(finalTextX + halfWidth, finalTextY + totalTextHeight / 2);
        ctx.lineTo(boxX, boxY + boxHeight / 2);
    } else if (drawToSide === 'right') {
        // Line from left side of text to right side of box
        ctx.moveTo(finalTextX - halfWidth, finalTextY + totalTextHeight / 2);
        ctx.lineTo(boxX + boxWidth, boxY + boxHeight / 2);
    } else {
        // Determine if annotation is above or below the box
        const annotationIsBelow = finalTextY > boxY + boxHeight;
        if (annotationIsBelow) {
            // Line from top of text to bottom of box
            ctx.moveTo(finalTextX, finalTextY);
            ctx.lineTo(boxX + boxWidth / 2, boxY + boxHeight);
        } else {
            // Line from bottom of text to top of box
            ctx.moveTo(finalTextX, finalTextY + totalTextHeight);
            ctx.lineTo(boxX + boxWidth / 2, boxY);
        }
    }
    ctx.stroke();

    ctx.setLineDash([]); // Reset dash pattern

    // Draw text with shadow for readability
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
    ctx.shadowBlur = 4;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;

    for (let i = 0; i < lines.length; i++) {
        const lineY = finalTextY + (i * lineHeight);
        ctx.fillText(lines[i], finalTextX, lineY);
    }

    ctx.restore();
}

/**
 * Draw a saved box from eternal coordinates (time/frequency)
 * EXACT COPY of orange box coordinate conversion logic!
 */
function drawSavedBox(ctx, box) {
    const canvas = document.getElementById('spectrogram');
    if (!canvas) return;
    
    // Need zoom state and data times
    if (!State.dataStartTime || !State.dataEndTime || !zoomState.isInitialized()) {
        return;
    }
    
    // Convert eternal coordinates (time/frequency) to pixel positions
    const lowFreq = box.lowFreq;
    const highFreq = box.highFreq;
    
    // Get original sample rate from metadata (same as orange boxes!)
    // NOT hardcoded - comes from State.currentMetadata.original_sample_rate
    const originalSampleRate = State.currentMetadata?.original_sample_rate || 100;
    const originalNyquist = originalSampleRate / 2; // Calculated from metadata, not assumed!
    
    // Get current playback rate (CRITICAL for stretching!)
    const playbackRate = State.currentPlaybackRate || 1.0;
    
    // Convert frequencies to Y positions (DEVICE PIXELS) - WITH SCALE INTERPOLATION! 🎯
    // Use exact same interpolation logic as Y-axis ticks during scale transitions
    const scaleTransition = getScaleTransitionState();
    
    let lowFreqY_device, highFreqY_device;
    
    if (scaleTransition.inProgress && scaleTransition.oldScaleType) {
        // Interpolate between old and new scale positions (like axis ticks!)
        const oldLowY = getYPositionForFrequencyScaled(lowFreq, originalNyquist, canvas.height, scaleTransition.oldScaleType, playbackRate);
        const newLowY = getYPositionForFrequencyScaled(lowFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
        const oldHighY = getYPositionForFrequencyScaled(highFreq, originalNyquist, canvas.height, scaleTransition.oldScaleType, playbackRate);
        const newHighY = getYPositionForFrequencyScaled(highFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
        
        lowFreqY_device = oldLowY + (newLowY - oldLowY) * scaleTransition.interpolationFactor;
        highFreqY_device = oldHighY + (newHighY - oldHighY) * scaleTransition.interpolationFactor;
    } else {
        // No transition - use current scale directly
        lowFreqY_device = getYPositionForFrequencyScaled(lowFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
        highFreqY_device = getYPositionForFrequencyScaled(highFreq, originalNyquist, canvas.height, State.frequencyScale, playbackRate);
    }
    
    // Convert times to X positions (DEVICE PIXELS) - EXACT COPY of orange box logic!
    const startTimestamp = new Date(box.startTime);
    const endTimestamp = new Date(box.endTime);

    // Use EXACT same interpolated time range as spectrogram elastic stretching!
    const interpolatedRange = getInterpolatedTimeRange();
    const displayStartMs = interpolatedRange.startTime.getTime();
    const displayEndMs = interpolatedRange.endTime.getTime();
    const displaySpanMs = displayEndMs - displayStartMs;
    
    const startMs = startTimestamp.getTime();
    const endMs = endTimestamp.getTime();
    
    const startProgress = (startMs - displayStartMs) / displaySpanMs;
    const endProgress = (endMs - displayStartMs) / displaySpanMs;
    
    // Convert to DEVICE pixels (orange boxes use CSS pixels with canvas.offsetWidth)
    const startX_device = startProgress * canvas.width;
    const endX_device = endProgress * canvas.width;
    
    // Check if completely off-screen horizontally (don't draw)
    if (endX_device < 0 || startX_device > canvas.width) {
        return;
    }
    
    // Check if completely off-screen vertically (don't draw)
    const topY = Math.min(highFreqY_device, lowFreqY_device);
    const bottomY = Math.max(highFreqY_device, lowFreqY_device);
    if (bottomY < 0 || topY > canvas.height) {
        return;
    }
    
    // Calculate box dimensions
    const x = Math.min(startX_device, endX_device);
    const y = Math.min(highFreqY_device, lowFreqY_device);
    const width = Math.abs(endX_device - startX_device);
    const height = Math.abs(lowFreqY_device - highFreqY_device);
    
    // Draw the box (red, like old temp boxes)
    ctx.strokeStyle = '#ff4444';
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, width, height);
    
    ctx.fillStyle = 'rgba(255, 68, 68, 0.2)';
    ctx.fillRect(x, y, width, height);
    
    // Add feature number label in upper left corner (like orange boxes!)
    const numberText = (box.featureIndex + 1).toString(); // 1-indexed for display
    ctx.font = '16px Arial, sans-serif'; // Removed bold for flatter look
    ctx.fillStyle = 'rgba(255, 160, 80, 0.9)'; // Slightly more opaque, less 3D
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    
    // No shadow - completely flat text
    ctx.shadowBlur = 0;
    ctx.shadowColor = 'transparent';
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;
    
    // Position: 6px from left, 7px from top (moved down more)
    ctx.fillText(numberText, x + 6, y + 7);
}

/**
 * Draw active selection box on spectrogram canvas
 * ✅ PURE CANVAS: Renders directly with ctx.strokeRect() - no DOM manipulation!
 * Called from playhead rendering loop (spectrogram-playhead.js)
 */
export function drawSpectrogramSelectionBox(ctx, canvasWidth, canvasHeight) {
    // Only draw if actively selecting
    if (!spectrogramSelectionActive || spectrogramStartX === null || spectrogramStartY === null) {
        return;
    }
    
    // Only draw if user has dragged at least 5 pixels
    if (spectrogramCurrentX === null || spectrogramCurrentY === null) {
        return;
    }
    
    const dragDistanceX = Math.abs(spectrogramCurrentX - spectrogramStartX);
    const dragDistanceY = Math.abs(spectrogramCurrentY - spectrogramStartY);
    const dragDistance = Math.max(dragDistanceX, dragDistanceY);
    
    if (dragDistance < 5) {
        return; // Not enough drag yet
    }
    
    // Convert CSS pixels to device pixels for rendering
    const canvas = document.getElementById('spectrogram');
    if (!canvas) return;
    
    const scaleX = canvas.width / canvas.offsetWidth;
    const scaleY = canvas.height / canvas.offsetHeight;
    
    const startX_device = spectrogramStartX * scaleX;
    const startY_device = spectrogramStartY * scaleY;
    const currentX_device = spectrogramCurrentX * scaleX;
    const currentY_device = spectrogramCurrentY * scaleY;
    
    // Calculate normalized rectangle
    const x = Math.min(startX_device, currentX_device);
    const y = Math.min(startY_device, currentY_device);
    const width = Math.abs(currentX_device - startX_device);
    const height = Math.abs(currentY_device - startY_device);
    
    // Draw selection box on canvas (matches the old DOM style)
    ctx.strokeStyle = '#ff4444';
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, width, height);
    
    // Semi-transparent fill
    ctx.fillStyle = 'rgba(255, 68, 68, 0.2)';
    ctx.fillRect(x, y, width, height);
}

/**
 * Cleanup spectrogram selection event listeners
 * 🔥 FIX: Prevents memory leaks from accumulating listeners
 */
export function cleanupSpectrogramSelection() {
    if (spectrogramMouseUpHandler) {
        const canvas = document.getElementById('spectrogram');
        if (canvas) {
            // 🔥 FIX: Remove from canvas, not document (matches the addEventListener)
            canvas.removeEventListener('mouseup', spectrogramMouseUpHandler);
        }
        spectrogramMouseUpHandler = null;
    }
    if (spectrogramKeyDownHandler) {
        document.removeEventListener('keydown', spectrogramKeyDownHandler);
        spectrogramKeyDownHandler = null;
    }
    if (spectrogramVisibilityHandler) {
        document.removeEventListener('visibilitychange', spectrogramVisibilityHandler);
        spectrogramVisibilityHandler = null;
    }
    if (spectrogramFocusHandler) {
        window.removeEventListener('focus', spectrogramFocusHandler);
        spectrogramFocusHandler = null;
    }
    if (spectrogramBlurHandler) {
        window.removeEventListener('blur', spectrogramBlurHandler);
        spectrogramBlurHandler = null;
    }
    if (spectrogramResizeObserver) {
        spectrogramResizeObserver.disconnect();
        spectrogramResizeObserver = null;
    }
    if (spectrogramRepositionOnVisibility) {
        document.removeEventListener('visibilitychange', spectrogramRepositionOnVisibility);
        spectrogramRepositionOnVisibility = null;
    }

    // Clear any active timeouts
    if (spectrogramSelectionTimeout) {
        clearTimeout(spectrogramSelectionTimeout);
        spectrogramSelectionTimeout = null;
    }
    
    // Remove overlay canvas
    if (spectrogramOverlayCanvas) {
        spectrogramOverlayCanvas.remove();
        spectrogramOverlayCanvas = null;
        spectrogramOverlayCtx = null;
    }

    spectrogramSelectionSetup = false;
}

