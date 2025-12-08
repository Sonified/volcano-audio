/**
 * CNS (Connectedness to Nature Scale) Submission Handler
 *
 * Handles submission of CNS survey responses to R2 storage.
 * This is a post-intervention survey administered at the end of the study.
 *
 * Storage key: study_cns_post_completed
 * R2 folder: volcano-audio-anonymized-data/participants/{id}/CNS_POST/
 */

import { getParticipantId } from './qualtrics-api.js';

// Storage key for tracking CNS completion
export const CNS_STORAGE_KEY = 'study_cns_post_completed';

/**
 * Check if participant has already completed the CNS post survey
 */
export function hasCnsPostCompleted() {
    return localStorage.getItem(CNS_STORAGE_KEY) === 'true';
}

/**
 * Mark CNS post survey as completed
 */
export function markCnsPostCompleted() {
    localStorage.setItem(CNS_STORAGE_KEY, 'true');
    console.log('✅ CNS post survey marked as completed');
}

/**
 * Collect CNS responses from the modal
 * @returns {Object} CNS responses with item numbers as keys
 */
export function collectCnsResponses() {
    const responses = {};

    // Collect all 14 CNS items
    for (let i = 1; i <= 14; i++) {
        const selected = document.querySelector(`input[name="cns${i}"]:checked`);
        responses[`cns${i}`] = selected ? parseInt(selected.value) : null;
    }

    return responses;
}

/**
 * Validate that all CNS items are answered
 * @returns {boolean} True if all 14 items are answered
 */
export function validateCnsResponses() {
    for (let i = 1; i <= 14; i++) {
        const selected = document.querySelector(`input[name="cns${i}"]:checked`);
        if (!selected) {
            return false;
        }
    }
    return true;
}

/**
 * Submit CNS responses to R2 storage
 * @returns {Promise<boolean>} True if submission successful
 */
export async function submitCnsToR2() {
    const participantId = getParticipantId();

    if (!participantId) {
        console.error('❌ Cannot submit CNS: No participant ID');
        return false;
    }

    if (!validateCnsResponses()) {
        console.error('❌ Cannot submit CNS: Incomplete responses');
        return false;
    }

    const responses = collectCnsResponses();
    const timestamp = new Date().toISOString();

    // Build the submission payload
    const payload = {
        participantId: participantId,
        surveyType: 'CNS_POST',
        submissionTimestamp: timestamp,
        responses: responses,
        // Include reverse-scored items for reference
        reverseScoreItems: [4, 12, 14],
        // Calculate raw total (before reverse scoring)
        rawTotal: Object.values(responses).reduce((sum, val) => sum + (val || 0), 0),
        metadata: {
            userAgent: navigator.userAgent,
            screenWidth: window.innerWidth,
            screenHeight: window.innerHeight
        }
    };

    console.log('📤 Submitting CNS to R2:', payload);

    try {
        // Use the data uploader to send to R2
        const { uploadToR2 } = await import('./data-uploader.js');

        // Create filename with participant ID and timestamp
        const filename = `${participantId}_CNS_POST_${timestamp.replace(/[:.]/g, '-')}.json`;
        const key = `volcano-audio-anonymized-data/CNS_POST/${filename}`;

        const success = await uploadToR2(key, JSON.stringify(payload, null, 2));

        if (success) {
            console.log('✅ CNS submission successful');
            markCnsPostCompleted();
            return true;
        } else {
            console.error('❌ CNS submission failed');
            return false;
        }
    } catch (error) {
        console.error('❌ CNS submission error:', error);
        return false;
    }
}

/**
 * Clear CNS completion status (for testing)
 */
export function clearCnsStatus() {
    localStorage.removeItem(CNS_STORAGE_KEY);
    console.log('🔄 CNS completion status cleared');
}

/**
 * Setup CNS modal submit handler
 * Call this after modals are initialized
 */
export function setupCnsSubmitHandler() {
    const cnsModal = document.getElementById('cnsModal');
    if (!cnsModal) {
        console.warn('⚠️ CNS modal not found');
        return;
    }

    const submitBtn = cnsModal.querySelector('.modal-submit');
    if (!submitBtn) {
        console.warn('⚠️ CNS submit button not found');
        return;
    }

    // Replace the submit button click handler
    submitBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();

        if (!validateCnsResponses()) {
            alert('Please answer all questions before submitting.');
            return;
        }

        // Disable button during submission
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';

        const success = await submitCnsToR2();

        if (success) {
            submitBtn.textContent = '✓ Submitted!';
            // Close the modal after a brief delay and chain to next in workflow
            setTimeout(async () => {
                const { closeCnsModal } = await import('./ui-controls.js');
                await closeCnsModal();
            }, 1000);
        } else {
            submitBtn.disabled = false;
            submitBtn.textContent = '✓ Submit';
            alert('Submission failed. Please try again.');
        }
    });

    console.log('✅ CNS submit handler configured');
}
