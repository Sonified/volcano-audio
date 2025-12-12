#!/usr/bin/env python3
"""
Benchmark: Time to First Audio - Traditional vs Progressive Loading

Compares two approaches for 24 hours of Kilauea seismic data:

1. TRADITIONAL: Download all 24h → process all → first audio ready
2. PROGRESSIVE: Download first 1h chunk → process → first audio ready
                (remaining data loads in background)

This demonstrates the UX advantage of progressive loading - users can start
listening immediately while the rest of the data loads.

Station: HV.OBL.--. HHZ (Kilauea, 100 Hz)
"""

import requests
import time
import numpy as np
from scipy import signal
from scipy.io import wavfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import io

# Configuration - Mauna Loa station
NETWORK = "HV"
STATION = "MOKD"
LOCATION = "--"
CHANNEL = "HHZ"
SAMPLE_RATE = 100  # Hz

# IRIS FDSN Web Service
IRIS_URL = "https://service.iris.edu/fdsnws/dataselect/1/query"

# Output paths
OUTPUT_DIR = Path(__file__).parent / "benchmark_results"
RESULTS_FILE = OUTPUT_DIR / "time_to_first_audio_results.jsonl"


def fetch_from_iris(start_time, end_time, description=""):
    """Fetch miniSEED data from IRIS FDSN web service."""
    params = {
        "net": NETWORK,
        "sta": STATION,
        "loc": LOCATION,
        "cha": CHANNEL,
        "start": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "end": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "format": "miniseed"
    }

    print(f"   Fetching {description}...")
    print(f"   URL: {IRIS_URL}")
    print(f"   Time range: {params['start']} to {params['end']}")

    t_start = time.time()
    response = requests.get(IRIS_URL, params=params)
    t_download = time.time() - t_start

    if response.status_code != 200:
        raise Exception(f"IRIS returned {response.status_code}: {response.text[:200]}")

    size_mb = len(response.content) / (1024 * 1024)
    print(f"   ✓ Downloaded {size_mb:.2f} MB in {t_download:.2f}s ({size_mb/t_download:.2f} MB/s)")

    return response.content, t_download


def parse_miniseed(mseed_bytes):
    """Parse miniSEED to numpy array using obspy."""
    from obspy import read

    t_start = time.time()

    # Write to temp file (obspy needs file-like object or path)
    temp_path = OUTPUT_DIR / "temp_mseed.mseed"
    with open(temp_path, 'wb') as f:
        f.write(mseed_bytes)

    st = read(str(temp_path))

    # Merge traces and handle gaps
    st.merge(method=1, fill_value=0)

    data = st[0].data.astype(np.float64)
    actual_rate = st[0].stats.sampling_rate

    t_parse = time.time() - t_start

    # Clean up
    temp_path.unlink()

    return data, actual_rate, t_parse


def process_for_audio(data, sample_rate):
    """
    Apply audification processing pipeline:
    1. Detrend (remove DC)
    2. Taper edges
    3. High-pass filter (remove very low frequencies)
    4. Low-pass filter (anti-aliasing)
    5. Normalize

    This matches the processing in our production pipeline.
    """
    t_start = time.time()

    # 1. Detrend
    data = data - np.mean(data)

    # 2. Taper (5% Tukey window)
    taper = signal.windows.tukey(len(data), alpha=0.05)
    data = data * taper

    # 3. High-pass filter at 0.045 Hz (→ 20 Hz in audio domain at 441x speedup)
    hp_freq = 0.045
    sos_hp = signal.butter(2, hp_freq, btype='high', fs=sample_rate, output='sos')
    data = signal.sosfilt(sos_hp, data)

    # 4. Low-pass filter at 47.6 Hz (→ 21 kHz in audio domain at 441x speedup)
    lp_freq = 47.6
    sos_lp = signal.butter(4, lp_freq, btype='low', fs=sample_rate, output='sos')
    data = signal.sosfilt(sos_lp, data)

    # 5. Normalize to [-1, 1]
    max_abs = np.max(np.abs(data))
    if max_abs > 0:
        data = data / max_abs

    t_process = time.time() - t_start

    return data.astype(np.float32), t_process


