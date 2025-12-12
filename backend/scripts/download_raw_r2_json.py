#!/usr/bin/env python3
"""
Download raw JSON files from R2 to inspect exactly what's stored
"""

import boto3
import os
import json
from pathlib import Path
from dotenv import load_dotenv

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

# Download one example from each participant to inspect
participants_to_check = [
    'R_1V3caOYK2YJcVLi',
    'R_5JaVr26m73u2RY5', 
    'R_5xRUHrX8m8iB6m5'
]

print("📥 Downloading raw JSON files from R2...\n")

for participant_id in participants_to_check:
    print(f"\n{'='*80}")
    print(f"PARTICIPANT: {participant_id}")
    print('='*80)
    
    # Get first submission file
    submission_prefix = f'volcano-audio-anonymized-data/participants/{participant_id}/submissions/'
    response = s3.list_objects_v2(
        Bucket=R2_BUCKET_NAME,
        Prefix=submission_prefix
    )
    
    if 'Contents' not in response:
        print("No submissions found")
        continue
    
    # Download first submission
    first_file = response['Contents'][0]
    key = first_file['Key']
    filename = key.split('/')[-1]
    
    print(f"\nFile: {filename}")
    print(f"Size: {first_file['Size']} bytes\n")
    
    # Download and print raw JSON
    obj_response = s3.get_object(Bucket=R2_BUCKET_NAME, Key=key)
    raw_json = obj_response['Body'].read().decode('utf-8')
    
    print("RAW JSON:")
    print("-" * 80)
    print(raw_json)
    print("-" * 80)
    
    # Also parse and print pretty
    data = json.loads(raw_json)
    print("\nPRETTY PRINTED:")
    print("-" * 80)
    print(json.dumps(data, indent=2))
    print("-" * 80)
    
    # Check for survey data
    print("\n🔍 SURVEY DATA CHECK:")
    if 'surveyResponses' in data:
        print(f"   ✅ Has 'surveyResponses' key")
        print(f"   Contents: {list(data['surveyResponses'].keys())}")
    else:
        print(f"   ❌ NO 'surveyResponses' key")
    
    # Check for tracking data
    print("\n🔍 TRACKING DATA CHECK:")
    if 'tracking' in data:
        print(f"   ✅ Has 'tracking' key")
        if 'events' in data['tracking']:
            print(f"   Events count: {len(data['tracking']['events'])}")
        else:
            print(f"   ❌ NO 'events' in tracking")
    else:
        print(f"   ❌ NO 'tracking' key")
    
    print("\n")

print("\n" + "="*80)
print("✅ Download complete")



