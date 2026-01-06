# Captain's Log - December 16, 2025

## Performance Benchmarking: R2 Progressive Streaming vs IRIS Direct Fetch

### Executive Summary

Comprehensive TTFA (Time To First Audio) benchmarking confirms that **R2 CDN progressive streaming is 163.5x faster** than downloading 24 hours of seismic data directly from IRIS via Railway backend.

**Key Finding:** Users can start listening in **~400ms** with R2 progressive streaming versus **~66 seconds** waiting for IRIS to deliver 24 hours of data.

---

## Benchmark Methodology

### Test Configuration

**Test Script:** `tests/ttfa_r2_vs_railway.py`
**Test Date:** December 12, 2025 02:24 UTC
**Data Duration:** 24 hours of seismic data
**Stations Tested:** All 5 study stations (Kilauea, Mauna Loa, Great Sitkin, Shishaldin, Spurr)

### Two Approaches Compared

#### Approach 1: R2 CDN Progressive Streaming
**Architecture:**
```
Browser → cdn.now.audio → R2 Bucket → First 10m chunk
```

**Flow:**
1. Fetch metadata JSON from R2 (~50ms)
2. Fetch FIRST 10-minute chunk (compressed) from R2 (~150ms)
3. Decompress with zstd (~200ms)
4. **AUDIO PLAYS** ← TTFA measured here
5. Remaining 23h 50m loads in background while user listens

**Data Source:** Pre-cached data from daily collector runs

#### Approach 2: Railway → IRIS (Non-Progressive)
**Architecture:**
```
Browser → Railway Backend → IRIS FDSN → Process ALL 24h → Return ALL
```

**Flow:**
1. Request 24h of data from Railway
2. Railway fetches ALL 24h from IRIS FDSN web service
3. Railway processes all data (detrend, filter, normalize)
4. Railway returns complete 24h dataset
5. **AUDIO PLAYS** ← TTFA measured here

**Data Source:** Live fetch from IRIS every request

---

## Benchmark Results

### Individual Station Performance

| Station | Volcano | R2 TTFA | Railway TTFA | Speedup |
|---------|---------|---------|--------------|---------|
| HV.OBL | Kilauea | 427ms | 106,660ms | **249.6x** |
| HV.MOKD | Mauna Loa | 407ms | 89,350ms | **219.5x** |
| AV.GSTD | Great Sitkin | 354ms | 42,229ms | **119.2x** |
| AV.SSLS | Shishaldin | 414ms | 56,890ms | **137.4x** |
| AV.SPCP | Spurr | 433ms | 37,746ms | **87.2x** |
| **AVERAGE** | - | **407ms** | **66,575ms** | **163.5x** |

### Time Savings

- **Average time saved:** 66,168ms (66.2 seconds)
- **R2 average TTFA:** 407ms (0.4 seconds)
- **Railway average TTFA:** 66,575ms (66.6 seconds)

---

## Analysis

### Why R2 is 163x Faster

**1. Pre-Cached Data (Biggest Factor)**
- R2: Data already processed and stored on CDN
- IRIS: Must fetch from IRIS every single request
- **Impact:** Eliminates ~60+ seconds of IRIS fetch time

**2. Progressive Loading Strategy**
- R2: Only fetches first 10 minutes initially (~600KB compressed)
- IRIS: Must download ALL 24 hours before playing (~50MB+)
- **Impact:** 40x less data to download before playback starts

**3. CDN Edge Caching**
- R2: Cloudflare CDN with global edge network
- Railway: Single Oregon server → IRIS → back to user
- **Impact:** Lower latency, faster delivery

**4. Compression Efficiency**
- R2: zstd level 3 compression (70% compression ratio)
- Railway: May use different compression or uncompressed transfer
- **Impact:** Smaller payloads = faster transfer

### Performance Variance by Station

**Fastest (249x speedup - Kilauea HV.OBL):**
- Most popular station (likely cached at edge)
- Hawaii → West Coast → excellent connectivity
- IRIS took longest (106 seconds) for this station

**Slowest (87x speedup - Spurr AV.SPCP):**
- Less popular station (may not be edge-cached)
- Alaska station → potentially slower IRIS response
- IRIS was fastest (38 seconds) for this station

**Key Insight:** Even the "slowest" R2 result (433ms) is still **87x faster** than the fastest IRIS result (37 seconds).

---

## Real-World UX Impact

### User Experience with R2 Progressive Streaming
```
0.0s  - User clicks "Fetch Data"
0.4s  - Audio starts playing ← User hears volcano!
1.0s+ - Remaining 23h 50m loads silently in background
```

