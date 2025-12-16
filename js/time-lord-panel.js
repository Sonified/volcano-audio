/**
 * Time Lord Panel - Search and browse volcano data by date/time
 *
 * Provides UI for:
 * - Selecting start and end date/time
 * - Searching for data in that time range
 * - Managing recent searches
 */

const RECENT_SEARCHES_KEY = 'timelord_recent_searches';
const MAX_RECENT_SEARCHES = 10;

let recentSearches = [];

/**
 * Initialize the time lord panel
 */
export async function initTimeLordPanel() {
    console.log('⏰ Initializing Time Lord panel');

    // Load recent searches from localStorage
    loadRecentSearches();

    // Populate recent searches dropdown
    populateRecentSearchesDropdown();

    // Setup event listeners
    setupEventListeners();

    // Set default times (last 24 hours)
    setDefaultTimes();
}

/**
 * Load recent searches from localStorage
 */
function loadRecentSearches() {
    try {
        const stored = localStorage.getItem(RECENT_SEARCHES_KEY);
        if (stored) {
            recentSearches = JSON.parse(stored);
            console.log(`⏰ Loaded ${recentSearches.length} recent searches`);
        }
    } catch (error) {
        console.error('❌ Error loading recent searches:', error);
        recentSearches = [];
    }
}

/**
 * Save recent searches to localStorage
 */
function saveRecentSearches() {
    try {
        localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recentSearches));
        console.log(`⏰ Saved ${recentSearches.length} recent searches`);
    } catch (error) {
        console.error('❌ Error saving recent searches:', error);
    }
}

/**
 * Add a search to recent searches (moves to top if already exists)
 */
function addRecentSearch(startDate, endDate, volcano, station) {
    // Create search object
    const search = {
        startDate,
        endDate,
        volcano,
        station,
        timestamp: new Date().toISOString(),
        label: formatSearchLabel(startDate, endDate, volcano, station)
    };

    // Remove if already exists (we'll re-add at top)
    recentSearches = recentSearches.filter(s =>
        s.startDate !== startDate || s.endDate !== endDate || s.volcano !== volcano || s.station !== station
    );

    // Add to top
    recentSearches.unshift(search);

    // Trim to max
    if (recentSearches.length > MAX_RECENT_SEARCHES) {
        recentSearches = recentSearches.slice(0, MAX_RECENT_SEARCHES);
    }

    // Save and update dropdown
    saveRecentSearches();
    populateRecentSearchesDropdown();
}

/**
 * Format a search label for display
 */
function formatSearchLabel(startDate, endDate, volcano, station) {
    const start = new Date(startDate);
    const end = new Date(endDate);

    const formatDate = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    };

    // Get volcano name from dropdown
    const volcanoSelect = document.getElementById('volcano');
    const volcanoName = volcanoSelect ?
        volcanoSelect.querySelector(`option[value="${volcano}"]`)?.textContent || volcano :
        volcano;

    return `${volcanoName} - ${station} - ${formatDate(start)} → ${formatDate(end)}`;
}

/**
 * Populate the recent searches dropdown
 */
function populateRecentSearchesDropdown() {
    const dropdown = document.getElementById('timeLordRecentSearches');
    if (!dropdown) return;

    // Clear existing options
    dropdown.innerHTML = '';

    if (recentSearches.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No recent searches';
        dropdown.appendChild(option);
        return;
    }

    // Add placeholder option
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Select a recent search...';
    dropdown.appendChild(placeholder);

    // Add recent searches
    recentSearches.forEach((search, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = search.label;
        option.dataset.searchData = JSON.stringify(search);
        dropdown.appendChild(option);
    });
}

/**
 * Set default times (December 6th, 2025 full day in UTC)
 * 00:00 UTC to 00:00 UTC (midnight to midnight UTC)
 */
