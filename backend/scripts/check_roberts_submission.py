#!/usr/bin/env python3
"""
Check Robert's test submission
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

participant_id = 'TEST_ROBERT_11_25_25'

print(f"🔍 Checking submission for: {participant_id}")
print("=" * 80)

# List submissions
submission_prefix = f'volcano-audio-anonymized-data/participants/{participant_id}/submissions/'
response = s3.list_objects_v2(
    Bucket=R2_BUCKET_NAME,
    Prefix=submission_prefix
)

if 'Contents' not in response:
    print("❌ NO SUBMISSIONS FOUND")
    exit(1)

# Get the latest submission
latest = response['Contents'][-1]
key = latest['Key']
filename = key.split('/')[-1]

print(f"\n📄 File: {filename}")
print(f"📊 Size: {latest['Size']:,} bytes")
print(f"⏰ Modified: {latest['LastModified']}\n")

# Download and parse
obj_response = s3.get_object(Bucket=R2_BUCKET_NAME, Key=key)
data = json.loads(obj_response['Body'].read().decode('utf-8'))

# Pretty print the whole thing
print("=" * 80)
print("FULL JSON DATA:")
print("=" * 80)
print(json.dumps(data, indent=2))
print("=" * 80)

# Key checks
print("\n✅ KEY DATA CHECKS:")
print(f"   Session ID: {data.get('sessionId', 'MISSING')}")
print(f"   Completed All Surveys: {data.get('completedAllSurveys', 'MISSING')}")
print(f"   Submitted to Qualtrics: {data.get('submittedToQualtrics', 'MISSING')}")

# Regions
regions = data.get('regions', [])
print(f"\n🗺️  REGIONS: {len(regions)}")
for i, region in enumerate(regions, 1):
    print(f"\n   Region {i}:")
    print(f"      Number: {region.get('regionNumber', 'MISSING')}")
    print(f"      Start: {region.get('regionStartTime', 'MISSING')}")
    print(f"      End: {region.get('regionEndTime', 'MISSING')}")
    
    features = region.get('features', [])
    print(f"      Features: {len(features)}")
    
    for j, feature in enumerate(features, 1):
        print(f"\n         Feature {j}:")
        print(f"            Number: {feature.get('featureNumber', 'MISSING')}")
        print(f"            Type: {feature.get('type', 'MISSING')}")
        print(f"            Frequency: {feature.get('lowFreq', '?')}-{feature.get('highFreq', '?')} Hz")
        print(f"            Start: {feature.get('featureStartTime', 'MISSING')}")
        print(f"            End: {feature.get('featureEndTime', 'MISSING')}")
        print(f"            Repetition: {feature.get('repetition', 'MISSING')}")
        print(f"            Notes: {feature.get('notes', 'MISSING')}")

# Survey responses
survey_responses = data.get('surveyResponses', {})
print(f"\n📋 SURVEY RESPONSES: {len(survey_responses)} surveys")
for survey_type, survey_data in survey_responses.items():
    print(f"   ✓ {survey_type}")

# Tracking
tracking = data.get('tracking', {})
events = tracking.get('events', [])
print(f"\n📊 TRACKING EVENTS: {len(events)}")

print("\n" + "=" * 80)
if regions and regions[0].get('regionNumber') and regions[0].get('features', [{}])[0].get('type'):
    print("🎉 SUCCESS! COMPLETE DATA WITH ALL METADATA!")
else:
    print("⚠️  Data exists but missing metadata")



