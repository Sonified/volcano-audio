# Tutorial Flow: From Feature Description to End

This document outlines every step in the tutorial from when the user submits their first feature description through to the end.

---

## Part 1: After First Feature Description (in `runFeatureSelectionTutorial()`)

| Step | Message | Duration | Action |
|------|---------|----------|--------|
| 1 | "Nice!" | 1.5s | Celebrate description submission |
| 2 | "Click the drop down menu on the far left to choose whether this event is unique or repeating" | 15s timeout | Glow repetition dropdown, wait for click |
| 3 | *(after click)* | 1s | Brief pause |
| 4 | "Impulsive events are short, and continuous events are long" | 15s timeout | Glow type dropdown, wait for click |
| 5 | *(after click)* | 1s | Brief pause |
| 6 | "In the future, you can use this box to change your selection (it's disabled for now)." | 4s | Glow select feature button |
| 7 | "To add another feature, just click and drag on the spectrogram to draw a new box." | **WAIT** | Glow spectrogram, wait for `waitForFeatureSelection()` |
| 8 | "Excellent!" | 1.5s | Celebrate second feature |

---

## Part 2: Zoom Out Tutorial (in `runZoomOutTutorial()`)

**Precondition:** Must be zoomed into a region (otherwise returns early with warning!)

| Step | Message | Duration | Action |
|------|---------|----------|--------|
| 9 | "Let's return to the full-day view by pressing ESC or clicking the orange return arrow." | **WAIT** | Wait for `waitForZoomOut()` |
| 10 | *(after zoom out)* | 2s | Enable all region buttons |
| 11 | "Those are the basics!" | 2s | Success message |
| 12 | "Using hotkeys will help you move around quickly!" | 5s | Info message |

---

## Part 3: Second Region Tutorial (in `runSecondRegionTutorial()`)

| Step | Message | Duration | Action |
|------|---------|----------|--------|
| 13 | "Click and drag on the waveform to create a new region." | **WAIT** | Pulse waveform, overlay "Click and drag here", wait for `waitForRegionCreation(1)` |
| 14 | "Great!" | 2s | Celebrate second region creation |

**IF `secondRegionIndex >= 1` (at least 2 regions exist):**

| Step | Message | Duration | Action |
|------|---------|----------|--------|
| 15 | "To zoom in on this second region, just press (2) on your keyboard." | **WAIT** | Wait for `waitForNumberKeyPress('2')` |
| 16 | *(after press)* | 1s | Brief pause |
| 17 | "Now press 2 again to play this region from the beginning!" | **WAIT** | Wait for `waitForNumberKeyPress('2')` |
| 18 | "Excellent! Now press 1 to jump to our first region." | **WAIT** | Wait for `waitForNumberKeyPress('1')` |
| 19 | *(after press)* | 1s | Brief pause |
| 20 | "And now press 1 to play back this region." | **WAIT** | Wait for `waitForNumberKeyPress('1')` |
| 21 | *(after press)* | 2s | Brief pause |
| 22 | "Great! Now hit escape to jump back to the main screen." | **WAIT** | Wait for `waitForZoomOut()` |
| 23 | *(after escape)* | 1s | Brief pause |
| 24 | "This Tutorial is now complete! Continue your analysis and hit Submit when you are done." | 5s | Enable all restricted features |
| 25 | "Have fun exploring! There's no minimum or maximum feature requirement." | 5s | Final message |

---

## Part 4: Begin Analysis Tutorial (in `runBeginAnalysisTutorial()`)

*Called from `runMainTutorial()` AFTER `runFrequencyScaleTutorial()` returns*

| Step | Message | Duration | Action |
|------|---------|----------|--------|
| 26 | "For your weekly sessions you will begin by selecting one volcano to work with." | 6s | Info message |
| 27 | "Click Begin Analysis now to end the tutorial ↘️" | 2.5s then **WAIT** | Right-align, fade in Begin Analysis button, wait for click |
| 28 | *(after click)* | 2s | Brief pause |
| 29 | "Press the Complete button when you are ready to share your findings." | - | Final message (stays) |

---

## Call Chain

```
runMainTutorial()
  └── await runFrequencyScaleTutorial()
        └── await runFeatureSelectionTutorial()     ← Part 1
              └── await runZoomOutTutorial()        ← Part 2
                    └── await runSecondRegionTutorial()  ← Part 3
  └── await runBeginAnalysisTutorial()              ← Part 4
```

---

## Known Issues / Things to Check

1. **`waitForRegionCreation(1)`** - Now correctly waits for `regions.length > 1` (second region)

2. **`if (secondRegionIndex >= 1)`** - This check SKIPS the entire hotkey section if only 1 region exists. If `waitForRegionCreation(1)` times out or is skipped, the hotkey tutorial won't run.

3. **`runZoomOutTutorial()` precondition** - If not zoomed into a region, it returns early and skips everything after!

4. **The message "Click and drag on the waveform to create a new region."** appears in `runSecondRegionTutorial()` at step 13. If you're seeing this too early, the tutorial might be jumping ahead.

---

## Debug Points

To debug where the tutorial is, add console logs:
- Start of `runFeatureSelectionTutorial()`: `console.log('🎯 ENTERING runFeatureSelectionTutorial')`
- Start of `runZoomOutTutorial()`: `console.log('🎯 ENTERING runZoomOutTutorial')`  
- Start of `runSecondRegionTutorial()`: `console.log('🎯 ENTERING runSecondRegionTutorial')`
- Start of `runBeginAnalysisTutorial()`: `console.log('🎯 ENTERING runBeginAnalysisTutorial')`

