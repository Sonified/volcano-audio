# Captain's Log - December 8, 2025

## v2.73 - CNS (Connectedness to Nature Scale) Production Integration

### What Changed
Integrated the CNS post-study survey into the production workflow. This 14-item survey measures participants' connection to nature and is administered once during the study.

### Workflow
```
Returning Visit:
Welcome Back Modal
    ↓
    [CNS not completed?]
    ├── Yes → CNS Modal → Pre-Survey → Experience
    └── No  → Pre-Survey → Experience
```

### Files Modified
- `js/ui-controls.js` - Added `openCnsModal()`, `closeCnsModal()`, workflow routing, submit handler
- `js/main.js` - Removed redundant `setupCnsSubmitHandler()` call (now in ui-controls.js)
- `js/modal-manager.js` - Added `cnsModal` to `closeAllModals` list
- `js/cns-submission.js` - Updated to use `closeCnsModal()` for workflow chaining
- `dashboards/user_metadata_config.html` - Added CNS flag to admin panel
- `dashboards/modal_viewer.html` - Added CNS button for testing
- `styles.css` - CNS modal styling (hidden X, left-aligned title)

### Data Storage
- CNS responses stored in R2: `volcano-audio-anonymized-data/CNS_POST/{participantId}_CNS_POST_{timestamp}.json`
- Completion tracked via localStorage flag: `study_cns_post_completed`
- Completely separate from main Qualtrics submission flow

### Payload Structure
```json
{
  "participantId": "...",
  "surveyType": "CNS_POST",
  "submissionTimestamp": "2025-12-08T20:17:09.980Z",
  "responses": { "cns1": 4, "cns2": 4, ... "cns14": 4 },
  "reverseScoreItems": [4, 12, 14],
  "rawTotal": 56,
  "metadata": { "userAgent": "...", "screenWidth": 1438, "screenHeight": 1170 }
}
```

### Welcome Back Modal Dynamic Content
- If CNS not completed: Shows 🌿 emoji with message about completing "Connectedness to Nature" survey
- If CNS completed: Shows 🌋 emoji with default welcome back text

### Error Handling
- If R2 submission fails: Button re-enables, user sees alert, modal stays open for retry
- CNS flag only set on successful submission
- User cannot skip - must complete CNS before proceeding to pre-survey
