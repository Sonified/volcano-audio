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

        // Setup listener for data fetch completion to inject regions
        setupRegionInjectionListener();

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

        // 1. Set volcano dropdown
        const volcanoSelect = document.getElementById('volcano');
        if (volcanoSelect) {
            volcanoSelect.value = session.volcano;
            console.log(`✅ Set volcano to: ${session.volcano}`);
        }

        // 2. Load stations for this volcano (auto-selects default station)
        const { loadStations } = await import('./ui-controls.js');
        loadStations();

        // 3. Set duration dropdown
        const durationSelect = document.getElementById('duration');
        if (durationSelect) {
            durationSelect.value = session.duration.toString();
            console.log(`✅ Set duration to: ${session.duration} hours`);
        }

        // 4. Set highpass filter
        const highpassInput = document.getElementById('highpassFreq');
        if (highpassInput) {
            highpassInput.value = session.highpass_freq || '2';
            console.log(`✅ Set highpass to: ${session.highpass_freq} Hz`);
        }

        // 5. Set normalize checkbox
        const normalizeCheckbox = document.getElementById('enableNormalize');
        if (normalizeCheckbox) {
            normalizeCheckbox.checked = session.enable_normalize;
            console.log(`✅ Set normalize to: ${session.enable_normalize}`);
        }

        // 6. Clear any existing regions for this volcano to prevent stale data
        const { getCurrentRegions } = await import('./region-tracker.js');
        const currentRegions = getCurrentRegions();
        const regionsCleared = currentRegions.length;
        currentRegions.length = 0;
        if (regionsCleared > 0) {
            console.log(`🧹 Cleared ${regionsCleared} old regions for ${session.volcano}`);
        }

        // 7. Calculate expected data window for this session
        const fetchTime = new Date(session.fetch_timestamp);
        const fetchMinute = fetchTime.getUTCMinutes();
        const fetchSecond = fetchTime.getUTCSeconds();
        const periodStart = Math.floor(fetchMinute / 10) * 10;
        const secondsSincePeriodStart = (fetchMinute - periodStart) * 60 + fetchSecond;

        let expectedDataEnd;
        if (secondsSincePeriodStart >= 135) {
            expectedDataEnd = new Date(fetchTime.getTime());
            expectedDataEnd.setUTCMinutes(periodStart, 0, 0);
        } else {
            expectedDataEnd = new Date(fetchTime.getTime());
            expectedDataEnd.setUTCMinutes(periodStart - 10, 0, 0);
        }
        const expectedDataStart = new Date(expectedDataEnd.getTime() - session.duration * 3600 * 1000);

        // 8. Store regions AND expected data window for loading after data fetch
        window.pendingSessionRegions = session.regions;
        window.pendingSessionDataStart = expectedDataStart.toISOString();
        window.pendingSessionDataEnd = expectedDataEnd.toISOString();
        console.log(`📦 Stored ${session.region_count} regions for loading after fetch`);
        console.log(`⏰ Expected data window: ${expectedDataStart.toISOString()} to ${expectedDataEnd.toISOString()}`);

        // 9. Store fetch timestamp to override time calculation
        window.sessionFetchTimestamp = session.fetch_timestamp;
        console.log(`📅 Using session fetch timestamp: ${session.fetch_timestamp}`);

        // 9. Force enable and click fetch button (bypass volcano-data lock in study mode)
        const startBtn = document.getElementById('startBtn');
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.classList.remove('streaming');
            startBtn.title = '';
            console.log('🔓 Fetch button force-enabled for session load');
            console.log('🚀 Triggering data fetch...');
            startBtn.click();
        } else {
            console.error('❌ Fetch button not found');
        }

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
 * Setup listener to inject regions after data fetch completes
 */
function setupRegionInjectionListener() {
    // Poll for when data is loaded and we have pending regions to inject
    const checkInterval = setInterval(async () => {
        // Atomically grab and clear regions FIRST (race condition protection)
        const regionsToInject = window.pendingSessionRegions;
        const expectedDataStart = window.pendingSessionDataStart;
        const expectedDataEnd = window.pendingSessionDataEnd;
        if (!regionsToInject) return;

        window.pendingSessionRegions = null;
        window.pendingSessionDataStart = null;
        window.pendingSessionDataEnd = null;

        // Import State to check data times
        const State = await import('./audio-state.js');
        if (!State.dataStartTime || !State.dataEndTime) {
            // Restore regions if data not ready yet
            window.pendingSessionRegions = regionsToInject;
            window.pendingSessionDataStart = expectedDataStart;
            window.pendingSessionDataEnd = expectedDataEnd;
            return;
        }

        // Check if data window matches expected window for this session
        const actualDataStart = State.dataStartTime.toISOString();
        const actualDataEnd = State.dataEndTime.toISOString();
        if (actualDataStart !== expectedDataStart || actualDataEnd !== expectedDataEnd) {
            // Wrong data window - restore regions and wait for correct data
            window.pendingSessionRegions = regionsToInject;
            window.pendingSessionDataStart = expectedDataStart;
            window.pendingSessionDataEnd = expectedDataEnd;
            return;
        }

        // Import zoomState to check if initialized
        const { zoomState } = await import('./zoom-state.js');
        if (!zoomState.isInitialized()) {
            // Restore regions if zoom not ready yet
            window.pendingSessionRegions = regionsToInject;
            window.pendingSessionDataStart = expectedDataStart;
            window.pendingSessionDataEnd = expectedDataEnd;
            return;
        }

        // All conditions met - inject regions!
        console.log(`🎯 Injecting ${regionsToInject.length} regions from session data`);

        await injectSessionRegions(regionsToInject);
    }, 100); // Check every 100ms
}