def benchmark_traditional(start_time, end_time):
    """
    Traditional approach: Download ALL data, then process ALL, then audio ready.

    User waits for entire download + processing before hearing anything.
    """
    print("\n" + "=" * 70)
    print("METHOD A: TRADITIONAL (Download All → Process All → First Audio)")
    print("=" * 70)

    total_start = time.time()

    # Step 1: Download ALL 24 hours
    duration_hours = (end_time - start_time).total_seconds() / 3600
    mseed_bytes, t_download = fetch_from_iris(start_time, end_time, f"all {duration_hours:.0f} hours")

    # Step 2: Parse ALL data
    print("\n   Parsing miniSEED...")
    data, actual_rate, t_parse = parse_miniseed(mseed_bytes)
    print(f"   ✓ Parsed {len(data):,} samples ({len(data)/actual_rate:.1f}s) in {t_parse:.2f}s")

    # Step 3: Process ALL data
    print("\n   Processing for audio...")
    audio_data, t_process = process_for_audio(data, actual_rate)
    print(f"   ✓ Processed in {t_process:.2f}s")

    # FIRST AUDIO IS NOW READY
    time_to_first_audio = time.time() - total_start

    print(f"\n   🔊 FIRST AUDIO READY: {time_to_first_audio:.2f}s")

    return {
        'method': 'traditional',
        'duration_hours': duration_hours,
        'download_time': t_download,
        'parse_time': t_parse,
        'process_time': t_process,
        'time_to_first_audio': time_to_first_audio,
        'data_size_mb': len(mseed_bytes) / (1024 * 1024),
        'samples': len(data)
    }


def benchmark_progressive(start_time, end_time, chunk_hours=1):
    """
    Progressive approach: Download FIRST chunk, process it, audio ready.
    Remaining chunks load in background (simulated here).

    User can start listening after just the first chunk is ready.
    """
    print("\n" + "=" * 70)
    print(f"METHOD B: PROGRESSIVE (First {chunk_hours}h chunk → First Audio)")
    print("=" * 70)

    total_start = time.time()
    duration_hours = (end_time - start_time).total_seconds() / 3600

    # Step 1: Download ONLY first chunk
    first_chunk_end = start_time + timedelta(hours=chunk_hours)
    mseed_bytes, t_download = fetch_from_iris(start_time, first_chunk_end, f"first {chunk_hours}h chunk")

    # Step 2: Parse first chunk
    print("\n   Parsing first chunk...")
    data, actual_rate, t_parse = parse_miniseed(mseed_bytes)
    print(f"   ✓ Parsed {len(data):,} samples ({len(data)/actual_rate:.1f}s) in {t_parse:.2f}s")

    # Step 3: Process first chunk
    print("\n   Processing first chunk for audio...")
    audio_data, t_process = process_for_audio(data, actual_rate)
    print(f"   ✓ Processed in {t_process:.2f}s")

    # FIRST AUDIO IS NOW READY
    time_to_first_audio = time.time() - total_start

    print(f"\n   🔊 FIRST AUDIO READY: {time_to_first_audio:.2f}s")

    # Now simulate loading remaining chunks (user is already listening!)
    print(f"\n   📦 Loading remaining {duration_hours - chunk_hours:.0f} hours in background...")

    remaining_chunks = []
    chunk_start = first_chunk_end

    while chunk_start < end_time:
        chunk_end = min(chunk_start + timedelta(hours=chunk_hours), end_time)

        chunk_bytes, chunk_download_time = fetch_from_iris(
            chunk_start, chunk_end,
            f"chunk {len(remaining_chunks) + 2}"
        )

        chunk_data, _, chunk_parse_time = parse_miniseed(chunk_bytes)
        _, chunk_process_time = process_for_audio(chunk_data, actual_rate)

        remaining_chunks.append({
            'download_time': chunk_download_time,
            'parse_time': chunk_parse_time,
            'process_time': chunk_process_time,
            'size_mb': len(chunk_bytes) / (1024 * 1024)
        })

        chunk_start = chunk_end

    total_time = time.time() - total_start
    total_download = t_download + sum(c['download_time'] for c in remaining_chunks)

    print(f"\n   ✓ All {duration_hours:.0f} hours loaded in {total_time:.2f}s total")

    return {
        'method': 'progressive',
        'duration_hours': duration_hours,
        'chunk_hours': chunk_hours,
        'first_chunk_download_time': t_download,
        'first_chunk_parse_time': t_parse,
        'first_chunk_process_time': t_process,
        'time_to_first_audio': time_to_first_audio,
        'total_download_time': total_download,
        'total_time': total_time,
        'first_chunk_size_mb': len(mseed_bytes) / (1024 * 1024),
        'first_chunk_samples': len(data),
        'remaining_chunks': len(remaining_chunks)
    }


