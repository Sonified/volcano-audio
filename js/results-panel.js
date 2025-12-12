/**
 * Results Panel - Load and display participant session data
 *
 * Loads participant_sessions.json and provides UI for:
 * - Selecting participant
 * - Selecting session
 * - Loading session data (regions, features, fetch parameters)
 */

let participantData = null;
let selectedSession = null;

/**
 * Initialize the results panel
 */
export async function initResultsPanel() {
    try {
        // Load participant session data
        const response = await fetch('final_analysis/participant_sessions.json');
        if (!response.ok) {
            throw new Error(`Failed to load participant data: ${response.status}`);
        }

        participantData = await response.json();
        console.log('📊 Loaded participant session data:', {
            participants: participantData.participants.length,
            expert: participantData.expert ? 1 : 0,
            total_sessions: participantData.metadata.total_sessions
        });

        // Populate participant dropdown
        populateParticipantDropdown();

        // Setup event listeners
        setupEventListeners();

    } catch (error) {
        console.error('❌ Error loading participant data:', error);
        alert('Failed to load participant data. Check console for details.');
    }
}

/**
 * Populate the participant dropdown with P1-P6 + Expert
 */
function populateParticipantDropdown() {
    const participantSelect = document.getElementById('participantSelect');
    if (!participantSelect) return;

    // Clear existing options (except placeholder)
    participantSelect.innerHTML = '<option value="">Select participant...</option>';

    // Add participants section
    const participantsGroup = document.createElement('optgroup');
    participantsGroup.label = 'Participants';

    participantData.participants.forEach(p => {
        const option = document.createElement('option');
        option.value = p.value; // participant ID
        option.textContent = `${p.label} (${p.sessions.length} sessions)`;
        option.dataset.participantData = JSON.stringify(p);
        participantsGroup.appendChild(option);
    });

    participantSelect.appendChild(participantsGroup);

    // Add expert section if exists
    if (participantData.expert) {
        const expertGroup = document.createElement('optgroup');
        expertGroup.label = 'Expert';

        const option = document.createElement('option');
        option.value = participantData.expert.value;
        option.textContent = `${participantData.expert.label} (${participantData.expert.sessions.length} sessions)`;
        option.dataset.participantData = JSON.stringify(participantData.expert);
        expertGroup.appendChild(option);

        participantSelect.appendChild(expertGroup);
    }
}

/**
 * Populate session dropdown when participant is selected
 */
function populateSessionDropdown(participant) {
    const sessionSelect = document.getElementById('sessionSelect');
    if (!sessionSelect) return;

    // Clear existing options
    sessionSelect.innerHTML = '<option value="">Select session...</option>';

    // Add sessions
    participant.sessions.forEach((session, index) => {
        const option = document.createElement('option');
        option.value = index; // Use array index
        option.textContent = session.label;
        option.dataset.sessionData = JSON.stringify(session);
        sessionSelect.appendChild(option);
    });

    // Enable session dropdown
    sessionSelect.disabled = false;
}

/**
 * Setup event listeners for dropdowns and load button
 */
function setupEventListeners() {
    const participantSelect = document.getElementById('participantSelect');
    const sessionSelect = document.getElementById('sessionSelect');
    const loadSessionBtn = document.getElementById('loadSessionBtn');

    // Participant selection changed
    if (participantSelect) {
        participantSelect.addEventListener('change', (e) => {
            const selectedOption = e.target.selectedOptions[0];

            if (selectedOption && selectedOption.dataset.participantData) {
                const participant = JSON.parse(selectedOption.dataset.participantData);
                populateSessionDropdown(participant);

                // Reset session selection
                sessionSelect.selectedIndex = 0;
                loadSessionBtn.disabled = true;
                hideSessionInfo();
            } else {
                // No participant selected - reset
                sessionSelect.innerHTML = '<option value="">Select session...</option>';
                sessionSelect.disabled = true;
                loadSessionBtn.disabled = true;
                hideSessionInfo();
            }
        });
    }

    // Session selection changed
    if (sessionSelect) {
        sessionSelect.addEventListener('change', (e) => {
            const selectedOption = e.target.selectedOptions[0];

            if (selectedOption && selectedOption.dataset.sessionData) {
                // Enable load button
                loadSessionBtn.disabled = false;
            } else {
                loadSessionBtn.disabled = true;
                hideSessionInfo();
            }
        });
    }

    // Load session button clicked
    if (loadSessionBtn) {
        loadSessionBtn.addEventListener('click', async () => {
            const sessionSelect = document.getElementById('sessionSelect');
            const selectedOption = sessionSelect.selectedOptions[0];

            if (selectedOption && selectedOption.dataset.sessionData) {
                const session = JSON.parse(selectedOption.dataset.sessionData);
                await loadSession(session);
            }
        });
    }
}

/**
 * Load and display session data
 */
async function loadSession(session) {
    console.log('📊 Loading session:', session);

    try {
        selectedSession = session;

        // Display session info
        displaySessionInfo(session);

        // TODO: Load the actual session data into the UI
        // This will involve:
        // 1. Setting volcano, station, duration from session data
        // 2. Fetching the seismic data from R2
        // 3. Loading regions and features onto the spectrogram

        // For now, just show the info
        alert(`Session loaded!\n\nVolcano: ${session.volcano}\nDate: ${session.date}\nRegions: ${session.region_count}\nFeatures: ${session.feature_count}\n\nNext step: Wire up to fetch seismic data and display regions.`);

    } catch (error) {
        console.error('❌ Error loading session:', error);
        alert('Failed to load session. Check console for details.');
    }
}

/**
 * Display session information
 */
function displaySessionInfo(session) {
    const sessionInfo = document.getElementById('sessionInfo');
    if (!sessionInfo) return;

    document.getElementById('infoVolcano').textContent = session.volcano || '-';
    document.getElementById('infoDate').textContent = session.date || '-';
    document.getElementById('infoRegions').textContent = session.region_count || 0;
    document.getElementById('infoFeatures').textContent = session.feature_count || 0;
    document.getElementById('infoDuration').textContent = session.duration || '-';

    sessionInfo.style.display = 'block';
}

/**
 * Hide session information
 */
function hideSessionInfo() {
    const sessionInfo = document.getElementById('sessionInfo');
    if (sessionInfo) {
        sessionInfo.style.display = 'none';
    }
}

/**
 * Get currently selected session data
 */
export function getSelectedSession() {
    return selectedSession;
}
