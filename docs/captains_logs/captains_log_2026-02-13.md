# Captain's Log - 2026-02-13

## Chrome Rendering Audit & Fixes

Audited all CSS/JS rendering issues causing flickering on Chrome (similar to spaceweather.now.audio pass):

- **Drop-shadow stacks**: Collapsed 2-3 layer stacks to single shadows across ~10 keyframe animations in `styles.css`
- **`mix-blend-mode: multiply`**: Removed from volcano watermark in `modal-templates.js`
- **`backdrop-filter: blur()`**: Removed from oscilloscope panel and frost texture overlay in `index.html`
- **Canvas `shadowBlur`**: Replaced with multi-stroke glow pattern on both playheads in `waveform-renderer.js`
- **`filter: brightness()` animations**: Swapped to `opacity` in `pulseBright` and `pulseVibrant` keyframes
- **`transform: translateZ(0)`**: Removed from static `.panel` element
- **`will-change`**: Added `opacity` to `.region-card`

Note: `flame-engine.js` intentionally left complex — it's beautiful for a reason.

## Railway Collector Crash & Recovery

Discovered the collector service had been down, causing data gaps. Root cause investigation:

1. **Python 3.13 removed `setuptools` from stdlib** — Railway auto-upgraded Python, breaking ObsPy's `import pkg_resources`
2. **Pinned Python to 3.11.11** via `runtime.txt` — but this broke two multi-line f-strings (PEP 701, Python 3.12+ only)
3. **Fixed f-strings** in `collector_loop.py` (lines ~3012 and ~3428) by extracting `json.dumps` to variables
4. **Railway build cache refused to invalidate** — tried bumping setuptools version, adding `nixpacks.toml` with `--clear`, nothing worked
5. **Created `Dockerfile`** as escape hatch from Nixpacks caching
6. **setuptools 80+ removed `pkg_resources`** — even fresh installs of setuptools 82.0.0 didn't have it!
7. **Fix: Pinned `setuptools==69.5.1`** (last version with `pkg_resources`) — this finally worked

Six-layer dependency onion: Python version → f-string syntax → build cache → setuptools version → pkg_resources removal.

### Key Learnings
- `setuptools==69.5.1` is the last version that includes `pkg_resources` — DO NOT upgrade past 69.x
- `python:3.11.11-slim` does NOT include setuptools — must install explicitly in Dockerfile
- Railway's Dockerfile takes priority over `nixpacks.toml` — use it to escape build cache issues
- PEP 701 multi-line f-strings only work in Python 3.12+ — don't use them in `collector_loop.py`

## Backfill & Cache Purge

- **Backfill bug fix**: Station matching in `/backfill` endpoint was broken — location field (`"--"` vs `""`) wasn't normalized on both sides of comparison
- **Backfill results**: Kilauea 4/4 success, Mauna Loa 4/4 success, Spurr 0/3 (IRIS had no data — seismometer gaps)
- **Cloudflare caching 404s**: After backfill, CDN was still serving cached 404 responses
- **Added `/purge-cache` endpoint** to collector — calls Cloudflare API to purge all cached responses
- Requires `CLOUDFLARE_ZONE_ID` and `CLOUDFLARE_API_TOKEN` env vars on Railway (now configured)

## Cleanup

- Terminated old Render deployment (was being billed $25/mo for nothing)
- Destroyed unused "volcano audio streaming" Railway service (duplicate of collector's built-in `/api/stream-audio`)
- Updated README with Backend Deployment section and all operational endpoints
- Deleted old `purge-cache-nowaudio` Cloudflare API token, created fresh one

## Files Changed
- `styles.css` — Chrome compositing fixes
- `js/waveform-renderer.js` — Multi-stroke glow replaces shadowBlur
- `js/modal-templates.js` — Removed mix-blend-mode
- `index.html` — Removed backdrop-filter
- `backend/Dockerfile` — Created (python:3.11.11-slim + setuptools 69.5.1)
- `backend/requirements.txt` — Pinned setuptools==69.5.1
- `backend/runtime.txt` — Created (python-3.11.11)
- `backend/nixpacks.toml` — Created (attempted cache bust)
- `backend/collector_loop.py` — Fixed f-strings, backfill station matching, added /purge-cache
- `README.md` — Added Backend Deployment section with operational endpoints
