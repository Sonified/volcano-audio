#!/usr/bin/env python3
"""
Download and view actual participant data from R2
"""

import boto3
import os
import sys
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

print("🔍 Downloading Participant Data from R2...")
print("=" * 100)

# Get all real participants (R_* format)
prefix = 'volcano-audio-anonymized-data/participants/'
response = s3.list_objects_v2(
    Bucket=R2_BUCKET_NAME,
    Prefix=prefix,
    Delimiter='/'
)

participants = []
if 'CommonPrefixes' in response:
    for prefix_obj in response['CommonPrefixes']:
        participant_path = prefix_obj['Prefix']
        participant_id = participant_path.split('/')[-2]
        if participant_id.startswith('R_'):
            participants.append(participant_id)

print(f"\n📊 Found {len(participants)} real participants\n")

# For each participant, download all submissions
for participant_id in sorted(participants):
    print("\n" + "=" * 100)
    print(f"\n👤 PARTICIPANT: {participant_id}")
    print("-" * 100)
    
    # List all submissions
    submission_prefix = f'volcano-audio-anonymized-data/participants/{participant_id}/submissions/'
    submission_response = s3.list_objects_v2(
        Bucket=R2_BUCKET_NAME,
        Prefix=submission_prefix
    )
    
    if 'Contents' not in submission_response:
        print("   ⚠️  No submissions found")
        continue
    
    submissions = submission_response['Contents']
    print(f"\n   📄 Found {len(submissions)} submission(s)\n")
    
    for i, obj in enumerate(submissions, 1):
        key = obj['Key']
        size = obj['Size']
        modified = obj['LastModified']
        filename = key.split('/')[-1]
        
        print(f"\n   {'─' * 96}")
        print(f"   Submission #{i}: {filename}")
        print(f"   {'─' * 96}")
        print(f"   Size: {size:,} bytes | Modified: {modified}")
        
        # Download and parse
        try:
            response = s3.get_object(Bucket=R2_BUCKET_NAME, Key=key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Extract key information
            session_id = data.get('sessionId', 'N/A')
            session_started = data.get('sessionStarted', 'N/A')
            session_ended = data.get('sessionEnded', 'N/A')
            submission_timestamp = data.get('submissionTimestamp', 'N/A')
            
            # Calculate duration
            duration = "N/A"
            if session_started != 'N/A' and submission_timestamp != 'N/A':
                try:
                    start = datetime.fromisoformat(session_started.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(submission_timestamp.replace('Z', '+00:00'))
                    duration_seconds = (end - start).total_seconds()
                    minutes = int(duration_seconds // 60)
                    seconds = int(duration_seconds % 60)
                    duration = f"{minutes}m {seconds}s"
                except:
                    pass
            
            # Count regions and features
            regions = data.get('regions', [])
            total_features = sum(len(r.get('features', [])) for r in regions)
            
            # Check survey completion
            survey_responses = data.get('surveyResponses', {})
            surveys_completed = []
            if survey_responses.get('pre'): surveys_completed.append('pre')
            if survey_responses.get('post'): surveys_completed.append('post')
            if survey_responses.get('awesf'): surveys_completed.append('awesf')
            if survey_responses.get('activityLevel'): surveys_completed.append('activityLevel')
            
            # Event tracking
            tracking = data.get('tracking', {})
            events = tracking.get('events', [])
            
            print(f"\n   📋 SESSION INFO:")
            print(f"      Session ID:    {session_id}")
            print(f"      Started:       {session_started}")
            print(f"      Ended:         {session_ended}")
            print(f"      Submitted:     {submission_timestamp}")
            print(f"      Duration:      {duration}")
            
            print(f"\n   📊 DATA SUMMARY:")
            print(f"      Events:        {len(events)}")
            print(f"      Regions:       {len(regions)}")
            print(f"      Features:      {total_features}")
            print(f"      Surveys:       {len(surveys_completed)}/4 ({', '.join(surveys_completed)})")
            
            # Show regions in detail
            if regions:
                print(f"\n   🗺️  REGIONS DETAIL:")
                for region in regions:
                    region_num = region.get('regionNumber', '?')
                    region_start = region.get('regionStartTime', 'N/A')
                    region_end = region.get('regionEndTime', 'N/A')
                    features = region.get('features', [])
                    
                    print(f"\n      Region {region_num}: {region_start[:19]} → {region_end[:19]}")
                    print(f"      Features: {len(features)}")
                    
                    for feature in features:
                        feat_num = feature.get('featureNumber', '?')
                        feat_type = feature.get('type', 'Unknown')
                        freq_low = feature.get('lowFreq', '?')
                        freq_high = feature.get('highFreq', '?')
                        repetition = feature.get('repetition', '?')
                        notes = feature.get('notes', '')
                        
                        print(f"         Feature {feat_num} ({feat_type}, {repetition})")
                        print(f"         Freq: {freq_low}-{freq_high} Hz")
                        if notes:
                            print(f"         Notes: {notes}")
            
            # Show volcanos explored
            volcanos = set()
            for event in events:
                if event.get('type') == 'volcano_selected':
                    volcano = event.get('data', {}).get('volcano')
                    if volcano:
                        volcanos.add(volcano)
                elif event.get('type') == 'fetch_data':
                    volcano = event.get('data', {}).get('volcano')
                    if volcano:
                        volcanos.add(volcano)
            
            if volcanos:
                print(f"\n   🌋 VOLCANOES EXPLORED:")
                print(f"      {', '.join(sorted(volcanos))}")
            
        except Exception as e:
            print(f"   ❌ Error reading submission: {e}")

print("\n" + "=" * 100)
print("\n✅ Audit Complete")