function setDefaultTimes() {
    // December 6, 2025 at 00:00 UTC
    const startDate = new Date(Date.UTC(2025, 11, 6, 0, 0)); // Month is 0-indexed, so 11 = December
    // December 7, 2025 at 00:00 UTC
    const endDate = new Date(Date.UTC(2025, 11, 7, 0, 0));

    // Format for datetime-local input (YYYY-MM-DDTHH:MM)
    // Display in user's local timezone
    const formatForInput = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    };

    const startInput = document.getElementById('timeLordStartDate');
    const endInput = document.getElementById('timeLordEndDate');

    if (startInput) startInput.value = formatForInput(startDate);
    if (endInput) endInput.value = formatForInput(endDate);
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    const recentSearchesDropdown = document.getElementById('timeLordRecentSearches');
    const startDateInput = document.getElementById('timeLordStartDate');
    const endDateInput = document.getElementById('timeLordEndDate');

    // Recent search selection
    if (recentSearchesDropdown) {
        recentSearchesDropdown.addEventListener('change', handleRecentSearchSelection);
    }

    // Re-enable Fetch Data button when times change
    if (startDateInput) {
        startDateInput.addEventListener('change', () => {
            const startBtn = document.getElementById('startBtn');
            if (startBtn && startBtn.disabled) {
                startBtn.disabled = false;
                console.log('🔓 Fetch button re-enabled after time change');
            }
        });
    }

    if (endDateInput) {
        endDateInput.addEventListener('change', () => {
            const startBtn = document.getElementById('startBtn');
            if (startBtn && startBtn.disabled) {
                startBtn.disabled = false;
                console.log('🔓 Fetch button re-enabled after time change');
            }
        });
    }
}

/**
 * Get the current time lord date range (for integration with fetch button)
 * Returns null if dates are invalid
 */
export function getTimeLordDateRange() {
    const startInput = document.getElementById('timeLordStartDate');
    const endInput = document.getElementById('timeLordEndDate');

    if (!startInput || !endInput) {
        return null;
    }

    const startDate = startInput.value;
    const endDate = endInput.value;

    if (!startDate || !endDate) {
        return null;
    }

    // Validate date range
    const start = new Date(startDate);
    const end = new Date(endDate);

    if (start >= end) {
        console.warn('⚠️ Time Lord: Start date must be before end date');
        return null;
    }

    return {
        startDate,
        endDate,
        startTime: start,
        endTime: end
    };
}

/**
 * Record a search in recent searches (called after successful fetch)
 */
export function recordTimeLordSearch(startDate, endDate, volcano, station) {
    console.log('⏰ Recording Time Lord search:', { startDate, endDate, volcano, station });
    addRecentSearch(startDate, endDate, volcano, station);
}

/**
 * Handle recent search selection
 */
async function handleRecentSearchSelection(event) {
    const selectedOption = event.target.selectedOptions[0];

    if (!selectedOption || !selectedOption.dataset.searchData) {
        return;
    }

    const search = JSON.parse(selectedOption.dataset.searchData);

    console.log('⏰ Selected recent search:', search.label);

    // 1. Update volcano dropdown
    const volcanoSelect = document.getElementById('volcano');
    if (volcanoSelect && search.volcano) {
        volcanoSelect.value = search.volcano;
        console.log(`✅ Set volcano to: ${search.volcano}`);

        // Trigger change event to load stations
        volcanoSelect.dispatchEvent(new Event('change'));
    }

    // 2. Wait for stations to load, then set station
    if (search.station) {
        // Give stations time to load
        await new Promise(resolve => setTimeout(resolve, 100));

        const stationSelect = document.getElementById('station');
        if (stationSelect) {
            stationSelect.value = search.station;
            console.log(`✅ Set station to: ${search.station}`);
        }
    }

    // 3. Update date inputs
    const startInput = document.getElementById('timeLordStartDate');
    const endInput = document.getElementById('timeLordEndDate');

    if (startInput) startInput.value = search.startDate;
    if (endInput) endInput.value = search.endDate;
    console.log(`✅ Set dates: ${search.startDate} → ${search.endDate}`);

    // 4. Move this search to the top
    addRecentSearch(search.startDate, search.endDate, search.volcano, search.station);

    // 5. Reset dropdown to placeholder
    event.target.selectedIndex = 0;

    // 6. Trigger fetch automatically
    await new Promise(resolve => setTimeout(resolve, 100));
    const startBtn = document.getElementById('startBtn');
    if (startBtn && !startBtn.disabled) {
        console.log('🚀 Auto-triggering data fetch for selected search');
        startBtn.click();
    } else {
        console.warn('⚠️ Fetch button not available for auto-trigger');
    }
}
