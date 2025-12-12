#!/usr/bin/env python3
"""
TTFA Comparison: R2 CDN (Progressive) vs Railway → IRIS

Measures Time To First Audio (TTFA) - when audio starts playing.

Real-world comparison for 24 HOURS of seismic data:

1. R2 CDN Progressive:
   - 24h of data is PRE-STORED on R2 (not locally cached)
   - Progressive loading: fetch metadata → fetch FIRST 10m chunk → decompress
   - TTFA = time until first chunk is playable (~600ms)
   - Remaining 23h 50m loads in background while user listens
   - This is how the production app works

2. Railway → IRIS (non-progressive):
   - Request 24h of data to Railway backend
   - Railway fetches ALL 24h from IRIS FDSN web service
   - Railway processes and returns the full 24h
   - TTFA = time until ALL data arrives (user waits for everything)

This demonstrates the massive UX advantage of progressive loading with pre-cached data.
All 5 study stations tested with averaged results.
"""

import requests
import time
import zstandard as zstd
import numpy as np
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

# URLs
R2_CDN_BASE = "https://cdn.now.audio"
RAILWAY_URL = "https://volcano-audio-collector-production.up.railway.app/api/stream-audio"

# All 5 study stations
STATIONS = [
    {"network": "HV", "station": "OBL", "location": "--", "channel": "HHZ", "volcano": "kilauea", "sample_rate": 100},
    {"network": "HV", "station": "MOKD", "location": "--", "channel": "HHZ", "volcano": "maunaloa", "sample_rate": 100},
    {"network": "AV", "station": "GSTD", "location": "--", "channel": "BHZ", "volcano": "greatsitkin", "sample_rate": 50},
    {"network": "AV", "station": "SSLS", "location": "--", "channel": "BHZ", "volcano": "shishaldin", "sample_rate": 50},
    {"network": "AV", "station": "SPCP", "location": "--", "channel": "BHZ", "volcano": "spurr", "sample_rate": 50},
]

OUTPUT_DIR = Path(__file__).parent / "benchmark_results"


def test_r2_cdn_ttfa(station, test_date):
    """
    Test TTFA via R2 CDN progressive loading.

    Steps:
    1. Fetch metadata JSON (tells us about available chunks)
    2. Fetch first 10-minute chunk (compressed)
    3. Decompress → ready to play

    Returns TTFA in milliseconds.
    """
    net = station["network"]
    sta = station["station"]
    loc = station["location"]
    cha = station["channel"]
    volcano = station["volcano"]

    year = test_date.year
    month = f"{test_date.month:02d}"
    day = f"{test_date.day:02d}"
    date_str = test_date.strftime("%Y-%m-%d")
    date_path = f"data/{year}/{month}/{day}"

    # Build metadata URL
    metadata_url = f"{R2_CDN_BASE}/{date_path}/{net}/{volcano}/{sta}/{loc}/{cha}/{net}_{sta}_{loc}_{cha}_{date_str}.json"

    t_start = time.time()

    # Step 1: Fetch metadata
    try:
        resp = requests.get(metadata_url, timeout=10)
        if resp.status_code != 200:
            return None, f"Metadata HTTP {resp.status_code}"
        metadata = resp.json()
        t_metadata = (time.time() - t_start) * 1000
    except Exception as e:
        return None, f"Metadata error: {e}"

    # Step 2: Get first 10m chunk
    chunks_10m = metadata.get("chunks", {}).get("10m", [])
    if not chunks_10m:
        return None, "No 10m chunks"

    first_chunk = chunks_10m[0]
    start_time = first_chunk.get("start", "00:00:00")
    end_time = first_chunk.get("end", "00:10:00")

    # Build chunk filename: {net}_{sta}_{loc}_{cha}_10m_{date}-{start}_to_{date}-{end}.bin.zst
    start_fmt = start_time.replace(":", "-")
    end_fmt = end_time.replace(":", "-")
    chunk_filename = f"{net}_{sta}_{loc}_{cha}_10m_{date_str}-{start_fmt}_to_{date_str}-{end_fmt}.bin.zst"

    chunk_url = f"{R2_CDN_BASE}/{date_path}/{net}/{volcano}/{sta}/{loc}/{cha}/10m/{chunk_filename}"

    # Step 3: Fetch first chunk
    try:
        resp = requests.get(chunk_url, timeout=30)
        if resp.status_code != 200:
            return None, f"Chunk HTTP {resp.status_code}"
        t_download = (time.time() - t_start) * 1000
        compressed_data = resp.content
    except Exception as e:
        return None, f"Chunk error: {e}"

    # Step 4: Decompress
    try:
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed_data)
        samples = np.frombuffer(decompressed, dtype=np.int32)
        t_total = (time.time() - t_start) * 1000
    except Exception as e:
        return None, f"Decompress error: {e}"

    return {
        "ttfa_ms": t_total,
        "metadata_ms": t_metadata,
        "download_ms": t_download - t_metadata,
        "decompress_ms": t_total - t_download,
        "chunk_kb": len(compressed_data) / 1024,
        "samples": len(samples),
        "duration_sec": len(samples) / station["sample_rate"]
    }, None


