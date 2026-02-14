# Volcano Audio Streaming System

A real-time web-based system for streaming and audifying seismic data from active volcanoes worldwide.

## Overview

This project provides a complete pipeline for converting seismic data into audio streams. It fetches real-time data from IRIS FDSN, processes and compresses it with multi-size Zstd chunks, stores it on Cloudflare R2, and streams it progressively to web browsers for immediate playback and visualization.

## 🎯 Quick Links

- **[🎵 Main Interface](index.html)** - AudioWorklet-based streaming player
- **[📝 TODO List](docs/TODO.md)** - Current development priorities
- **[📖 Captain's Logs](docs/captains_logs/)** - Daily progress notes and version history
- **[🛠️ Developer Guide](docs/DEV_GUIDE.md)** - Backend setup, R2 uploads, testing, debugging
- **[⚙️ Stations Config](backend/stations_config.json)** - Active/inactive station configuration

## Architecture

### Data Pipeline Flow

The system uses **two separate paths** depending on station activity:

#### Path 1: Active Stations (HV.OBL, HV.SBL, etc.)
```
Browser → cdn.now.audio/data (Direct CDN fetch)
```
- Browser fetches `.zst` chunks directly from Cloudflare R2 CDN
- Metadata JSON consulted to determine which chunks exist
- Realistic chunk fetch optimization: tries to grab first chunk immediately for instant playback
- No backend involved (fastest path)

#### Path 2: Inactive Stations (Mauna Loa, etc.)
```
Browser → Railway Backend → IRIS → Browser
```
- On-demand streaming via Railway `/api/stream-audio` endpoint
- Backend fetches from IRIS, processes, and streams to browser
- Used for stations not actively collected by scheduled collector

### Data Collection Pipeline (Backend)

1. **Scheduled Collection**: Railway collector runs every 10 minutes (:02, :12, :22, etc.)
2. **IRIS Fetch**: Downloads raw seismic data from IRIS FDSN web services
3. **Data Processing**: Detrend, deduplicate, gap-fill, calculate min/max for normalization
4. **Multi-Size Chunking**: Creates time-aligned chunks:
   - **10-minute chunks** - First 60 minutes (mandatory for instant playback)
   - **1-hour chunks** - After 60 minutes, at hour boundaries
   - **6-hour chunks** - At 6-hour boundaries (maximum efficiency)
5. **Zstd Compression**: Level 3 compression (~2.4-3.6:1 ratio, fast browser decompression)
6. **R2 Upload**: Chunks and metadata uploaded to Cloudflare R2 via `cdn.now.audio`
7. **Metadata Generation**: Per-day JSON files track all chunks with timestamps, sample counts, min/max

### Browser Playback System

1. **Station Check**: Browser determines if station is active (from `stations_config.json`)
2. **Metadata Fetch**: Downloads daily metadata JSON to know which chunks exist
3. **Realistic Chunk Fetch**: Tries to grab first 10m chunk immediately (with fallback +10, +20, +30 minutes)
4. **Progressive Streaming**: Fetches remaining chunks in batches while first chunk plays
5. **Web Worker Decompression**: Zstd decompression off main thread
6. **AudioWorklet Playback**: `SeismicProcessor` handles real-time audio in separate high-priority thread
7. **Progressive Waveform**: Waveform Worker builds visualization left-to-right as chunks arrive

### Supported Volcanoes
- **Kīlauea** (Hawaii) - HV network
- **Mauna Loa** (Hawaii) - HV network
- **Great Sitkin** (Alaska) - AV network
- **Shishaldin** (Alaska) - AV network
- **Mount Spurr** (Alaska) - AV network

### Station Selection Criteria
- **Radius**: 13 miles (21 km) from volcano coordinates
- **Component**: Z-component only (vertical seismometers)
- **Status**: Active channels only (no end_time)
- **Data Source**: Parsed from `volcano_station_availability.json`

## Features

- ✅ **Dual-Path Architecture**: Direct CDN for active stations, Railway backend for inactive
- ✅ **Realistic Chunk Optimization**: Instant playback start by fetching first chunk immediately
- ✅ **Multi-Size Chunking**: 10m/1h/6h chunks with smart boundary-aligned selection
- ✅ **AudioWorklet Playback**: Glitch-free, low-latency audio on separate high-priority thread
- ✅ **Progressive Waveform**: Left-to-right visualization builds as chunks arrive
- ✅ **Fast Decompression**: Zstd level 3 (~10-30 MB/s) in Web Worker
- ✅ **Global Edge Distribution**: Cloudflare R2 CDN (`cdn.now.audio`)
- ✅ **Scheduled Collection**: Automated 10-minute collection cycle for active stations
- ✅ **Automatic Metadata**: Per-day JSON with min/max for consistent normalization
- ✅ **Sample-Accurate Playback**: Zero clicks/pops between chunks

## Backend Deployment (Railway)

The data collector runs on **Railway** and auto-deploys from `main` branch via GitHub.

**Key files:**
- `backend/Dockerfile` — Defines the container (takes priority over nixpacks.toml)
- `backend/requirements.txt` — Python dependencies (production only)
- `backend/runtime.txt` — Pins Python to 3.11.11
- `backend/collector_loop.py` — The collector service (~3500 lines)

**Critical dependency note:** `setuptools` must be pinned to **69.5.1** (or any version <70). Setuptools 80+ removed `pkg_resources`, which ObsPy requires at runtime. The Dockerfile installs it explicitly before other dependencies. See the `DO NOT upgrade past 69.x` comment in the Dockerfile.

**Python version:** Pinned to **3.11.11**. Do not use 3.12+ features in `collector_loop.py` (e.g., PEP 701 multi-line f-strings require 3.12+).

**Build caching:** Railway's Nixpacks builder caches aggressively. If you need to bust the cache (e.g., after changing system dependencies), the Dockerfile is the reliable escape hatch — Railway uses it when present.

**Operational endpoints:**
- `GET /health` — Health check (status, uptime, version)
- `GET /status` — Detailed collector metrics
- `GET /trigger` — Manually trigger a collection cycle
- `GET /gaps/24h` — Detect missing data chunks (also: `4h`, `1h`, `complete`)
- `POST /backfill` — Backfill missing chunks from IRIS (use `{"use_latest_report": true}` or manual windows)
- `POST /purge-cache` — Purge Cloudflare CDN cache (requires `CLOUDFLARE_ZONE_ID` and `CLOUDFLARE_API_TOKEN` env vars on Railway)

## Local Development Setup

### Quick Start - Local Collector

For testing the scheduled collector and on-demand streaming:

```bash
cd backend
# Start local collector (includes /api/stream-audio endpoint)
./start_local_collector.sh
```

This runs the collector on `http://localhost:5005` with:
- Scheduled 10-minute collection cycles
- `/api/stream-audio` endpoint for on-demand inactive station streaming
- `/health`, `/status`, `/trigger` monitoring endpoints

**To stop:**
```bash
pkill -f collector_loop.py
```

### Frontend Development

Simply open `index.html` in a browser:
- **Active stations**: Fetches directly from `cdn.now.audio` (no local setup needed)
- **Inactive stations**: Configure to use local collector at `http://localhost:5005`

### Testing

1. **Active Stations** (HV.OBL, etc.): Just open `index.html` - works immediately
2. **Inactive Stations** (Mauna Loa, etc.): Start local collector, then open `index.html`
3. **Collection Pipeline**: Run collector with `./start_local_collector.sh`, check logs

**Need more help?** See **[Developer Guide](docs/DEV_GUIDE.md)** for detailed setup, R2 configuration, and troubleshooting.

## Usage

### Web Streaming Interface

**Note**: The current codebase is the **production/study branch** designed for research participants. The workflow is:

1. **Onboarding** (first visit): Participant setup → Welcome → Pre-survey → Tutorial
2. **Begin Analysis**: User selects volcano, clicks "Begin Analysis" to start feature identification
3. **Exploration**: 24-hour seismic window displayed, user identifies and marks regions of interest
4. **Session end**: Activity survey → AWE-SF (weekly) → Post-survey → Submission

Each session uses a fixed 24-hour display window. Returning participants skip onboarding and go directly to exploration.

### API Endpoints

#### Railway Collector Service

**Production**: `https://volcano-audio-collector-production.up.railway.app`

##### Primary Endpoints
- `GET /health` - Health check (returns status, version, uptime)
- `GET /status` - Detailed collector status with metrics (optional `?timezone=` param)
- `GET /stations` - List active stations from `stations_config.json`
- `GET /trigger` - Manually trigger collection cycle immediately
- `POST /api/stream-audio` - On-demand audio streaming for inactive stations
  - **Body**: `{network, station, location, channel, starttime, duration, highpass_hz, normalize, send_raw}`
  - **Used by**: Browser for inactive stations (Mauna Loa, etc.)
- `GET /gaps/<mode>` - Gap detection (`smart`, `simple`, or `all`)
- `POST /backfill` - Backfill missing data for specified time ranges

##### CDN Direct Access (Active Stations)
- `https://cdn.now.audio/data/{YYYY}/{MM}/{DD}/{NETWORK}/{VOLCANO}/{STATION}/{LOCATION}/{CHANNEL}/{TYPE}/{FILENAME}.bin.zst`
- **Types**: `10m`, `1h`, `6h`
- **Metadata**: `https://cdn.now.audio/data/{YYYY}/{MM}/{DD}/{NETWORK}/{VOLCANO}/{STATION}/{LOCATION}/{CHANNEL}/{NETWORK}_{STATION}_{LOCATION}_{CHANNEL}_{YYYY-MM-DD}.json`

## Data Management

### Station Availability Database
The system uses `data/reference/volcano_station_availability.json` which contains:
- Volcano coordinates (lat/lon)
- All available seismic and infrasound stations within 50km
- Channel metadata (network, station, location, channel codes)
- Sample rates, instrument details, active date ranges
- Distance from volcano summit

### Updating Station Data
The station availability database (`data/reference/volcano_station_availability.json`) is maintained manually. The collector service uses `backend/stations_config.json` for active station configuration.

### Participant Data Pipeline

Survey responses and session data flow through a dual-submission system:

```
Browser (localStorage)
    │
    ├─► Qualtrics API (primary)
    │   └─ Survey responses submitted via qualtrics-api.js
    │
    └─► R2 Backup (secondary)
        └─ Full session data uploaded via data-uploader.js
```

**Storage during session:**
- Survey responses: `localStorage['participant_response_{participantId}']`
- Session state: `localStorage['participant_session_state']`
- Managed by: `Qualtrics/participant-response-manager.js`

**On session complete or timeout:**
1. `qualtrics-api.js` submits survey responses to Qualtrics API
2. `data-uploader.js` uploads backup to R2: `volcano-audio-anonymized-data/participants/{id}/`
   - `user-status/status.json` - Current state snapshot (overwritten each upload)
   - `submissions/{id}_Complete_{timestamp}.json` - Permanent record (append-only)

**Backend endpoint:**
- `POST /api/upload-user-data` - Receives participant data for R2 storage

## Performance Metrics

### Compression Efficiency (1-hour window, 100 Hz data)
| Format | Size | Compression Time (Render) | Decompression Time (Browser) | Ratio |
|--------|------|---------------------------|----------------------------|-------|
| Raw int32 | 1.44 MB | - | - | 1.0:1 |
| **Zstd-3** | **~400-600 KB** | **~30-50ms** | **~20-40ms** | **~2.4-3.6:1** |

### Multi-Size Chunking Strategy
- **10-minute chunks**: First 60 minutes (mandatory for instant playback, 6 chunks)
- **1-hour chunks**: After 60 minutes at hour boundaries (balanced efficiency)
- **6-hour chunks**: At 6-hour boundaries (maximum compression, fewest requests)
- **Smart Selection**: Browser picks largest available chunk at each time boundary
- **Example (6 hours)**: Six 10m chunks + five 1h chunks = 11 total requests

### Streaming Performance
- **Time to First Audio**: Target <100ms (depends on R2 cache status)
- **Browser decompression**: 10-30 MB/s with fzstd library
- **Network bandwidth**: ~400-600 KB/hour per station (compressed)
- **IndexedDB storage**: Uncompressed int32 for instant replay

## Project Structure

```
volcano-audio/
├── index.html               # 🎵 Main audio streaming interface (AudioWorklet-based)
├── backend/
│   ├── collector_loop.py    # 🔄 Scheduled collector + HTTP API (Railway)
│   ├── audio_stream.py      # 🎧 On-demand streaming endpoint (/api/stream-audio)
│   ├── stations_config.json # ⚙️ Active station configuration
│   ├── start_local_collector.sh  # 🚀 Start local collector for testing
│   └── requirements.txt     # Python dependencies (ObsPy, boto3, zstandard)
├── data/reference/
│   ├── volcano_station_availability.json  # Complete station database
│   └── monitored_volcanoes.json          # Volcano list from USGS
├── docs/
│   ├── TODO.md              # 📝 Current development priorities
│   ├── captains_logs/       # 📖 Daily progress logs
│   └── DEV_GUIDE.md         # 🛠️ Developer setup guide
├── waveform-worker.js       # 🎨 Web Worker for progressive waveform rendering
└── archive/                  # 📦 Archived old code, docs, and prototypes
```

## Technical Details

### Data Storage Format
- **R2 Storage**: Zstd-compressed `.zst` files (level 3)
- **Data type**: float32 (normalized to [-1.0, 1.0])
- **Metadata**: Per-day JSON files with min/max, sample rate, timestamps, all available chunks
- **Hierarchy**: `/data/{YYYY}/{MM}/{DD}/{NETWORK}/{VOLCANO}/{STATION}/{LOCATION}/{CHANNEL}/{TYPE}/`
  - `{TYPE}` = `10m`, `1h`, or `6h`

### Audio Processing Pipeline
- **Input**: Seismic data sampled at 20-100 Hz (typically 100 Hz for HV network)
- **Processing**: Merge traces, deduplicate, gap-fill with interpolation
- **Normalization**: Global min/max sent to browser for consistent playback levels
- **Speedup**: 50-400x (configurable in browser)
- **Output sample rate**: Original × speedup (e.g., 100 Hz × 200 = 20 kHz)

### Compression Strategy
- **Format**: Zstandard (Zstd) level 3
- **Rationale**: 
  - Fast browser decompression (10-30 MB/s with fzstd.js)
  - Better compression than gzip (~2.4-3.6:1 ratio)
  - Decompression happens in Web Worker (non-blocking)
- **Multi-size chunks**: 10m/1h/6h aligned to time boundaries for efficient caching

### Browser Technologies
- **AudioWorklet API**: `SeismicProcessor` class runs audio on separate high-priority thread
- **Web Workers**: Separate threads for Zstd decompression and waveform rendering
- **Zstd Decompression**: fzstd.js library (~10-30 MB/s)
- **Fetch API**: Direct CDN chunk fetching from `cdn.now.audio`
- **Canvas API**: Real-time progressive waveform visualization

### Cloudflare Infrastructure
- **R2 Storage**: Object storage with zero egress fees
- **CDN Distribution**: `cdn.now.audio` for global edge delivery
- **Metadata + Chunks**: Per-day JSON manifests + Zstd-compressed binary chunks

## Frontend Architecture

The browser-side code (~35,000 lines across 40+ modules) uses a **3-tier architecture** separating concerns across threads:

### Three-Tier Thread Model

```
┌─────────────────────────────────────────────────────────────────┐
│ TIER 1: Main Thread (js/*.js)                                   │
│ - State management, UI events, coordination                     │
│ - Imports all modules, orchestrates data flow                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌───────────────────────┐     ┌─────────────────────────────────┐
│ TIER 2: Web Workers   │     │ TIER 3: AudioWorklet            │
│ (workers/*.js)        │     │ (workers/audio-worklet.js)      │
│ - Decompression       │     │ - Real-time audio synthesis     │
│ - Waveform min/max    │     │ - High-priority thread          │
│ - FFT/spectrogram     │     │ - Variable speed, filters       │
└───────────────────────┘     └─────────────────────────────────┘
```

### Key Frontend Modules

```
js/
├── core/                        # 🔥 LOADS FIRST - survives app crashes (see below)
│   ├── error-system.js          # Catches errors, shows "overheated" state
│   ├── flame-engine.js          # Pink noise + oscilloscope flames
│   └── oscilloscope-renderer.js # Pure canvas rendering (core copy)
│
├── main.js                      # Entry point, initialization hub
├── audio-state.js               # Central state (100+ getters/setters, single source of truth)
├── audio-player.js              # Playback control (play/pause, speed, seeking, loop)
├── data-fetcher.js              # Progressive chunk batching algorithm
│
├── ui-controls.js               # Button handlers, modals, filters
├── modal-manager.js             # Modal lifecycle (open/close/queue)
├── modal-templates.js           # HTML templates for all modals
├── keyboard-shortcuts.js        # Keybindings (spacebar, C/V/B frequency scale, etc.)
│
├── region-tracker.js            # User-defined time/frequency regions
├── spectrogram-complete-renderer.js  # Infinite-canvas spectrogram
├── spectrogram-feature-boxes.js # Visual boxes on spectrogram for marked features
├── waveform-renderer.js         # Canvas waveform visualization
├── waveform-x-axis-renderer.js  # Time axis labels below waveform
├── waveform-buttons-renderer.js # Clickable region buttons on waveform
├── oscilloscope-renderer.js     # Real-time audio feedback (app copy)
├── zoom-state.js                # Waveform zoom level management
│
├── study-workflow.js            # Session flow, surveys, visit rules
├── session-management.js        # Inactivity timeout (10min warn, 20min hard)
├── tutorial.js                  # Interactive guided experience
├── tutorial-sequence.js         # Step definitions for tutorial
├── tutorial-state.js            # Tutorial progress flags
│
├── qualtrics-api.js             # Survey integration, participant ID
├── master-modes.js              # 8 app modes (personal, dev, production, study variants)
└── station-config.js            # Active/inactive station definitions

workers/
├── audio-worklet.js         # SeismicProcessor class (54KB) - real-time playback
├── audio-processor-worker.js # Zstd decompression + normalization
├── waveform-worker.js       # Min/max calculation, DC offset removal
└── spectrogram-worker.js    # FFT computation
```

### Two-Tier Loading (Beta-Proof Architecture)

The app uses a **core-first loading strategy** to gracefully handle crashes during beta:

```
index.html
├── CORE (loads first) ← js/core/ - ALWAYS works
│   ├── error-system.js     # Catches errors, reports to backend
│   ├── flame-engine.js     # Pink noise generator
│   └── oscilloscope-renderer.js  # Flame visualization
│
└── APP (loads second) ← js/main.js - might break during beta
```

**If the app layer crashes:**
- Core catches the error via `window.onerror`
- Shows "Interface overheated" message (fits volcano theme)
- Oscilloscope flames keep blazing (core is immortal)
- Error automatically reported to backend with participant ID
- UI buttons disabled to prevent further issues

**Test overheat mode:** `window.enterOverheatMode()` in console.

See [js/core/README.md](js/core/README.md) for full documentation.

### Data Flow: Streaming to Playback

```
CDN (cdn.now.audio)
    │ Zstd chunks
    ▼
data-fetcher.js (Main Thread)
    │ Compressed buffer (transferable)
    ▼
audio-processor-worker.js (Web Worker)
    │ Decompresses, normalizes → Float32Array
    ▼
Main Thread accumulates completeSamplesArray
    │
    ├──────────────────────────────┐
    ▼                              ▼
waveform-worker.js          AudioWorklet (SeismicProcessor)
    │                              │
    ▼                              ▼
Waveform Canvas             Audio Output (speakers)
(left-to-right progressive)
```

### State Management Pattern

All state lives in `audio-state.js` with explicit setters:

```javascript
// Centralized state - modules import what they need
import { getPlaybackState, setPlaybackState, getCompleteSamplesArray } from './audio-state.js';

// Key state categories:
// - Audio nodes: audioContext, workletNode, gainNode
// - Playback: playbackState ('STOPPED'|'PLAYING'|'PAUSED'), currentPlaybackRate
// - Data: completeSamplesArray (Float32Array), currentMetadata
// - Regions: user-marked time/frequency regions with features
// - Visualization: frequencyScale ('linear'|'sqrt'|'logarithmic'), cached canvases
```

### AudioWorklet: SeismicProcessor

The `SeismicProcessor` class in `workers/audio-worklet.js` handles real-time audio:

- **Circular buffer** with dynamic expansion (5-minute capacity)
- **Variable speed** (0.1x - 15x) with linear interpolation
- **Sample-accurate seeking** with crossfade transitions
- **Loop mode** with automatic 5ms fade-in/out
- **High-pass filter** (9 Hz IIR) removes DC drift
- **Anti-aliasing** filter for slow playback
- **Position tracking** (30ms updates to main thread)

### Region System

Users mark regions of interest stored per-volcano:

```javascript
regions[volcanoName] = [{
  startTime: ISO string,
  stopTime: ISO string,
  regionName: "tremor event",
  features: [{
    featureName: "harmonic tremor",
    lowFreq: 5, highFreq: 12,
    type: "continuous",
    repetition: "periodic"
  }]
}]
// Persisted to localStorage
```

### App Modes

`master-modes.js` defines 8 modes affecting UI/behavior:

| Mode | Purpose |
|------|---------|
| `PERSONAL` | Skip tutorial, full access |
| `DEV` | Development environment |
| `PRODUCTION` | Live study interface |
| `STUDY_CLEAN` | Reset all flags (first-time test) |
| `STUDY_W2_S1` | Week 2, Session 1 variant |
| `TUTORIAL_END` | Jump to final tutorial step |

### Canvas Architecture

Multiple layered canvases per visualization:

- **Waveform**: 4 canvases (main, axis, x-axis, region buttons)
- **Spectrogram**: 2+ canvases (infinite pre-rendered canvas, viewport, overlays)
- **Oscilloscope**: 1 canvas (real-time feedback)

All use `devicePixelRatio` for crisp rendering.

### Code Conventions

```javascript
// Debug flags (set to true for verbose logging)
const DEBUG_CHUNKS = false;    // data-fetcher.js
const DEBUG_WAVEFORM = false;  // waveform-worker.js
const DEBUG_WORKLET = false;   // audio-worklet.js

// Emoji-prefixed logs for quick scanning:
// 🔥 FIX/Critical   ⚠️ Warning   ✅ Success
// 📡 Data fetch     ▶️ Playback  🎨 Visualization

// Memory leak prevention pattern (throughout codebase):
// 🔥 FIX: Clear old reference before assigning
completeSamplesArray = null;
completeSamplesArray = newValue;

// 🔥 FIX: Cancel RAF loops on cleanup
cancelAllRAFLoops();

// 🔥 FIX: Check document connected before DOM access
if (!document.body?.isConnected) return;
```

### Study/Tutorial System

`study-workflow.js` orchestrates the full research study with visit-dependent rules:

**First Visit (W1S1):**
```
Participant Setup → Welcome → Pre-Survey → Tutorial → Experience
    → Activity Level → AWE-SF → Post-Survey → End
```

**Session 2 of any week (W1S2, W2S2, W3S2):**
```
Pre-Survey → Experience → Activity Level → Post-Survey → End
(No AWE-SF survey)
```

**Session 1 of new week (W2S1, W3S1):**
```
Pre-Survey → Experience → Activity Level → AWE-SF → Post-Survey → End
(AWE-SF returns for first session of each week)
```

**Key design principles:**
- Session data in `sessionStorage` for durability across reloads
- Qualtrics integration for survey submission
- Tutorial uses waiting flags (`waitingForSelection`, `waitingForRegionCreation`, etc.)
- **Test modes only set FLAGS** - no special-case logic. Fix the real code, not test mode branches

### localStorage Flags System

The app uses localStorage flags to track user progress and session state. Flags are defined in `STORAGE_KEYS` in [study-workflow.js](js/study-workflow.js).

#### Lifetime Categories

**PERSISTENT (survive forever until manually cleared):**
| Flag | Purpose |
|------|---------|
| `study_has_seen_participant_setup` | User completed initial setup (once ever) |
| `study_has_seen_welcome` | User saw first-time welcome modal |
| `study_tutorial_completed` | User finished the tutorial |
| `study_weekly_session_count` | Sessions completed this week (1 or 2) |
| `study_week_start_date` | When current week started (for weekly reset) |
| `study_total_sessions_started` | Cumulative sessions started (all time) |
| `study_total_sessions_completed` | Cumulative sessions completed (all time) |
| `study_total_session_time` | Total time spent in sessions (ms) |
| `study_session_history` | JSON array of all session records |
| `study_total_regions_identified` | Cumulative regions marked (all time) |
| `study_total_features_identified` | Cumulative features marked (all time) |
| `study_session_completion_tracker` | Tracks which specific sessions are complete |
| `participantId` | User's participant ID |
| `selectedVolcano` | Last selected volcano |
| `selectedMode` | App mode (personal, study, dev, etc.) |
| `frequencyScale` | Spectrogram scale preference (linear/sqrt/log) |

**SESSION-SCOPED (cleared on session end or timeout):**
| Flag | Purpose |
|------|---------|
| `study_begin_analysis_clicked_this_session` | User clicked "Begin Analysis" (locks volcano) |
| `study_has_seen_welcome_back` | User saw "Welcome Back" modal this session |
| `study_current_session_start` | ISO timestamp when session started |
| `study_timeout_session_id` | Ties timeout to specific participant |
| `study_last_activity_time` | Last user activity (for timeout calculation) |
| `study_tutorial_in_progress` | Tutorial currently running |

**PER-VOLCANO (keyed by volcano name):**
| Flag | Purpose |
|------|---------|
| `volcano_audio_regions_{volcano}` | Saved regions with features (24h expiry filter) |

#### Session Timeout Behavior

After 20 minutes of inactivity:
1. `handleSessionTimeout()` in [session-management.js](js/session-management.js) fires
2. Partial data (regions, features, pre-survey) is submitted
3. Session-scoped flags are cleared
4. Volcano selection is re-enabled
5. User starts fresh on next visit

Regions older than 24 hours are automatically filtered out when loading from localStorage.

#### Flag Inspection

To inspect current flag state, run in browser console:
```javascript
// Quick view of study flags
Object.keys(localStorage).filter(k => k.startsWith('study_')).forEach(k => console.log(k, localStorage.getItem(k)));

// Or use the built-in debug panel (if in dev/study mode)
// Click the 🔧 button in the UI
```

### Browser Requirements

- **AudioWorklet**: Chrome 66+, Safari 14.1+, Firefox 76+
- **Web Workers**: All modern browsers
- **Transferable Objects**: Zero-copy data transfer between threads