/**
 * keyboard-shortcuts.js
 * Keyboard shortcuts for region navigation and feature drawing
 */

import { zoomToRegion, zoomToFull, getCurrentRegions, getActiveRegionIndex, isInFrequencySelectionMode, startFrequencySelection, addFeature, createRegionFromSelectionTimes, toggleRegionPlay, stopFrequencySelection } from './region-tracker.js';
import { zoomState } from './zoom-state.js';
import * as State from './audio-state.js';
import { changeFrequencyScale } from './spectrogram-renderer.js';
import { isStudyMode } from './master-modes.js';

// 🔥 FIX: Track if shortcuts are initialized to prevent duplicate listeners
let keyboardShortcutsInitialized = false;

/**
 * Initialize keyboard shortcuts
 */
export function initKeyboardShortcuts() {
    // 🔥 FIX: Only add listener once to prevent memory leaks
    if (keyboardShortcutsInitialized) {
        return;
    }
    
    // Use window.addEventListener with capture phase to ensure we catch events
    // This ensures keyboard shortcuts work even if other handlers prevent default
    window.addEventListener('keydown', handleKeyboardShortcut, true);
    keyboardShortcutsInitialized = true;
    // Only log in dev/personal modes, not study mode
    if (!isStudyMode()) {
        console.log('⌨️ Keyboard shortcuts initialized');
    }
}

/**
 * Cleanup keyboard shortcuts event listeners
 * 🔥 FIX: Prevents memory leaks
 */
export function cleanupKeyboardShortcuts() {
    if (keyboardShortcutsInitialized) {
        window.removeEventListener('keydown', handleKeyboardShortcut, true);
        keyboardShortcutsInitialized = false;
    }
}

/**
 * Handle keyboard shortcut events
 */