def test_railway_ttfa(station, test_date, duration_hours=24):
    """
    Test TTFA via Railway → IRIS path for 24 HOURS of data.

    Railway fetches ALL 24h from IRIS, processes on server, returns all at once.
    TTFA = time until ALL data arrives (user must wait for everything).

    This is the non-progressive path - no audio until full download completes.
    """
    net = station["network"]
    sta = station["station"]
    loc = station["location"]
    cha = station["channel"]

    # Start of test date
    start_time = datetime.combine(test_date, datetime.min.time())

    request_body = {
        "network": net,
        "station": sta,
        "location": loc,
        "channel": cha,
        "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "duration": duration_hours * 3600,  # seconds (24h)
        "highpass_hz": 0.045,
        "normalize": False,
        "send_raw": False
    }

    t_start = time.time()

    try:
        resp = requests.post(
            RAILWAY_URL,
            json=request_body,
            timeout=300,  # 5 min timeout for 24h data from IRIS
            headers={'Content-Type': 'application/json'}
        )
        t_response = (time.time() - t_start) * 1000

        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"

        # Check compression
        compression = resp.headers.get('X-Compression', 'none')
        data = resp.content

        # Decompress if needed
        if compression == 'zstd':
            try:
                dctx = zstd.ZstdDecompressor()
                data = dctx.decompress(data)
            except:
                return None, "zstd decompress failed"

        # Parse response format: [metadata_len (4 bytes)][metadata_json][float32_samples]
        metadata_length = int.from_bytes(data[:4], 'little')
        samples_data = data[4 + metadata_length:]
        samples = np.frombuffer(samples_data, dtype=np.float32)

        t_total = (time.time() - t_start) * 1000

        return {
            "ttfa_ms": t_total,
            "response_ms": t_response,
            "response_kb": len(resp.content) / 1024,
            "samples": len(samples),
            "duration_sec": len(samples) / station["sample_rate"]
        }, None

    except requests.exceptions.Timeout:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)


