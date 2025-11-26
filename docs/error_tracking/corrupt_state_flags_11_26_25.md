# Corrupted Session State Flags - November 26, 2025

## Bug Discovery

User (Robert) encountered a completely locked interface on the live production site. The entire UI was frozen - couldn't click Fetch Data button, volcano dropdown was disabled, no modals appeared.

## Diagnostic Output

```
═══════════════════════════════════════════════════════════
📊 STUDY WORKFLOW FLAGS DEBUG
═══════════════════════════════════════════════════════════

(index)                              Value
HAS_SEEN_PARTICIPANT_SETUP          'true'
HAS_SEEN_WELCOME                    'true'
TUTORIAL_COMPLETED                  'true'
TUTORIAL_IN_PROGRESS                null
HAS_SEEN_WELCOME_BACK               'true'  ⚠️ SESSION FLAG
BEGIN_ANALYSIS_CLICKED_THIS_SESSION 'true'  ⚠️ SESSION FLAG
PRE_SURVEY_COMPLETION_DATE          null
CURRENT_SESSION_START               null    ⚠️ SHOULD EXIST IF SESSION ACTIVE
TIMEOUT_SESSION_ID                  null    ⚠️ SHOULD EXIST IF SESSION ACTIVE
LAST_ACTIVITY_TIME                  '1764130140260'
WEEK_START_DATE                     '2025-11-23'
WEEKLY_SESSION_COUNT                '0'
TOTAL_SESSIONS_STARTED              '5'
TOTAL_SESSIONS_COMPLETED            '3'
TOTAL_SESSION_TIME                  '5112515'
TOTAL_REGIONS_IDENTIFIED            null
TOTAL_FEATURES_IDENTIFIED           null
PARTICIPANT_ID                      'Robert_Test_Volcano_Now_Participant'

🔍 DIAGNOSIS:
Session active? ❌ NO
Should see Welcome Back? ❌ NO (flags both true = STUCK STATE)
Pre-survey completed today? ❌ NO
Tutorial complete? ✅ YES
═══════════════════════════════════════════════════════════
```

## The Problem

**Corrupted State:**
- `HAS_SEEN_WELCOME_BACK` = true (session-level flag)
- `BEGIN_ANALYSIS_CLICKED_THIS_SESSION` = true (session-level flag)
- BUT `CURRENT_SESSION_START` = null (session not active)
- AND `TIMEOUT_SESSION_ID` = null (session not active)
- AND `PRE_SURVEY_COMPLETION_DATE` = null (pre-survey never completed)

**What this means:**
The session-level flags claim the user is mid-session, but there's no active session. The workflow gets confused and:
1. Doesn't show Welcome Back modal (thinks they already saw it)
2. Doesn't show Pre-Survey modal (no code path to open it)
3. Locks volcano selector (because BEGIN_ANALYSIS_CLICKED is true)
4. User is completely stuck

## Root Cause Analysis

### How We Got Here

**Theory:** Session timed out, but user had NOT completed pre-survey yet.

Looking at `session-management.js` `handleSessionTimeout()` function (lines 191-393):

```javascript
// Line 217: Check if pre-survey data exists
if (responses && responses.pre) {
    // ... submit data to Qualtrics ...
    
    // Line 355-362: Clear session flags
    try {
        localStorage.removeItem('study_has_seen_welcome_back');
        localStorage.removeItem('study_pre_survey_completion_date');
        localStorage.removeItem('study_begin_analysis_clicked_this_session');
        localStorage.removeItem('study_current_session_start');
        localStorage.removeItem('study_timeout_session_id');
        console.log('🧹 Cleared session flags after timeout');
    } catch (error) {
        console.warn('⚠️ Could not clear session flags:', error);
    }
} else {
    // Line 367: No pre-survey data
    console.warn('⚠️ No pre-survey data found for timeout submission');
    
    // 🔥 BUG: SESSION FLAGS ARE NOT CLEARED IN THIS BRANCH!
    // User gets stuck with stale flags on next visit
}
```

**The Bug:** Session flag clearing only happens inside the `if (responses && responses.pre)` block. If there's no pre-survey data when the session times out, the flags DON'T get cleared!

### Why Would There Be No Pre-Survey Data?

Possible scenarios:
1. User saw Welcome Back modal, clicked "Start Now"
2. Pre-Survey modal opened
3. User closed tab/browser before submitting pre-survey
4. Or: User let it time out before submitting pre-survey
5. Session timeout fired, found no `responses.pre`, didn't clear flags

## UI Symptoms

When in this corrupted state:

```javascript
// From console diagnostics:
console.log('Current volcano:', document.getElementById('volcano')?.value);
// → 'kilauea'

console.log('Volcano with data:', window.State?.volcanoWithData);
// → undefined

console.log('Fetch button disabled?', document.getElementById('startBtn')?.disabled);
// → false  (button is NOT disabled!)

console.log('Fetch button title:', document.getElementById('startBtn')?.title);
// → '' (no title)
```

