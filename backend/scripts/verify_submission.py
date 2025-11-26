#!/usr/bin/env python3
"""
Verify a specific Qualtrics submission by Response ID
Checks that all expected data was submitted correctly
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load environment variables from project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

QUALTRICS_API_TOKEN = os.getenv('QUALTRICS_API_TOKEN')
QUALTRICS_DATACENTER = os.getenv('QUALTRICS_DATACENTER', 'oregon.yul1')
SURVEY_ID = 'SV_bNni117IsBWNZWu'

def get_response(response_id):
    """Fetch a specific response from Qualtrics"""
    url = f'https://{QUALTRICS_DATACENTER}.qualtrics.com/API/v3/surveys/{SURVEY_ID}/responses/{response_id}'
    
    headers = {
        'X-API-TOKEN': QUALTRICS_API_TOKEN,
        'Content-Type': 'application/json'
    }
    
    print(f"🔍 Fetching response: {response_id}")
    print(f"   From survey: {SURVEY_ID}")
    print(f"   Datacenter: {QUALTRICS_DATACENTER}")
    print()
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def verify_submission(data):
    """Verify that the submission contains expected data"""
    if not data or 'result' not in data:
        print("❌ No data received")
        return False
    
    result = data['result']
    values = result.get('values', {})
    labels = result.get('labels', {})
    
    print("═══════════════════════════════════════════════════════════")
    print("📊 SUBMISSION VERIFICATION")
    print("═══════════════════════════════════════════════════════════\n")
    
    # Basic info
    print("📋 Basic Information:")
    print(f"   Response ID: {result.get('responseId')}")
    print(f"   Participant ID: {values.get('ParticipantID', 'NOT FOUND')}")
    print(f"   Submitted: {result.get('endDate')}")
    print()
    
    # Check surveys
    print("📊 Survey Responses:")
    has_pre = 'QID1_1' in values  # Pre-survey calm
    has_post = 'QID2_1' in values  # Post-survey calm
    has_awesf = 'QID3_1' in values  # AWE-SF first question
    has_activity = 'QID4' in values  # Activity level
    
    print(f"   Pre-Survey: {'✅ FOUND' if has_pre else '❌ MISSING'}")
    print(f"   Post-Survey: {'✅ FOUND' if has_post else '❌ MISSING'}")
    print(f"   AWE-SF: {'✅ FOUND' if has_awesf else '❌ MISSING'}")
    print(f"   Activity Level: {'✅ FOUND' if has_activity else '❌ MISSING'}")
    print()
    
    # Check features matrix (QID8)
    print("🎯 Features Matrix:")
    feature_count = 0
    for i in range(1, 21):  # Check up to 20 features
        feature_key = f'QID8_{i}_1'  # First column (feature number)
        if feature_key in values:
            feature_count += 1
            print(f"   Feature {i}:")
            print(f"      Type: {labels.get(f'QID8_{i}_2', 'N/A')}")
            print(f"      Repetition: {labels.get(f'QID8_{i}_3', 'N/A')}")
            print(f"      Low Freq: {values.get(f'QID8_{i}_9', 'N/A')}")
            print(f"      High Freq: {values.get(f'QID8_{i}_10', 'N/A')}")
            print(f"      Notes: {values.get(f'QID8_{i}_6', 'N/A')}")
    
    print(f"\n   Total Features: {feature_count}")
    print()
    
    # Check embedded data
    print("📦 Embedded Data Fields:")
    
    # SessionTracking
    session_tracking = values.get('SessionTracking')
    if session_tracking:
        print(f"   SessionTracking: ✅ FOUND ({len(session_tracking)} chars)")
        try:
            st_data = json.loads(session_tracking)
            print(f"      Session ID: {st_data.get('sessionId')}")
            print(f"      Duration: {st_data.get('sessionDurationMs')}ms")
            print(f"      Completed All Surveys: {st_data.get('completedAllSurveys')}")
            print(f"      Regions: {len(st_data.get('regions', []))}")
            
            # Check for log frequency flag
            uses_corrected = st_data.get('usesCorrectedLogFormula')
            print(f"      Uses Corrected Log Formula: {uses_corrected} {'✅' if uses_corrected else '❌'}")
        except json.JSONDecodeError:
            print("      ⚠️ Could not parse JSON")
    else:
        print("   SessionTracking: ❌ MISSING")
    print()
    
    # JSON_data
    json_data = values.get('JSON_data')
    if json_data:
        print(f"   JSON_data: ✅ FOUND ({len(json_data)} chars)")
        try:
            jd = json.loads(json_data)
            print(f"      Survey Answers: {list(jd.get('surveyAnswers', {}).keys())}")
            print(f"      Interactions: {len(jd.get('interactions', []))}")
        except json.JSONDecodeError:
            print("      ⚠️ Could not parse JSON")
    else:
        print("   JSON_data: ❌ MISSING")
    print()
    
    # Summary
    print("═══════════════════════════════════════════════════════════")
    print("📊 VERIFICATION SUMMARY")
    print("═══════════════════════════════════════════════════════════")
    
    checks = {
        'Participant ID': values.get('ParticipantID') is not None,
        'Post-Survey': has_post,
        'AWE-SF': has_awesf,
        'Activity Level': has_activity,
        'Features (2 expected)': feature_count == 2,
        'SessionTracking': session_tracking is not None,
        'JSON_data': json_data is not None,
        'Corrected Log Formula Flag': uses_corrected if session_tracking else False
    }
    
    for check, passed in checks.items():
        print(f"   {check}: {'✅ PASS' if passed else '❌ FAIL'}")
    
    all_passed = all(checks.values())
    print()
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
    else:
        print("⚠️ SOME CHECKS FAILED - Review above for details")
        if not has_pre:
            print("   Note: Pre-survey missing is expected for this test (timeout scenario)")
    
    return all_passed

if __name__ == '__main__':
    if len(sys.argv) > 1:
        response_id = sys.argv[1]
    else:
        response_id = 'R_6PDihdICaUUYnl4'  # Default to the test response
    
    data = get_response(response_id)
    
    if data:
        verify_submission(data)
        
        # Optionally save full response to file
        output_file = f'/Users/robertalexander/GitHub/volcano-audio/backend/tests/test_logs/response_{response_id}.json'
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 Full response saved to: {output_file}")

