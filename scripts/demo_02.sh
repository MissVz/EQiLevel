#!/usr/bin/env bash
# scripts/demo_day2.sh
set -euo pipefail
BASE="http://127.0.0.1:8000"
S="s3"

echo -e "\n=== Health ==="
curl -s "$BASE/api/v1/health/full" | jq

echo -e "\n=== Seed narrative ==="
curl -sX POST "$BASE/session" -H "Content-Type: application/json" -d "{\"user_text\":\"This is tough and I feel stuck.\",\"session_id\":\"$S\"}" | jq
curl -sX POST "$BASE/session" -H "Content-Type: application/json" -d "{\"user_text\":\"Okay, I think I understand this now.\",\"session_id\":\"$S\"}" | jq
curl -sX POST "$BASE/session" -H "Content-Type: application/json" -d "{\"user_text\":\"This is dragging. Can we speed up?\",\"session_id\":\"$S\"}" | jq
curl -sX POST "$BASE/session" -H "Content-Type: application/json" -d "{\"user_text\":\"Got it - ready for a challenge.\",\"session_id\":\"$S\"}" | jq
curl -sX POST "$BASE/session" -H "Content-Type: application/json" -d "{\"user_text\":\"Give me one more challenge.\",\"session_id\":\"$S\"}" | jq

echo -e "\n=== Metrics (session=$S, 24h) ==="
curl -s "$BASE/api/v1/metrics?session_id=$S&since_hours=24" | jq

echo -e "\n=== Admin summary (24h) ==="
curl -s "$BASE/api/v1/admin/summary?since_hours=24" | jq