**Fetch button is NOT disabled!** But user reported it wasn't clickable. Need to investigate further why - possibly a z-index/overlay issue or event handler problem.

**Volcano selector IS disabled** because of this check in `ui-controls.js` (lines 228-236):

```javascript
if (isStudyMode()) {
    const { hasBegunAnalysisThisSession } = await import('./study-workflow.js');
    if (hasBegunAnalysisThisSession()) {
        volcanoSelect.disabled = true;
        volcanoSelect.style.opacity = '0.5';
        volcanoSelect.style.cursor = 'not-allowed';
        console.log('🔒 Volcano selector disabled (Begin Analysis clicked this session)');
    }
}
```

## Potential Fixes (Currently Commented Out)

### Fix 1: Detection in study-workflow.js (lines 1043-1064)

Add safety check when returning visitor workflow runs:

```javascript
// 🛡️ SAFETY CHECK: Detect stale session flags
const sessionStart = localStorage.getItem(STORAGE_KEYS.CURRENT_SESSION_START);
const timeoutSessionId = localStorage.getItem(STORAGE_KEYS.TIMEOUT_SESSION_ID);
const hasBegunAnalysis = hasBegunAnalysisThisSession();

if (hasBegunAnalysis && (!sessionStart || !timeoutSessionId)) {
    console.warn('⚠️ STALE SESSION FLAGS DETECTED!');
    // Clear the corrupted session flags
    localStorage.removeItem(STORAGE_KEYS.HAS_SEEN_WELCOME_BACK);
    localStorage.removeItem(STORAGE_KEYS.BEGIN_ANALYSIS_CLICKED_THIS_SESSION);
    localStorage.removeItem(STORAGE_KEYS.PRE_SURVEY_COMPLETION_DATE);
    console.log('✅ Stale flags cleared - user will see Welcome Back modal');
}
```

**Pros:**
- Catches the problem at workflow startup
- Recovers gracefully by showing Welcome Back modal
- User can start fresh

**Cons:**
- Is this masking a deeper problem?
- What if there are legitimate cases where these flags are set without an active session?

### Fix 2: Prevention in session-management.js (lines 378-389)

Always clear session flags on timeout, even when no pre-survey data:

```javascript
} else {
    console.warn('⚠️ No pre-survey data found for timeout submission');
    
    // 🔥 CRITICAL: Still need to clear session flags even without pre-survey data!
    try {
        localStorage.removeItem('study_has_seen_welcome_back');
        localStorage.removeItem('study_pre_survey_completion_date');
        localStorage.removeItem('study_begin_analysis_clicked_this_session');
        localStorage.removeItem('study_current_session_start');
        localStorage.removeItem('study_timeout_session_id');
        console.log('🧹 Cleared session flags after timeout (no pre-survey case)');
    } catch (error) {
        console.warn('⚠️ Could not clear session flags:', error);
    }
}
```

**Pros:**
- Fixes the root cause
- Ensures proper cleanup regardless of session state
- Prevents this corrupted state from happening

**Cons:**
- Need to understand WHY there would be no pre-survey data in the first place
- Are we hiding a different bug?

## Open Questions

1. **Why was there no pre-survey data?** Did the user never complete it, or was there a different issue?

2. **Why couldn't the user click Fetch Data button?** Console showed `disabled: false`, so what was blocking it?

3. **Should we implement both fixes?** 
   - Fix 2 (prevention) stops the problem at source
   - Fix 1 (detection) provides safety net for users already in corrupted state

4. **Are there other places where session flags could get out of sync?**
   - Browser crash (no cleanup runs at all)
   - Tab close before session completes
   - Network errors during submission
   - JavaScript errors during cleanup

## Next Steps

Before implementing fixes:
1. Understand the full session lifecycle
2. Audit all places where session flags are set/cleared
3. Consider if we need a more robust session state machine
4. Test what happens in edge cases (crash, timeout, etc.)

## Related Code Locations

- `js/study-workflow.js` - Main workflow orchestration
  - Lines 94-113: STORAGE_KEYS definitions
  - Lines 766-803: Timeout check on page load
  - Lines 1043-1086: Returning visitor logic (where stuck state manifests)
  
- `js/session-management.js` - Timeout handling
  - Lines 191-393: `handleSessionTimeout()` function
  - Lines 355-365: Flag clearing (only if pre-survey exists)
  - Lines 366-390: No pre-survey case (BUG: no flag clearing)

- `js/ui-controls.js` - UI state management
  - Lines 228-236: Volcano selector disabled when BEGIN_ANALYSIS_CLICKED

## Status

**Current state:** Both fixes commented out, waiting for surgical analysis of proper solution.

**Risk:** Real participants could encounter this bug in production if they timeout before completing pre-survey.

