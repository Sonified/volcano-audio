# Project Instructions

## When to Read README.md First

README documents architecture that would take time to spider out. Read it for:

- **Session/volcano behavior**: When does volcano lock/unlock? What clears on timeout? What persists?
- **localStorage flags**: Full list of flags, their lifetimes (persistent vs session-scoped), and what clears them
- **Thread model**: 3-tier diagram (Main Thread → Web Workers → AudioWorklet)
- **Data flow**: CDN → data-fetcher → worker → AudioWorklet pipeline with diagrams
- **Study workflow**: Visit-dependent phases (W1S1 vs W2S1 vs W1S2), survey order
- **Frontend modules**: Table of all 40+ JS modules and their purposes
- **App modes**: 8 modes (PERSONAL, DEV, STUDY_CLEAN, etc.) and what each does

## When to Search Directly
- Specific bugs or implementation details
- Single-file changes
- Grep-able queries (function names, error messages)

## The Soul of This Codebase

**This is scientific audio software for research participants.** Every UX decision matters - confused users = bad data.

**Patterns you'll see everywhere:**
- `🔥 FIX:` comments mark hard-won bug fixes - read them before changing nearby code
- Memory leaks are the enemy - always clean up event listeners, RAF loops, timeouts
- State lives in `audio-state.js` - 100+ getters/setters, single source of truth
- Regions store timestamps (not sample indices) because time ranges change with speed

**The Zen Pattern (from the feature box odyssey):**
- One source of truth for positioning: `getYPositionForFrequencyScaled()` for Y, `getInterpolatedTimeRange()` for X
- When something drifts, find THE function everything else uses and use it too

**Test modes only set FLAGS** - never add `if (testMode)` branches. Fix the real code.

## Where Things Live
| What | Where |
|------|-------|
| All state | `audio-state.js` |
| Session flags | `study-workflow.js` → `STORAGE_KEYS` |
| Timeout logic | `session-management.js` |
| Region storage | `region-tracker.js` (per-volcano localStorage) |
| Tutorial flow | `tutorial-coordinator.js` (async/await) |
| Audio playback | `workers/audio-worklet.js` → `SeismicProcessor` |
| Survey submission | `qualtrics-api.js` + `Qualtrics/participant-response-manager.js` |
| R2 backup uploads | `data-uploader.js` |

## Data Submission Flow
1. Surveys collected throughout session → stored in localStorage (`participant_response_{id}`)
2. On session complete: `qualtrics-api.js` submits to Qualtrics API
3. Backup: `data-uploader.js` uploads to R2 (`volcano-audio-anonymized-data/participants/{id}/`)
   - `user-status/status.json` - overwritten each time (current state)
   - `submissions/{id}_Complete_{timestamp}.json` - append-only (permanent record)
4. CNS post-survey: `cns-submission.js` uploads to R2 (`volcano-audio-anonymized-data/CNS_POST/`)

## Data Archaeology (Dec 2025)

**Critical Discovery**: ParticipantID is NOT a top-level field in Qualtrics exports, but IS embedded in the `SessionTracking` JSON field!

```python
# To extract participant IDs from Qualtrics export:
import json
st = response['values'].get('SessionTracking')
if st:
    st_data = json.loads(st)
    participant_id = st_data.get('participantId')
```

**Data Sources & Linkage:**
| Source | Has ParticipantID | Notes |
|--------|-------------------|-------|
| R2 `submissions/` | ✅ Top-level field | Primary source after Nov 19 |
| Qualtrics `SessionTracking` | ✅ Nested in JSON | 81/92 submissions have it |
| Qualtrics top-level | ❌ Not captured | Embedded data field not configured |
| CNS pre-survey | ❌ Email only | Cannot link to study participants |

**Known Data Gaps:**
- Nov 13, 2025: First 11 Qualtrics submissions have NO SessionTracking (before feature existed)
- Nov 13-19: 3 participants (`R_3AKHxZD5uNa4XOF`, `R_5w3fiJBdMtLFkA1`, `R_6GB2MdyhKnNXJl1`) only in Qualtrics, not R2