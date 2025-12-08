#!/usr/bin/env python3
"""
Test CNS upload to R2
Tests uploading a CNS survey response to the R2 bucket
"""

import os
import json
import boto3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# R2 configuration
s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("R2_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
    region_name="auto"
)

BUCKET = os.getenv("R2_BUCKET_NAME")

def test_cns_upload():
    """Test uploading a CNS survey response"""

    # Test data
    participant_id = "TEST_CNS_UPLOAD"
    timestamp = datetime.now().isoformat().replace(":", "-").replace(".", "-")

    test_payload = {
        "participantId": participant_id,
        "surveyType": "CNS_POST",
        "submissionTimestamp": datetime.now().isoformat(),
        "responses": {
            "cns1": 4,
            "cns2": 3,
            "cns3": 5,
            "cns4": 2,  # reverse scored
            "cns5": 4,
            "cns6": 3,
            "cns7": 4,
            "cns8": 5,
            "cns9": 3,
            "cns10": 4,
            "cns11": 4,
            "cns12": 2,  # reverse scored
            "cns13": 5,
            "cns14": 1   # reverse scored
        },
        "reverseScoreItems": [4, 12, 14],
        "rawTotal": 49,
        "metadata": {
            "userAgent": "Test Script",
            "screenWidth": 1920,
            "screenHeight": 1080
        }
    }

    # Create the key path
    filename = f"{participant_id}_CNS_POST_{timestamp}.json"
    key = f"volcano-audio-anonymized-data/participants/{participant_id}/CNS_POST/{filename}"

    print(f"Testing CNS upload to R2...")
    print(f"Bucket: {BUCKET}")
    print(f"Key: {key}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    print()

    try:
        # Upload to R2
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=json.dumps(test_payload, indent=2),
            ContentType="application/json"
        )
        print(f"✅ Upload successful!")
        print(f"   Path: {key}")

        # Verify by reading it back
        print()
        print("Verifying upload by reading it back...")
        response = s3.get_object(Bucket=BUCKET, Key=key)
        content = json.loads(response["Body"].read().decode("utf-8"))
        print(f"✅ Verification successful!")
        print(f"   Read back participantId: {content['participantId']}")
        print(f"   Read back surveyType: {content['surveyType']}")

        # Clean up test data
        print()
        print("Cleaning up test data...")
        s3.delete_object(Bucket=BUCKET, Key=key)
        print("✅ Test data deleted")

        return True

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("CNS Upload Test")
    print("=" * 60)
    print()

    success = test_cns_upload()

    print()
    print("=" * 60)
    if success:
        print("TEST PASSED - CNS upload to R2 works correctly")
    else:
        print("TEST FAILED - Check error messages above")
    print("=" * 60)