/**
 * Inject regions from session data into the spectrogram
 */
async function injectSessionRegions(sessionRegions) {
    const audioState = await import('./audio-state.js');
    const { zoomState } = await import('./zoom-state.js');
    const { getCurrentRegions, getCurrentVolcano, updateCompleteButtonState, renderRegionsAfterCrossfade } = await import('./region-tracker.js');

    const volcano = getCurrentVolcano();
    if (!volcano) {
        console.error('❌ Cannot inject regions - no volcano selected');
        return;
    }

    const dataStartMs = audioState.dataStartTime.getTime();
    const dataEndMs = audioState.dataEndTime.getTime();

    // Get current regions array (reference to array in Map)
    const regions = getCurrentRegions();

    // Clear existing regions
    regions.length = 0;

    let regionId = 1;

    for (const sessionRegion of sessionRegions) {
        // Parse region timestamps
        const regionStartMs = new Date(sessionRegion.regionStartTime).getTime();
        const regionEndMs = new Date(sessionRegion.regionEndTime).getTime();

        // Skip regions completely outside data bounds
        if (regionEndMs < dataStartMs || regionStartMs > dataEndMs) {
            console.log(`⏭️ Skipping region ${sessionRegion.regionNumber} - outside data window`);
            continue;
        }

        // Clamp to data bounds
        const clampedStartMs = Math.max(regionStartMs, dataStartMs);
        const clampedEndMs = Math.min(regionEndMs, dataEndMs);

        // Double-check clamped values are valid
        if (clampedStartMs >= clampedEndMs) {
            console.warn(`⚠️ Skipping region ${sessionRegion.regionNumber} - invalid after clamping`);
            continue;
        }

        // Calculate sample indices
        const regionStartSeconds = (clampedStartMs - dataStartMs) / 1000;
        const regionEndSeconds = (clampedEndMs - dataStartMs) / 1000;
        const startSample = zoomState.timeToSample(regionStartSeconds);
        const endSample = zoomState.timeToSample(regionEndSeconds);

        // Convert features
        const features = [];
        let featureId = 1;

        for (const sessionFeature of sessionRegion.features || []) {
            // Parse feature timestamps
            const featureStartMs = new Date(sessionFeature.featureStartTime).getTime();
            const featureEndMs = new Date(sessionFeature.featureEndTime).getTime();

            // Clamp to region bounds
            const clampedFeatureStartMs = Math.max(featureStartMs, clampedStartMs);
            const clampedFeatureEndMs = Math.min(featureEndMs, clampedEndMs);

            // Calculate sample indices
            const featureStartSeconds = (clampedFeatureStartMs - dataStartMs) / 1000;
            const featureEndSeconds = (clampedFeatureEndMs - dataStartMs) / 1000;
            const featureStartSample = zoomState.timeToSample(featureStartSeconds);
            const featureEndSample = zoomState.timeToSample(featureEndSeconds);

            features.push({
                id: featureId++,
                startSample: featureStartSample,
                endSample: featureEndSample,
                startTime: sessionFeature.featureStartTime,
                endTime: sessionFeature.featureEndTime,
                lowFreq: parseFloat(sessionFeature.lowFreq),
                highFreq: parseFloat(sessionFeature.highFreq),
                type: sessionFeature.type || '',
                repetition: sessionFeature.repetition || '',
                notes: sessionFeature.notes || '',
                speedFactor: sessionFeature.speedFactor || 1,
                numberOfEvents: sessionFeature.numberOfEvents || 1
            });
        }

        // Create region object and add to array
        regions.push({
            id: regionId++,
            startSample: startSample,
            endSample: endSample,
            startTime: new Date(clampedStartMs).toISOString(),
            stopTime: new Date(clampedEndMs).toISOString(),
            features: features,
            expanded: false // Start collapsed
        });
    }

    console.log(`✅ Injected ${regions.length} regions with ${regions.reduce((sum, r) => sum + r.features.length, 0)} total features`);

    // Update button state
    updateCompleteButtonState();

    // Render regions (will be handled by crossfade completion normally)
    renderRegionsAfterCrossfade();

    console.log('🎨 Regions ready for rendering');
}

/**
 * Get currently selected session data
 */
export function getSelectedSession() {
    return selectedSession;
}