### User Experience with IRIS Direct Fetch
```
0.0s  - User clicks "Fetch Data"
...   - Loading spinner
...   - Still loading
...   - User checks Twitter
...   - Still loading
66.6s - Audio finally starts playing ← User already left!
```

### Why This Matters

**For AGU Presentations:**
- ✅ Sub-second response time = professional, polished demo
- ✅ No awkward waiting during live presentations
- ✅ Can demo multiple stations quickly

**For Study Participants:**
- ✅ Instant gratification = better engagement
- ✅ No confusion about whether app is working
- ✅ Professional-feeling experience = more trust

**For Viral Potential:**
- ✅ Fast load times = people actually use it
- ✅ Twitter demos look snappy and responsive
- ✅ "Wow factor" from instant audio playback

---

## Cost Efficiency

### R2 Progressive Streaming Costs

**At 1,000 requests/day (30k/month):**

| Component | Cost |
|-----------|------|
| R2 Storage (150 GB) | $1.50/month |
| R2 Class A Ops (30k) | $0.14/month |
| R2 Egress to CDN | **FREE** |
| CDN Bandwidth | **FREE** (Cloudflare) |
| Railway Collector | $5/month (runs daily) |
| **TOTAL** | **~$7/month** |

### IRIS Direct Fetch Costs

**At 1,000 requests/day (30k/month):**

| Component | Cost |
|-----------|------|
| Railway Compute | $21/month (always-on) |
| Railway Bandwidth | $200-400/month (30k × 50MB) |
| IRIS Rate Limits | Likely throttled/blocked |
| **TOTAL** | **$221-421/month** |

**Cost savings:** ~$214-414/month (30-60x cheaper)

---

## Technical Architecture Benefits

### R2 Progressive Streaming Architecture

**Benefits:**
1. ✅ **Decoupled collection from serving** - Collector runs once daily, serves millions
2. ✅ **Edge caching** - Data served from nearest Cloudflare POP
3. ✅ **Parallel downloads** - Browser can fetch multiple chunks simultaneously
4. ✅ **Graceful degradation** - Falls back to Railway if R2 unavailable
5. ✅ **Zero IRIS load** - Collector makes 1 request/day, not 30k requests/day

**Scalability:**
- ✅ 1 request or 1 million requests = same cost (within free tier)
- ✅ No IRIS rate limiting concerns
- ✅ No backend scaling concerns
- ✅ Global fast performance

### IRIS Direct Fetch Architecture

**Challenges:**
1. ❌ **Tightly coupled** - Every user request = IRIS request
2. ❌ **Single point of failure** - IRIS down = app down
3. ❌ **Rate limiting** - IRIS throttles at high volume
4. ❌ **Slow for users** - 60+ second wait times
5. ❌ **Sequential processing** - Can't parallelize

**Scalability:**
- ❌ Cost scales linearly with users
- ❌ IRIS will rate-limit at scale
- ❌ Backend becomes bottleneck
- ❌ Performance depends on IRIS health

---

## Files Referenced

- **Test Script:** `tests/ttfa_r2_vs_railway.py`
- **Results File:** `tests/benchmark_results/ttfa_r2_vs_railway.json`
- **R2 CDN Base:** `https://cdn.now.audio`
- **Railway Backend:** `https://volcano-audio-collector-production.up.railway.app/api/stream-audio`

---

## Conclusions

1. **R2 progressive streaming is 163.5x faster** than IRIS direct fetch for 24-hour seismic data
2. **Time to first audio averages 407ms** with R2 vs 66.6 seconds with IRIS
3. **Cost is 30-60x cheaper** at scale ($7/month vs $221-421/month)
4. **Architecture is more scalable** - decoupled, edge-cached, globally fast
5. **User experience is dramatically better** - instant audio vs minute-long waits

### Recommendation

**Continue with R2 progressive streaming architecture.** The performance, cost, and UX advantages are overwhelming. IRIS direct fetch should only be used as a fallback for stations/times not yet cached on R2.

---

## Future Optimizations

### Potential Improvements (Not Urgent)

1. **Pre-warm CDN cache** - Proactively fetch popular stations to edge
2. **Adaptive chunk sizing** - Use 5m chunks for even faster TTFA
3. **Service worker caching** - Cache chunks in browser for instant replay
4. **WebSocket live updates** - Stream newest data as it arrives from collector
5. **Predictive pre-loading** - Pre-fetch likely next stations based on usage patterns

---

**Status:** R2 progressive streaming is production-ready and battle-tested. Performance results validate architectural decisions. No changes needed before AGU presentation.

