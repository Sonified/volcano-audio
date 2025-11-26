#!/usr/bin/env python3
"""
Quick audit of participant data on R2
"""

import boto3
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / '.env'
print(f"Loading .env from: {env_path}")
print(f".env exists: {env_path.exists()}")
load_dotenv(env_path)

# Get R2 credentials
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')

print(f"R2_ACCOUNT_ID: {R2_ACCOUNT_ID[:10] if R2_ACCOUNT_ID else 'NOT FOUND'}...")
print(f"R2_BUCKET_NAME: {R2_BUCKET_NAME}")

if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME]):
    print("\n❌ Missing R2 credentials!")
    if not R2_ACCOUNT_ID: print("   - R2_ACCOUNT_ID missing")
    if not R2_ACCESS_KEY_ID: print("   - R2_ACCESS_KEY_ID missing")
    if not R2_SECRET_ACCESS_KEY: print("   - R2_SECRET_ACCESS_KEY missing")
    if not R2_BUCKET_NAME: print("   - R2_BUCKET_NAME missing")
    sys.exit(1)

# Create S3 client
s3 = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name='auto'
)

print("🔍 Auditing R2 Participant Data...")
print("=" * 80)

# List all participants
prefix = 'volcano-audio-anonymized-data/participants/'
response = s3.list_objects_v2(
    Bucket=R2_BUCKET_NAME,
    Prefix=prefix,
    Delimiter='/'
)

# Get unique participant IDs from CommonPrefixes
participants = []
if 'CommonPrefixes' in response:
    for prefix_obj in response['CommonPrefixes']:
        participant_path = prefix_obj['Prefix']
        # Extract participant ID from path
        participant_id = participant_path.split('/')[-2]
        participants.append(participant_id)

print(f"\n📊 Total participants found: {len(participants)}")
print(f"\n{'Participant ID':<30} {'Type':<10} {'Submissions':<15} {'Status':<10}")
print("-" * 80)

# Separate real participants from test IDs
real_participants = []
test_participants = []

for participant_id in sorted(participants):
    # Check if it's a Qualtrics ID (starts with R_)
    is_qualtrics = participant_id.startswith('R_')
    
    # Count submissions
    submission_prefix = f'volcano-audio-anonymized-data/participants/{participant_id}/submissions/'
    submission_response = s3.list_objects_v2(
        Bucket=R2_BUCKET_NAME,
        Prefix=submission_prefix
    )
    submission_count = len(submission_response.get('Contents', []))
    
    # Check for status file
    status_key = f'volcano-audio-anonymized-data/participants/{participant_id}/user-status/status.json'
    has_status = False
    try:
        s3.head_object(Bucket=R2_BUCKET_NAME, Key=status_key)
        has_status = True
    except:
        pass
    
    participant_type = "REAL" if is_qualtrics else "TEST"
    status = "✓" if has_status else "✗"
    
    print(f"{participant_id:<30} {participant_type:<10} {submission_count:<15} {status:<10}")
    
    if is_qualtrics:
        real_participants.append({
            'id': participant_id,
            'submissions': submission_count,
            'has_status': has_status
        })
    else:
        test_participants.append(participant_id)

print("\n" + "=" * 80)
print(f"\n📈 SUMMARY:")
print(f"   Real Participants (R_*): {len(real_participants)}")
print(f"   Test Participants: {len(test_participants)}")
print(f"   Total: {len(participants)}")

# Look for the specific participant
target_id = "R_3AKHxZD5uNa4XOF"
print(f"\n🎯 Looking for specific participant: {target_id}")

if target_id in participants:
    print(f"   ✅ FOUND on R2!")
    
    # Get detailed info
    submission_prefix = f'volcano-audio-anonymized-data/participants/{target_id}/submissions/'
    submission_response = s3.list_objects_v2(
        Bucket=R2_BUCKET_NAME,
        Prefix=submission_prefix
    )
    
    if 'Contents' in submission_response:
        print(f"\n   📄 Submission files:")
        for obj in submission_response['Contents']:
            key = obj['Key']
            size = obj['Size']
            modified = obj['LastModified']
            filename = key.split('/')[-1]
            print(f"      - {filename}")
            print(f"        Size: {size} bytes")
            print(f"        Modified: {modified}")
            
            # Download and show preview
            response = s3.get_object(Bucket=R2_BUCKET_NAME, Key=key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            
            print(f"        Session ID: {data.get('sessionId', 'N/A')}")
            print(f"        Started: {data.get('sessionStarted', 'N/A')}")
            print(f"        Regions: {len(data.get('regions', []))}")
            
            # Count features
            total_features = sum(len(r.get('features', [])) for r in data.get('regions', []))
            print(f"        Features: {total_features}")
            print()
else:
    print(f"   ❌ NOT FOUND on R2")

print("\n" + "=" * 80)
print("\n💡 If your collaborator sees 38 responses, they might be counting:")
print("   - Individual survey submissions (4 per session)")
print("   - Partial sessions (started but not completed)")
print("   - Multiple sessions from same participant")
print("   - Or they're looking at Qualtrics's own response log")

