#!/usr/bin/env python3
"""
Download CNS post-survey submissions from R2 and save to final_analysis/data/CNS_POST/
"""

import boto3
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# Get R2 credentials
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')

# Create S3 client
s3 = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name='auto'
)

# Create output directory
output_dir = Path(__file__).parent.parent.parent / 'final_analysis' / 'data' / 'CNS_POST'
output_dir.mkdir(parents=True, exist_ok=True)

print("📥 Downloading CNS submissions from R2...\n")
print(f"Output directory: {output_dir}\n")

# List all CNS submissions
prefix = 'volcano-audio-anonymized-data/CNS_POST/'
response = s3.list_objects_v2(
    Bucket=R2_BUCKET_NAME,
    Prefix=prefix
)

if 'Contents' not in response:
    print("❌ No CNS submissions found in R2")
    exit(1)

files = response['Contents']
print(f"Found {len(files)} CNS submission(s)")
print("="*80)

# Download each file
downloaded = []
for file_obj in files:
    key = file_obj['Key']
    filename = key.split('/')[-1]

    # Skip if it's just the directory
    if not filename:
        continue

    # Download the file
    print(f"\nDownloading: {filename}")
    print(f"  Size: {file_obj['Size']} bytes")
    print(f"  Modified: {file_obj['LastModified']}")

    obj_response = s3.get_object(Bucket=R2_BUCKET_NAME, Key=key)
    content = obj_response['Body'].read().decode('utf-8')
    data = json.loads(content)

    # Save to local file
    output_path = output_dir / filename
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"  ✅ Saved to: {output_path}")

    # Print summary
    if 'responses' in data:
        response_values = list(data['responses'].values())
        print(f"  📊 Responses: {response_values}")

        # Check if all values are the same (quick click-through)
        if len(set(response_values)) == 1:
            print(f"  ⚠️  ALL SAME VALUE ({response_values[0]}) - likely quick click-through")
        elif len(set(response_values)) <= 3:
            print(f"  ⚠️  Only {len(set(response_values))} unique values - possibly quick click-through")

    downloaded.append({
        'filename': filename,
        'participantId': data.get('participantId', 'UNKNOWN'),
        'timestamp': data.get('submissionTimestamp', 'UNKNOWN'),
        'responses': data.get('responses', {}),
        'rawTotal': data.get('rawTotal', 'UNKNOWN')
    })

print("\n" + "="*80)
print(f"✅ Downloaded {len(downloaded)} CNS submission(s) to {output_dir}")
print("\nSummary:")
for item in sorted(downloaded, key=lambda x: x['timestamp'], reverse=True):
    print(f"\n{item['filename']}")
    print(f"  Participant: {item['participantId']}")
    print(f"  Timestamp: {item['timestamp']}")
    print(f"  Raw Total: {item['rawTotal']}")
    if item['responses']:
        values = list(item['responses'].values())
        print(f"  Responses: {values}")
