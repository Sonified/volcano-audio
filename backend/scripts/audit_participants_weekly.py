#!/usr/bin/env python3
import boto3
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
    region_name="auto"
)

prefix = "volcano-audio-anonymized-data/participants/"
response = s3.list_objects_v2(Bucket=os.getenv("R2_BUCKET_NAME"), Prefix=prefix, Delimiter="/")

participants = []
if "CommonPrefixes" in response:
    for p in response["CommonPrefixes"]:
        pid = p["Prefix"].split("/")[-2]
        if pid.startswith("R_") and len(pid) > 5 and "robert" not in pid.lower() and "test" not in pid.lower():
            participants.append(pid)

print("=" * 100)
print(f"PARTICIPANT DATA AUDIT - {len(participants)} real participants")
print("=" * 100)
print()
print(f"{'Participant ID':<25} | {'Status Tracker (claimed)':<35} | Submissions")
print("-" * 100)

results = []
for pid in sorted(participants):
    # Get status
    try:
        resp = s3.get_object(Bucket=os.getenv("R2_BUCKET_NAME"), Key=f"volcano-audio-anonymized-data/participants/{pid}/user-status/status.json")
        status = json.loads(resp["Body"].read().decode("utf-8"))
        # Check studyProgress first (nested), then top-level
        progress = status.get("studyProgress", {})
        tracker_raw = progress.get("sessionCompletionTracker") or status.get("sessionCompletionTracker")
        # It might be double-encoded as a string
        if isinstance(tracker_raw, str):
            tracker = json.loads(tracker_raw)
        else:
            tracker = tracker_raw
    except:
        tracker = None

    # Get submissions
    sub_resp = s3.list_objects_v2(Bucket=os.getenv("R2_BUCKET_NAME"), Prefix=f"volcano-audio-anonymized-data/participants/{pid}/submissions/")
    subs = len(sub_resp.get("Contents", []))

    if tracker:
        w1 = tracker.get("week1", [False, False])
        w2 = tracker.get("week2", [False, False])
        w3 = tracker.get("week3", [False, False])
        # Show as "W1: 2/2" meaning "2 sessions complete out of 2"
        w1_count = (1 if w1[0] else 0) + (1 if w1[1] else 0)
        w2_count = (1 if w2[0] else 0) + (1 if w2[1] else 0)
        w3_count = (1 if w3[0] else 0) + (1 if w3[1] else 0)
        claimed = f"W1:{w1_count}/2  W2:{w2_count}/2  W3:{w3_count}/2"
        total = w1_count + w2_count + w3_count
    else:
        claimed = "No tracker"
        total = 0

    mismatch = " !!MISMATCH" if total != subs else ""
    print(f"{pid:<25} | {claimed:<35} | {subs}{mismatch}")
    results.append({"tracker": tracker, "subs": subs})

print()
print("=" * 100)
w1s1 = sum(1 for r in results if r["tracker"] and r["tracker"].get("week1", [0, 0])[0])
w1s2 = sum(1 for r in results if r["tracker"] and r["tracker"].get("week1", [0, 0])[1])
w2s1 = sum(1 for r in results if r["tracker"] and r["tracker"].get("week2", [0, 0])[0])
w2s2 = sum(1 for r in results if r["tracker"] and r["tracker"].get("week2", [0, 0])[1])
w3s1 = sum(1 for r in results if r["tracker"] and r["tracker"].get("week3", [0, 0])[0])
w3s2 = sum(1 for r in results if r["tracker"] and r["tracker"].get("week3", [0, 0])[1])
print(f"CLAIMED (from status.json): W1=[{w1s1},{w1s2}] W2=[{w2s1},{w2s2}] W3=[{w3s1},{w3s2}]")
print(f"ACTUAL SUBMISSIONS ON R2: {sum(r['subs'] for r in results)}")

# Now show detailed breakdown by date
print()
print("=" * 100)
print("DETAILED SUBMISSION BREAKDOWN")
print("=" * 100)

from datetime import datetime

STUDY_START = datetime(2025, 11, 18)  # Tuesday Nov 18

for pid in sorted(participants):
    sub_resp = s3.list_objects_v2(Bucket=os.getenv("R2_BUCKET_NAME"), Prefix=f"volcano-audio-anonymized-data/participants/{pid}/submissions/")
    subs = sub_resp.get("Contents", [])

    print(f"\n{pid}:")
    weeks = {1: 0, 2: 0, 3: 0}
    for sub in sorted(subs, key=lambda x: x["LastModified"]):
        modified = sub["LastModified"].replace(tzinfo=None)
        days_since_start = (modified - STUDY_START).days
        week = min(3, max(1, (days_since_start // 7) + 1))
        weeks[week] += 1
        print(f"  {modified.strftime('%Y-%m-%d %H:%M')} (Week {week})")
    print(f"  TOTALS: W1={weeks[1]}, W2={weeks[2]}, W3={weeks[3]}")

print()
print("=" * 100)
print("GRAND TOTALS BY WEEK")
print("=" * 100)
grand_weeks = {1: 0, 2: 0, 3: 0}
for pid in participants:
    sub_resp = s3.list_objects_v2(Bucket=os.getenv("R2_BUCKET_NAME"), Prefix=f"volcano-audio-anonymized-data/participants/{pid}/submissions/")
    for sub in sub_resp.get("Contents", []):
        modified = sub["LastModified"].replace(tzinfo=None)
        days_since_start = (modified - STUDY_START).days
        week = min(3, max(1, (days_since_start // 7) + 1))
        grand_weeks[week] += 1

print(f"Week 1 submissions on R2: {grand_weeks[1]}")
print(f"Week 2 submissions on R2: {grand_weeks[2]}")
print(f"Week 3 submissions on R2: {grand_weeks[3]}")
