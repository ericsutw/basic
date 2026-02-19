
Write-Host "Starting deployment to GitHub..."

# 1. Local Verification
Write-Host "Running local verification..."
python scripts/test_notification_local.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Local verification failed! Aborting deployment."
    exit 1
}

# 2. Git Sync
Write-Host "Syncing with remote..."
git pull --rebase origin main

# 3. Add & Commit
Write-Host "Staging changes..."
git add .
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$commitMsg = "Update: $timestamp"
git commit -m "$commitMsg"

# 4. Push
Write-Host "Pushing to GitHub..."
git push origin main

Write-Host "Deployment Complete! 🚀"