def run_comparison():
    """Run TTFA comparison for all 5 stations."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 70)
    print("TTFA COMPARISON: R2 CDN (Progressive) vs Railway → IRIS")
    print("=" * 70)
    print(f"\nTimestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"R2 CDN: {R2_CDN_BASE}")
    print(f"Railway: {RAILWAY_URL}")

    # Use yesterday for R2 (pre-cached), 3 days ago for Railway (IRIS availability)
    r2_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    railway_date = (datetime.now(timezone.utc) - timedelta(days=3)).date()

    print(f"\nR2 test date: {r2_date}")
    print(f"Railway test date: {railway_date}")

    results = []

    for station in STATIONS:
        station_name = f"{station['network']}.{station['station']}"
        volcano = station['volcano']

        print(f"\n{'-'*50}")
        print(f"Testing: {station_name} ({volcano})")
        print(f"{'-'*50}")

        # Test R2 CDN
        print("  R2 CDN (progressive)...", end=" ", flush=True)
        r2_result, r2_error = test_r2_cdn_ttfa(station, r2_date)
        if r2_error:
            print(f"FAILED: {r2_error}")
            r2_ttfa = None
        else:
            print(f"{r2_result['ttfa_ms']:.0f}ms")
            r2_ttfa = r2_result['ttfa_ms']

        # Test Railway
        print("  Railway → IRIS...", end=" ", flush=True)
        railway_result, railway_error = test_railway_ttfa(station, railway_date)
        if railway_error:
            print(f"FAILED: {railway_error}")
            railway_ttfa = None
        else:
            print(f"{railway_result['ttfa_ms']:.0f}ms")
            railway_ttfa = railway_result['ttfa_ms']

        # Calculate speedup
        speedup = None
        if r2_ttfa and railway_ttfa:
            speedup = railway_ttfa / r2_ttfa

        results.append({
            "station": station_name,
            "volcano": volcano,
            "r2_ttfa_ms": r2_ttfa,
            "railway_ttfa_ms": railway_ttfa,
            "speedup": speedup
        })

        time.sleep(0.5)  # Be nice to servers

    # Summary table
    print("\n" + "=" * 70)
    print("RESULTS: Time To First Audio (when audio starts playing)")
    print("=" * 70)
    print("\nR2 CDN: Fetch first 10m chunk from PRE-STORED 24h → decompress → AUDIO PLAYS (rest loads in background)")
    print("Railway: Request 24h → Railway fetches ALL 24h from IRIS → process → AUDIO PLAYS (must wait for everything)")

    print(f"\n{'Station':<18} {'Volcano':<14} {'R2 CDN':<12} {'Railway':<12} {'Speedup':<10}")
    print("-" * 70)

    valid_results = []
    for r in results:
        r2_str = f"{r['r2_ttfa_ms']:.0f}ms" if r['r2_ttfa_ms'] else "FAILED"
        railway_str = f"{r['railway_ttfa_ms']:.0f}ms" if r['railway_ttfa_ms'] else "FAILED"
        speedup_str = f"{r['speedup']:.1f}x" if r['speedup'] else "-"

        print(f"{r['station']:<18} {r['volcano']:<14} {r2_str:<12} {railway_str:<12} {speedup_str:<10}")

        if r['speedup']:
            valid_results.append(r)

    # Averages
    if valid_results:
        avg_r2 = sum(r['r2_ttfa_ms'] for r in valid_results) / len(valid_results)
        avg_railway = sum(r['railway_ttfa_ms'] for r in valid_results) / len(valid_results)
        avg_speedup = avg_railway / avg_r2

        print("-" * 70)
        print(f"{'AVERAGE':<18} {'':<14} {avg_r2:<12.0f} {avg_railway:<12.0f} {avg_speedup:.1f}x")

        print(f"\n✨ R2 CDN progressive loading is {avg_speedup:.1f}x faster than Railway → IRIS")
        print(f"   R2 CDN: {avg_r2:.0f}ms average TTFA")
        print(f"   Railway: {avg_railway:.0f}ms average TTFA")
        print(f"   Time saved: {avg_railway - avg_r2:.0f}ms per station")

    # Save results
    output_file = OUTPUT_DIR / "ttfa_r2_vs_railway.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "avg_r2_ttfa_ms": avg_r2 if valid_results else None,
            "avg_railway_ttfa_ms": avg_railway if valid_results else None,
            "avg_speedup": avg_speedup if valid_results else None
        }, f, indent=2)

    print(f"\n📊 Results saved to: {output_file}")

    return results


if __name__ == "__main__":
    run_comparison()
