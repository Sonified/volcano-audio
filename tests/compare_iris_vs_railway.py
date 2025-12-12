#!/usr/bin/env python3
"""
Compare data from IRIS direct vs Railway backend.
Validates we're getting the same amount of data.
"""

import requests
import time
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Test configuration - Kilauea
NETWORK = "HV"
STATION = "OBL"
LOCATION = "--"
CHANNEL = "HHZ"
SAMPLE_RATE = 100

IRIS_URL = "https://service.iris.edu/fdsnws/dataselect/1/query"
RAILWAY_URL = "https://volcano-audio-collector-production.up.railway.app/api/stream-audio"

OUTPUT_DIR = Path(__file__).parent / "benchmark_results"


def fetch_from_iris(start_time, end_time):
    """Fetch directly from IRIS."""
    params = {
        "net": NETWORK,
        "sta": STATION,
        "loc": LOCATION,
        "cha": CHANNEL,
        "start": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "end": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "format": "miniseed"
    }

    print(f"\n[IRIS DIRECT]")
    print(f"  URL: {IRIS_URL}")
    print(f"  Time: {params['start']} to {params['end']}")

    t_start = time.time()
    response = requests.get(IRIS_URL, params=params, timeout=300)
    t_download = time.time() - t_start

    if response.status_code != 200:
        print(f"  ERROR: HTTP {response.status_code}")
        return None, t_download, 0

    size_mb = len(response.content) / (1024 * 1024)
    print(f"  Downloaded: {size_mb:.2f} MB in {t_download:.2f}s")

    # Parse with obspy to get sample count
    from obspy import read
    temp_path = OUTPUT_DIR / "temp_iris.mseed"
    with open(temp_path, 'wb') as f:
        f.write(response.content)

    st = read(str(temp_path))
    st.merge(method=1, fill_value=0)
    samples = len(st[0].data)
    actual_rate = st[0].stats.sampling_rate
    temp_path.unlink()

    print(f"  Samples: {samples:,} @ {actual_rate} Hz")
    print(f"  Duration: {samples/actual_rate:.1f} seconds ({samples/actual_rate/3600:.2f} hours)")

    return response.content, t_download, samples


def fetch_from_railway(start_time, duration_hours):
    """Fetch from Railway backend (the real user path)."""
    request_body = {
        "network": NETWORK,
        "station": STATION,
        "location": LOCATION,
        "channel": CHANNEL,
        "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "duration": duration_hours * 3600,  # seconds
        "highpass_hz": 0.045,
        "normalize": False,
        "send_raw": False
    }

    print(f"\n[RAILWAY BACKEND]")
    print(f"  URL: {RAILWAY_URL}")
    print(f"  Start: {request_body['starttime']}, Duration: {duration_hours}h")

    t_start = time.time()
    try:
        response = requests.post(
            RAILWAY_URL,
            json=request_body,
            timeout=300,
            headers={'Content-Type': 'application/json'}
        )
        t_download = time.time() - t_start

        if response.status_code != 200:
            print(f"  ERROR: HTTP {response.status_code}")
            try:
                print(f"  {response.json()}")
            except:
                print(f"  {response.text[:200]}")
            return None, t_download, 0

        size_mb = len(response.content) / (1024 * 1024)
        print(f"  Downloaded: {size_mb:.2f} MB in {t_download:.2f}s")

        # Check compression header
        compression = response.headers.get('X-Compression', 'none')
        print(f"  Compression: {compression}")

        # Parse the response format: [metadata_length (4 bytes)] [metadata_json] [float32_samples]
        data = response.content

        # If compressed with zstd, decompress first
        if compression == 'zstd':
            try:
                import zstandard as zstd
                dctx = zstd.ZstdDecompressor()
                data = dctx.decompress(data)
                print(f"  Decompressed: {len(data)/(1024*1024):.2f} MB")
            except ImportError:
                print("  WARNING: zstandard not installed, can't decompress")
                return None, t_download, 0

        # Parse metadata
        metadata_length = int.from_bytes(data[:4], 'little')
        metadata_json = data[4:4+metadata_length].decode('utf-8')
        import json
        metadata = json.loads(metadata_json)

        print(f"  Metadata: {metadata}")

        # Parse float32 samples
        samples_data = data[4+metadata_length:]
        samples = np.frombuffer(samples_data, dtype=np.float32)

        print(f"  Samples: {len(samples):,}")
        print(f"  Duration: {len(samples)/SAMPLE_RATE:.1f} seconds ({len(samples)/SAMPLE_RATE/3600:.2f} hours)")

        return data, t_download, len(samples)

    except requests.exceptions.Timeout:
        print(f"  TIMEOUT after {time.time() - t_start:.1f}s")
        return None, time.time() - t_start, 0
    except Exception as e:
        print(f"  ERROR: {e}")
        return None, time.time() - t_start, 0


def run_comparison():
    """Run comparison for various durations."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 70)
    print("COMPARISON: IRIS Direct vs Railway Backend")
    print("=" * 70)
    print(f"Station: {NETWORK}.{STATION}.{LOCATION}.{CHANNEL}")
    print(f"Sample rate: {SAMPLE_RATE} Hz")

    # Test 3 days ago to ensure data availability
    end_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=3)

    # Test different durations
    for hours in [1, 4, 24]:
        print(f"\n{'='*70}")
        print(f"TESTING: {hours} hour(s) of data")
        print("="*70)

        start_time = end_time - timedelta(hours=hours)
        expected_samples = hours * 3600 * SAMPLE_RATE

        print(f"Expected samples: {expected_samples:,}")

        # IRIS
        iris_data, iris_time, iris_samples = fetch_from_iris(start_time, end_time)

        # Railway
        railway_data, railway_time, railway_samples = fetch_from_railway(start_time, hours)

        # Summary
        print(f"\n  COMPARISON:")
        print(f"  {'Source':<15} {'Time':>10} {'Samples':>15} {'% Expected':>12}")
        print(f"  {'-'*55}")

        if iris_samples > 0:
            iris_pct = (iris_samples / expected_samples) * 100
            print(f"  {'IRIS':<15} {iris_time:>8.2f}s {iris_samples:>15,} {iris_pct:>11.1f}%")
        else:
            print(f"  {'IRIS':<15} {'FAILED':>10} {'-':>15} {'-':>12}")

        if railway_samples > 0:
            railway_pct = (railway_samples / expected_samples) * 100
            print(f"  {'Railway':<15} {railway_time:>8.2f}s {railway_samples:>15,} {railway_pct:>11.1f}%")
        else:
            print(f"  {'Railway':<15} {'FAILED':>10} {'-':>15} {'-':>12}")

        if iris_samples > 0 and railway_samples > 0:
            match = "MATCH" if abs(iris_samples - railway_samples) < 100 else "MISMATCH"
            print(f"\n  Result: {match}")


if __name__ == '__main__':
    run_comparison()
