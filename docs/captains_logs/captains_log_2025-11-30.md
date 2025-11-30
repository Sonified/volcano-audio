# Captain's Log - November 30, 2025

## v2.72 Fix: Speed-Adjusted Sample Counting for Fade Triggers

### The Bug
When calculating how many input samples correspond to a fixed wall-clock time (like a 50ms fade), the formula in `audio-worklet.js` was inverted:

```javascript
// ❌ WRONG - triggers fade way too early at slow speeds
const FADE_SAMPLES_INPUT = Math.floor(FADE_SAMPLES_OUTPUT / this.speed);
```

### The Fix
```javascript
// ✅ CORRECT - multiply by speed, not divide
const FADE_SAMPLES_INPUT = Math.floor(FADE_SAMPLES_OUTPUT * this.speed);
```

### Why This Matters
In a variable-speed audio worklet:
- **Output samples** = samples sent to speakers (always at 44.1kHz)
- **Input samples** = samples consumed from the source buffer
- **Speed** = ratio of input consumption rate to output rate

At 0.1x speed: You consume 0.1 input samples per output sample
At 2x speed: You consume 2 input samples per output sample

To trigger a fade 50ms before the end (2205 output samples at 44.1kHz):
- At 0.1x: Only 2205 × 0.1 = 220 input samples will be consumed in that time
- At 2x: 2205 × 2 = 4410 input samples will be consumed in that time

The input sample warning threshold should scale proportionally with speed (multiply), not inversely (divide).

### General Rule
When converting from wall-clock time to input samples consumed:
```
input_samples = output_samples * speed
```

When converting from input samples to wall-clock time:
```
wall_clock_time = input_samples / speed
```

### Files Modified
- `workers/audio-worklet.js`: Fixed fade trigger calculation on line 517

---

**Status:** ✅ Fixed  
**Version:** v2.72

