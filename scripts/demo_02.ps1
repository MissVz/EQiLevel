# scripts/demo_day2.ps1
# EQiLevel Day 2 Demo – deterministic run you can show live

$base = "http://127.0.0.1:8000"
$session = "s3"   # change if needed
$H = @{ "Content-Type" = "application/json" }

function Show($title, $data) {
  Write-Host "`n=== $title ==="
  $data | ConvertTo-Json -Depth 6
}

# 0) Health
$health = Invoke-RestMethod -Uri "$base/api/v1/health/full"
Show "Health" $health

# 1) Seed a short narrative with emotions & correctness
$turns = @(
  @{ user_text = "This is tough and I feel stuck."; session_id = $session },     # frustrated -> warm, down/slow
  @{ user_text = "Okay, I think I understand this now."; session_id = $session },# calm -> neutral, hold
  @{ user_text = "This is dragging. Can we speed up?"; session_id = $session },  # bored -> concise/fast (if modeled)
  @{ user_text = "Got it - ready for a challenge."; session_id = $session },     # engaged + correct -> encouraging, up/fast
  @{ user_text = "Give me one more challenge."; session_id = $session }          # engaged -> up (if reward trend supports)
)

foreach ($t in $turns) {
  $resp = Invoke-RestMethod -Method Post -Uri "$base/session" -Headers $H -Body ($t | ConvertTo-Json)
  Show "Session turn: $($t.user_text)" $resp
  Start-Sleep -Milliseconds 300
}

# 2) Metrics – last 24h for the session
$metrics = Invoke-RestMethod -Uri "$base/api/v1/metrics?session_id=$session&since_hours=24"
Show "Metrics (session=$session, 24h)" $metrics

# 3) Admin summary – last 24h
$summary = Invoke-RestMethod -Uri "$base/api/v1/admin/summary?since_hours=24"
Show "Admin summary (24h)" $summary
