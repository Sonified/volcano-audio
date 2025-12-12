#!/usr/bin/env python3
"""
Comprehensive Benchmark: Time to First Audio - All Active Volcano Stations

Tests all active stations from our study:
- HV.OBL (Kilauea, Hawaii) - 100 Hz
- HV.MOKD (Mauna Loa, Hawaii) - 100 Hz
- AV.GSTD (Great Sitkin, Alaska) - 50 Hz
- AV.SSLS (Shishaldin, Alaska) - 50 Hz
- AV.SPCP (Spurr, Alaska) - 50 Hz

Compares Traditional vs Progressive loading for 24 hours of data.
"""

import requests
import time
import numpy as np
from scipy import signal
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

# All active stations from stations_config.json
STATIONS = [
    {"network": "HV", "station": "OBL", "location": "--", "channel": "HHZ", "sample_rate": 100, "volcano": "Kilauea"},
    {"network": "HV", "station": "MOKD", "location": "--", "channel": "HHZ", "sample_rate": 100, "volcano": "Mauna Loa"},
    {"network": "AV", "station": "GSTD", "location": "--", "channel": "BHZ", "sample_rate": 50, "volcano": "Great Sitkin"},
    {"network": "AV", "station": "SSLS", "location": "--", "channel": "BHZ", "sample_rate": 50, "volcano": "Shishaldin"},
    {"network": "AV", "station": "SPCP", "location": "--", "channel": "BHZ", "sample_rate": 50, "volcano": "Spurr"},
]

IRIS_URL = "https://service.iris.edu/fdsnws/dataselect/1/query"

OUTPUT_DIR = Path(__file__).parent / "benchmark_results"
RESULTS_FILE = OUTPUT_DIR / "all_stations_benchmark.jsonl"


def fetch_from_iris(network, station, location, channel, start_time, end_time):
    """Fetch miniSEED data from IRIS."""
    params = {
        "net": network,
        "sta": station,
        "loc": location,
        "cha": channel,
        "start": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "end": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "format": "miniseed"
    }

    t_start = time.time()
    response = requests.get(IRIS_URL, params=params, timeout=120)
    t_download = time.time() - t_start

    if response.status_code != 200:
        raise Exception(f"IRIS returned {response.status_code}")

    return response.content, t_download


def parse_miniseed(mseed_bytes):
    """Parse miniSEED to numpy array."""
    from obspy import read

    t_start = time.time()

    temp_path = OUTPUT_DIR / "temp_mseed.mseed"
    with open(temp_path, 'wb') as f:
        f.write(mseed_bytes)

    st = read(str(temp_path))
    st.merge(method=1, fill_value=0)

    data = st[0].data.astype(np.float64)
    actual_rate = st[0].stats.sampling_rate

    t_parse = time.time() - t_start
    temp_path.unlink()

    return data, actual_rate, t_parse


def process_for_audio(data, sample_rate):
    """Apply audification processing pipeline."""
    t_start = time.time()

    # Detrend
    data = data - np.mean(data)

    # Taper
    taper = signal.windows.tukey(len(data), alpha=0.05)
    data = data * taper

    # High-pass at 0.045 Hz
    hp_freq = 0.045
    sos_hp = signal.butter(2, hp_freq, btype='high', fs=sample_rate, output='sos')
    data = signal.sosfilt(sos_hp, data)

    # Low-pass (anti-aliasing) - scale based on sample rate
    nyquist = sample_rate / 2
    lp_freq = min(nyquist * 0.95, 47.6)  # Stay below Nyquist
    sos_lp = signal.butter(4, lp_freq, btype='low', fs=sample_rate, output='sos')
    data = signal.sosfilt(sos_lp, data)

    # Normalize
    max_abs = np.max(np.abs(data))
    if max_abs > 0:
        data = data / max_abs

    t_process = time.time() - t_start
    return data.astype(np.float32), t_process