def run_benchmark():
    """Run the full benchmark and save results."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 70)
    print("BENCHMARK: Time to First Audio - Traditional vs Progressive")
    print("=" * 70)
    print(f"\nStation: {NETWORK}.{STATION}.{LOCATION}.{CHANNEL}")
    print(f"Sample rate: {SAMPLE_RATE} Hz")

    # Use data from 3 days ago to ensure availability
    end_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=3)
    start_time = end_time - timedelta(hours=24)

    print(f"Time range: {start_time.isoformat()}Z to {end_time.isoformat()}Z")
    print(f"Duration: 24 hours")

    # Run traditional benchmark
    traditional_result = benchmark_traditional(start_time, end_time)

    # Run progressive benchmark
    progressive_result = benchmark_progressive(start_time, end_time, chunk_hours=1)

    # Calculate improvement
    speedup = traditional_result['time_to_first_audio'] / progressive_result['time_to_first_audio']
    time_saved = traditional_result['time_to_first_audio'] - progressive_result['time_to_first_audio']

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n{'Method':<20} {'Time to First Audio':>25}")
    print("-" * 50)
    print(f"{'Traditional':<20} {traditional_result['time_to_first_audio']:>22.2f}s")
    print(f"{'Progressive':<20} {progressive_result['time_to_first_audio']:>22.2f}s")
    print("-" * 50)
    print(f"{'Speedup':<20} {speedup:>22.1f}x")
    print(f"{'Time Saved':<20} {time_saved:>22.2f}s")

    print(f"\n✨ Progressive loading is {speedup:.1f}x faster to first audio!")
    print(f"   Users can start listening {time_saved:.1f} seconds sooner.")

    # Save results
    result_record = {
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'station': f"{NETWORK}.{STATION}.{LOCATION}.{CHANNEL}",
        'data_start': start_time.isoformat() + 'Z',
        'data_end': end_time.isoformat() + 'Z',
        'traditional': traditional_result,
        'progressive': progressive_result,
        'speedup': speedup,
        'time_saved_seconds': time_saved
    }

    # Append to JSONL file
    with open(RESULTS_FILE, 'a') as f:
        f.write(json.dumps(result_record) + '\n')

    print(f"\n📊 Results appended to: {RESULTS_FILE}")

    return result_record


def print_historical_results():
    """Print summary of all historical benchmark runs."""
    if not RESULTS_FILE.exists():
        print("No historical results found.")
        return

    print("\n" + "=" * 70)
    print("HISTORICAL BENCHMARK RESULTS")
    print("=" * 70)

    results = []
    with open(RESULTS_FILE) as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))

    print(f"\n{'Timestamp':<25} {'Traditional':>12} {'Progressive':>12} {'Speedup':>10}")
    print("-" * 65)

    for r in results[-10:]:  # Last 10 runs
        ts = r['timestamp'][:19].replace('T', ' ')
        trad = r['traditional']['time_to_first_audio']
        prog = r['progressive']['time_to_first_audio']
        speedup = r['speedup']
        print(f"{ts:<25} {trad:>10.2f}s {prog:>10.2f}s {speedup:>9.1f}x")

    if len(results) > 1:
        avg_speedup = sum(r['speedup'] for r in results) / len(results)
        avg_time_saved = sum(r['time_saved_seconds'] for r in results) / len(results)
        print("-" * 65)
        print(f"{'Average':<25} {'':<12} {'':<12} {avg_speedup:>9.1f}x")
        print(f"\nAverage time saved: {avg_time_saved:.1f} seconds")


if __name__ == '__main__':
    try:
        result = run_benchmark()
        print_historical_results()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