function handleKeyboardShortcut(event) {
    // Debug: Log Escape key presses
    if (event.key === 'Escape' && !isStudyMode()) {
        console.log('🔍 [ESCAPE DEBUG] handleKeyboardShortcut() called with Escape key');
        console.log('🔍 [ESCAPE DEBUG] event.target:', event.target);
        console.log('🔍 [ESCAPE DEBUG] event.target.tagName:', event.target.tagName);
    }
    
    // Don't capture shortcuts when user is typing in inputs, textareas, or contenteditable elements
    // EXCEPT for Escape key - Escape should always work to exit modes/zoom out
    const isTextInput = event.target.tagName === 'INPUT' && 
                       event.target.type !== 'range' && 
                       event.target.type !== 'checkbox';
    const isTextarea = event.target.tagName === 'TEXTAREA';
    const isContentEditable = event.target.isContentEditable;
    
    // Allow Escape key to work even when in text inputs/textareas
    const isEscapeKey = event.key === 'Escape';
    const isTypingInField = isTextInput || isTextarea || isContentEditable;
    
    if (isTypingInField && !isEscapeKey) {
        return; // Let browser handle normally (but not Escape)
    }
    
    // Debug: Log all key presses during tutorial (can be removed later)
    // if (event.key === 'Escape' || (event.key >= '1' && event.key <= '9')) {
    //     console.log(`⌨️ Keyboard shortcut handler called: key=${event.key}, target=${event.target.tagName}`);
    // }
    
    // Number keys (1-9): Zoom to region, or play region if already zoomed into it
    if (event.key >= '1' && event.key <= '9') {
        const regionIndex = parseInt(event.key) - 1; // Convert '1' to 0, '2' to 1, etc.
        const regions = getCurrentRegions();
        
        if (regionIndex < regions.length) {
            event.preventDefault();
            const region = regions[regionIndex];
            
            // 🎓 Tutorial: Resolve promise if waiting for this specific number key
            if (State.waitingForNumberKeyPress && State.targetNumberKey === event.key && State._numberKeyPressResolve) {
                State.setWaitingForNumberKeyPress(false);
                const resolve = State._numberKeyPressResolve;
                State.setNumberKeyPressResolve(null);
                State.setTargetNumberKey(null);
                resolve();
            }
            
            // Always execute the action, even during tutorial (tutorial will track it separately)
            // Check if we're already zoomed into this specific region
            if (zoomState.isInRegion() && zoomState.getCurrentRegionId() === region.id) {
                // Already zoomed into this region - play it from the start
                toggleRegionPlay(regionIndex);
                console.log(`▶️ Playing region ${regionIndex + 1} from start`);
            } else {
                // Not zoomed into this region - zoom to it
                zoomToRegion(regionIndex);
            }
        }
        return;
    }
    
    // 'f' key: DEPRECATED - no longer needed, click-to-draw is always active when zoomed in
    // Keeping this here commented out for reference, can be removed later
    // if (event.key === 'f' || event.key === 'F') {
    //     // Feature drawing is now always enabled when zoomed into a region
    //     // Just clicking and dragging on the spectrogram will create features
    //     return;
    // }
    
    // 'r' key: Confirm/add region from current selection
    if (event.key === 'r' || event.key === 'R') {
        // Check if region creation is enabled (requires "Begin Analysis" to be pressed)
        if (!State.isRegionCreationEnabled()) {
            console.log('🔒 Region creation disabled - please press "Begin Analysis" first');
            return;
        }
        
        // Check if there's a valid selection
        if (State.selectionStart !== null && State.selectionEnd !== null) {
            event.preventDefault();
            createRegionFromSelectionTimes(State.selectionStart, State.selectionEnd);
            console.log('✅ Region created from selection');
        }
        return;
    }
    
    // Frequency scale shortcuts: 'c' for linear, 'v' for square root, 'b' for logarithmic
    if (event.key === 'c' || event.key === 'C') {
        event.preventDefault();
        const select = document.getElementById('frequencyScale');
        if (select && State.frequencyScale !== 'linear') {
            select.value = 'linear';
            changeFrequencyScale();
            console.log('📊 Frequency scale changed to: Linear');
        }
        
        // 🎓 Tutorial: Track keyboard shortcut presses
        if (State.waitingForFrequencyScaleKeys) {
            State.setFrequencyScaleKeyPressCount(State.frequencyScaleKeyPressCount + 1);
            if (State.frequencyScaleKeyPressCount >= 2 && State._frequencyScaleKeysResolve) {
                State.setWaitingForFrequencyScaleKeys(false);
                const resolve = State._frequencyScaleKeysResolve;
                State.setFrequencyScaleKeysResolve(null);
                State.setFrequencyScaleKeyPressCount(0);
                resolve();
            }
        }
        return;
    }
    
    if (event.key === 'v' || event.key === 'V') {
        event.preventDefault();
        const select = document.getElementById('frequencyScale');
        if (select && State.frequencyScale !== 'sqrt') {
            select.value = 'sqrt';
            changeFrequencyScale();
            console.log('📊 Frequency scale changed to: Square Root');
        }
        
        // 🎓 Tutorial: Track keyboard shortcut presses
        if (State.waitingForFrequencyScaleKeys) {
            State.setFrequencyScaleKeyPressCount(State.frequencyScaleKeyPressCount + 1);
            if (State.frequencyScaleKeyPressCount >= 2 && State._frequencyScaleKeysResolve) {
                State.setWaitingForFrequencyScaleKeys(false);
                const resolve = State._frequencyScaleKeysResolve;
                State.setFrequencyScaleKeysResolve(null);
                State.setFrequencyScaleKeyPressCount(0);
                resolve();
            }
        }
        return;
    }
    
    if (event.key === 'b' || event.key === 'B') {
        event.preventDefault();
        const select = document.getElementById('frequencyScale');
        if (select && State.frequencyScale !== 'logarithmic') {
            select.value = 'logarithmic';
            changeFrequencyScale();
            console.log('📊 Frequency scale changed to: Logarithmic');
        }
        
        // 🎓 Tutorial: Track keyboard shortcut presses
        if (State.waitingForFrequencyScaleKeys) {
            State.setFrequencyScaleKeyPressCount(State.frequencyScaleKeyPressCount + 1);
            if (State.frequencyScaleKeyPressCount >= 2 && State._frequencyScaleKeysResolve) {
                State.setWaitingForFrequencyScaleKeys(false);
                const resolve = State._frequencyScaleKeysResolve;
                State.setFrequencyScaleKeysResolve(null);
                State.setFrequencyScaleKeyPressCount(0);
                resolve();
            }
        }
        return;
    }
    
    // Escape key: Zoom out immediately (exiting feature selection mode as part of the same action)
    if (event.key === 'Escape') {
        if (!isStudyMode()) {
            console.log('🔍 [ESCAPE DEBUG] Escape key pressed');
            console.log('🔍 [ESCAPE DEBUG] isTypingInField:', isTypingInField);
            console.log('🔍 [ESCAPE DEBUG] isInFrequencySelectionMode():', isInFrequencySelectionMode());
            console.log('🔍 [ESCAPE DEBUG] zoomState.isInRegion():', zoomState.isInRegion());
            console.log('🔍 [ESCAPE DEBUG] zoomState:', {
                mode: zoomState.mode,
                activeRegionId: zoomState.activeRegionId,
                initialized: zoomState.isInitialized()
            });
        }

        // If typing in a field, blur it first so Escape works
        if (isTypingInField) {
            if (!isStudyMode()) console.log('🔍 [ESCAPE DEBUG] Blurring active input/textarea');
            event.target.blur();
        }

        // Exit feature selection mode if active (as part of zoom out, not a separate step)
        if (isInFrequencySelectionMode()) {
            if (!isStudyMode()) console.log('🔍 [ESCAPE DEBUG] Exiting feature selection mode as part of zoom out');
            stopFrequencySelection();
            // Don't return - continue to zoom out
        }

        // Zoom out if in a region
        if (zoomState.isInRegion()) {
            // console.log('🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴');
            // console.log('🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴');
            // console.log('🔴🔴 ESCAPE PRESSED - STARTING ZOOM OUT 🔴🔴');
            
            // 🔍 DIAGNOSTIC: Check what's currently visible on the MAIN canvas before zoom out
            // const mainCanvas = document.getElementById('spectrogram');
            // if (mainCanvas) {
            //     const mainCtx = mainCanvas.getContext('2d', { willReadFrequently: true });
            //     const midX = Math.floor(mainCanvas.width / 2);
            //     const midY = Math.floor(mainCanvas.height / 2);
            //     const visiblePixel = mainCtx.getImageData(midX, midY, 1, 1).data;
            //     console.log(`🔍 MAIN CANVAS (what user sees) center pixel:`, {
            //         rgba: `${visiblePixel[0]}, ${visiblePixel[1]}, ${visiblePixel[2]}, ${visiblePixel[3]}`,
            //         brightness: visiblePixel[0] + visiblePixel[1] + visiblePixel[2]
            //     });
            // }
            
            // console.log('🔍 [ESCAPE DEBUG] In region - preventing default and calling zoomToFull()');
            event.preventDefault();
            zoomToFull();
            // console.log('🔙 Escape key: Zoomed out to full view');
        } else {
            console.log('🔍 [ESCAPE DEBUG] NOT in region and NOT in feature selection - Escape key ignored');
        }
        return;
    }
    
    // Enter key: Trigger first fetch (only works before first fetch, handled in main.js)
    // We don't handle it here, but we need to make sure we don't prevent it
    // The actual handler is in main.js DOMContentLoaded
}