def benchmark_station(station_config, start_time, end_time):
    """Benchmark a single station with both methods."""
    net = station_config["network"]
    sta = station_config["station"]
    loc = station_config["location"]
    cha = station_config["channel"]
    volcano = station_config["volcano"]
    sample_rate = station_config["sample_rate"]

    station_id = f"{net}.{sta}.{loc}.{cha}"
    print(f"\n{'='*70}")
    print(f"STATION: {station_id} ({volcano})")
    print(f"Sample rate: {sample_rate} Hz")
    print("="*70)

    result = {
        "station": station_id,
        "volcano": volcano,
        "sample_rate": sample_rate,
        "traditional": None,
        "progressive": None,
        "error": None
    }

    try:
        # === TRADITIONAL ===
        print(f"\n  [TRADITIONAL] Downloading all 24 hours...")
        trad_start = time.time()

        mseed_bytes, t_download = fetch_from_iris(net, sta, loc, cha, start_time, end_time)
        print(f"    Downloaded {len(mseed_bytes)/(1024*1024):.2f} MB in {t_download:.2f}s")

        data, actual_rate, t_parse = parse_miniseed(mseed_bytes)
        print(f"    Parsed {len(data):,} samples in {t_parse:.2f}s")

        _, t_process = process_for_audio(data, actual_rate)
        print(f"    Processed in {t_process:.2f}s")

        trad_total = time.time() - trad_start
        print(f"    🔊 TRADITIONAL Time to First Audio: {trad_total:.2f}s")

        result["traditional"] = {
            "download_time": t_download,
            "parse_time": t_parse,
            "process_time": t_process,
            "time_to_first_audio": trad_total,
            "data_size_mb": len(mseed_bytes) / (1024 * 1024),
            "samples": len(data)
        }

        # === PROGRESSIVE ===
        print(f"\n  [PROGRESSIVE] Downloading first 1 hour chunk...")
        prog_start = time.time()

        first_chunk_end = start_time + timedelta(hours=1)
        chunk_bytes, t_chunk_download = fetch_from_iris(net, sta, loc, cha, start_time, first_chunk_end)
        print(f"    Downloaded {len(chunk_bytes)/(1024*1024):.2f} MB in {t_chunk_download:.2f}s")

        chunk_data, chunk_rate, t_chunk_parse = parse_miniseed(chunk_bytes)
        print(f"    Parsed {len(chunk_data):,} samples in {t_chunk_parse:.2f}s")

        _, t_chunk_process = process_for_audio(chunk_data, chunk_rate)
        print(f"    Processed in {t_chunk_process:.2f}s")

        prog_total = time.time() - prog_start
        print(f"    🔊 PROGRESSIVE Time to First Audio: {prog_total:.2f}s")

        result["progressive"] = {
            "first_chunk_download_time": t_chunk_download,
            "first_chunk_parse_time": t_chunk_parse,
            "first_chunk_process_time": t_chunk_process,
            "time_to_first_audio": prog_total,
            "first_chunk_size_mb": len(chunk_bytes) / (1024 * 1024),
            "first_chunk_samples": len(chunk_data)
        }

        # === COMPARISON ===
        speedup = trad_total / prog_total
        time_saved = trad_total - prog_total
        result["speedup"] = speedup
        result["time_saved"] = time_saved

        print(f"\n  📊 SPEEDUP: {speedup:.1f}x ({time_saved:.1f}s saved)")

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        result["error"] = str(e)

    return result


def run_comprehensive_benchmark():
    """Run benchmark on all stations."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("="*70)
    print("COMPREHENSIVE BENCHMARK: All Active Volcano Stations")
    print("="*70)
    print(f"\nStations to test: {len(STATIONS)}")
    for s in STATIONS:
        print(f"  - {s['network']}.{s['station']} ({s['volcano']}) @ {s['sample_rate']} Hz")

    # Use data from 3 days ago
    end_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=3)
    start_time = end_time - timedelta(hours=24)
    print(f"\nTime range: {start_time.isoformat()}Z to {end_time.isoformat()}Z")

    all_results = []

    for i, station_config in enumerate(STATIONS, 1):
        print(f"\n[{i}/{len(STATIONS)}]", end="")
        result = benchmark_station(station_config, start_time, end_time)
        result["timestamp"] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        result["data_start"] = start_time.isoformat() + 'Z'
        result["data_end"] = end_time.isoformat() + 'Z'
        all_results.append(result)

        # Small delay between stations
        if i < len(STATIONS):
            print("\n  ⏳ Waiting 2s before next station...")
            time.sleep(2)

    # === SUMMARY ===
    print("\n" + "="*70)
    print("SUMMARY: ALL STATIONS")
    print("="*70)

    successful = [r for r in all_results if r["error"] is None]
    failed = [r for r in all_results if r["error"] is not None]

    print(f"\n{'Station':<25} {'Volcano':<15} {'Traditional':>12} {'Progressive':>12} {'Speedup':>10}")
    print("-"*80)

    for r in all_results:
        if r["error"]:
            print(f"{r['station']:<25} {r['volcano']:<15} {'ERROR':>12} {'-':>12} {'-':>10}")
        else:
            trad = r["traditional"]["time_to_first_audio"]
            prog = r["progressive"]["time_to_first_audio"]
            speedup = r["speedup"]
            print(f"{r['station']:<25} {r['volcano']:<15} {trad:>10.2f}s {prog:>10.2f}s {speedup:>9.1f}x")

    if successful:
        avg_speedup = sum(r["speedup"] for r in successful) / len(successful)
        avg_time_saved = sum(r["time_saved"] for r in successful) / len(successful)
        print("-"*80)
        print(f"{'AVERAGE':<25} {'':<15} {'':<12} {'':<12} {avg_speedup:>9.1f}x")
        print(f"\n✨ Average speedup: {avg_speedup:.1f}x")
        print(f"   Average time saved: {avg_time_saved:.1f} seconds")

    if failed:
        print(f"\n⚠️  {len(failed)} station(s) failed:")
        for r in failed:
            print(f"   - {r['station']}: {r['error']}")

    # Save results
    with open(RESULTS_FILE, 'a') as f:
        for r in all_results:
            f.write(json.dumps(r) + '\n')

    print(f"\n📊 Results appended to: {RESULTS_FILE}")

    return all_results


if __name__ == '__main__':
    try:
        run_comprehensive_benchmark()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
