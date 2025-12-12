#!/usr/bin/env python3
"""
Test TTFA (Time to First Audio) from R2 CDN for all 5 study stations.
This measures the ACTUAL progressive loading experience.
"""

import requests
import time
import zstandard as zstd
import numpy as np
from datetime import datetime, timedelta, timezone
import json

# CDN base URL (public, proxied through Cloudflare)
R2_BASE_URL = "https://cdn.now.audio"

# All 5 stations from the study
STATIONS = [
    {"network": "HV", "station": "OBL", "location": "--", "channel": "HHZ", "volcano": "kilauea", "sample_rate": 100},
    {"network": "HV", "station": "MOKD", "location": "--", "channel": "HHZ", "volcano": "maunaloa", "sample_rate": 100},
    {"network": "AV", "station": "GSTD", "location": "--", "channel": "BHZ", "volcano": "greatsitkin", "sample_rate": 50},
    {"network": "AV", "station": "SSLS", "location": "--", "channel": "BHZ", "volcano": "shishaldin", "sample_rate": 50},
    {"network": "AV", "station": "SPCP", "location": "--", "channel": "BHZ", "volcano": "spurr", "sample_rate": 50},
]


def get_metadata_url(station, date):
    """Build metadata URL for a station/date."""
    year = date.year
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"
    date_str = date.strftime("%Y-%m-%d")

    net = station["network"]
    sta = station["station"]
    loc = station["location"]
    cha = station["channel"]
    volcano = station["volcano"]

    return f"{R2_BASE_URL}/data/{year}/{month}/{day}/{net}/{volcano}/{sta}/{loc}/{cha}/{net}_{sta}_{loc}_{cha}_{date_str}.json"


def get_chunk_url(station, date, chunk_info, chunk_type="10m"):
    """Build chunk URL from metadata."""
    year = date.year
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    net = station["network"]
    sta = station["station"]
    loc = station["location"]
    cha = station["channel"]
    volcano = station["volcano"]

    # Build filename from chunk info
    filename = chunk_info.get("file", "")
    if not filename:
        return None

    return f"{R2_BASE_URL}/data/{year}/{month}/{day}/{net}/{volcano}/{sta}/{loc}/{cha}/{chunk_type}/{filename}"


def test_station_ttfa(station):
    """Test TTFA for a single station."""
    print(f"\n{'='*60}")
    print(f"Station: {station['network']}.{station['station']} ({station['volcano']})")
    print("="*60)

    # Use yesterday's data to ensure availability
    test_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    # Step 1: Fetch metadata
    metadata_url = get_metadata_url(station, test_date)
    print(f"Metadata URL: {metadata_url}")

    t_start = time.time()

    try:
        metadata_response = requests.get(metadata_url, timeout=10)
        t_metadata = (time.time() - t_start) * 1000

        if metadata_response.status_code != 200:
            print(f"  ERROR: Metadata fetch failed: HTTP {metadata_response.status_code}")
            return None

        metadata = metadata_response.json()
        print(f"  Metadata fetched: {t_metadata:.0f}ms")

    except Exception as e:
        print(f"  ERROR: {e}")
        return None

    # Step 2: Get first 10m chunk
    chunks_10m = metadata.get("chunks", {}).get("10m", [])
    if not chunks_10m:
        print(f"  ERROR: No 10m chunks found in metadata")
        return None

    first_chunk = chunks_10m[0]
    chunk_url = get_chunk_url(station, test_date, first_chunk, "10m")

    if not chunk_url:
        print(f"  ERROR: Could not build chunk URL")
        return None

    print(f"  First chunk: {first_chunk.get('start')} - {first_chunk.get('end')}")

    # Step 3: Fetch first chunk
    t_chunk_start = time.time()

    try:
        chunk_response = requests.get(chunk_url, timeout=30)
        t_download = (time.time() - t_chunk_start) * 1000

        if chunk_response.status_code != 200:
            print(f"  ERROR: Chunk fetch failed: HTTP {chunk_response.status_code}")
            return None

        compressed_data = chunk_response.content
        compressed_size = len(compressed_data)
        print(f"  Chunk downloaded: {compressed_size/1024:.1f} KB in {t_download:.0f}ms")

    except Exception as e:
        print(f"  ERROR fetching chunk: {e}")
        return None

    # Step 4: Decompress
    t_decompress_start = time.time()

    try:
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed_data)
        t_decompress = (time.time() - t_decompress_start) * 1000

        # Parse as int32 samples
        samples = np.frombuffer(decompressed, dtype=np.int32)
        duration_sec = len(samples) / station["sample_rate"]

        print(f"  Decompressed: {len(decompressed)/1024:.1f} KB ({len(samples):,} samples, {duration_sec:.0f}s) in {t_decompress:.1f}ms")

    except Exception as e:
        print(f"  ERROR decompressing: {e}")
        return None

    # Total TTFA
    t_total = time.time() - t_start
    ttfa_ms = t_total * 1000

    print(f"\n  TTFA: {ttfa_ms:.0f}ms")
    print(f"    - Metadata: {t_metadata:.0f}ms")
    print(f"    - Download: {t_download:.0f}ms")
    print(f"    - Decompress: {t_decompress:.1f}ms")

    return {
        "station": f"{station['network']}.{station['station']}",
        "volcano": station["volcano"],
        "ttfa_ms": ttfa_ms,
        "metadata_ms": t_metadata,
        "download_ms": t_download,
        "decompress_ms": t_decompress,
        "chunk_size_kb": compressed_size / 1024,
        "samples": len(samples),
        "duration_sec": duration_sec
    }


def run_all_stations():
    """Test all 5 study stations."""
    print("="*60)
    print("CDN TTFA TEST - All 5 Study Stations")
    print("="*60)
    print(f"Testing at: {datetime.now(timezone.utc).isoformat()}")
    print(f"R2 CDN: {R2_BASE_URL}")

    results = []

    for station in STATIONS:
        result = test_station_ttfa(station)
        if result:
            results.append(result)
        time.sleep(0.5)  # Small delay between tests

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if results:
        print(f"\n{'Station':<20} {'Volcano':<15} {'TTFA (ms)':<12} {'Download':<12} {'Decompress':<12}")
        print("-"*75)

        for r in results:
            print(f"{r['station']:<20} {r['volcano']:<15} {r['ttfa_ms']:<12.0f} {r['download_ms']:<12.0f} {r['decompress_ms']:<12.1f}")

        avg_ttfa = sum(r['ttfa_ms'] for r in results) / len(results)
        avg_download = sum(r['download_ms'] for r in results) / len(results)
        avg_decompress = sum(r['decompress_ms'] for r in results) / len(results)

        print("-"*75)
        print(f"{'AVERAGE':<20} {'':<15} {avg_ttfa:<12.0f} {avg_download:<12.0f} {avg_decompress:<12.1f}")

        print(f"\nAverage TTFA: {avg_ttfa:.0f}ms")
        print(f"  (Metadata + Download + Decompress)")
    else:
        print("No successful tests!")

    return results


if __name__ == "__main__":
    run_all_stations()
