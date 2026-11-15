$ErrorActionPreference = 'Stop'
$ProjectId = 'spaceline-87f04'
Set-Location -LiteralPath $PSScriptRoot

Write-Host ''
Write-Host 'SPACELINE - QUICK SETUP' -ForegroundColor Cyan
Write-Host '-----------------------'

if (-not (Test-Path -LiteralPath '.env')) {
    if (Test-Path -LiteralPath '.env.example') {
        Copy-Item '.env.example' '.env'
        Write-Host 'Created .env from the template.' -ForegroundColor Yellow
    }
    Write-Host 'Your Firebase web settings are not in .env yet. Add the values you copied from Firebase Console, save .env, then run QUICK_SETUP.bat again.' -ForegroundColor Yellow
    exit 1
}

# Reuse an already provisioned local key on subsequent launches.
$SecretDir = Join-Path $env:LOCALAPPDATA 'Spaceline\secrets'
$KeyPath = Join-Path $SecretDir 'firebase-admin.json'
if (-not (Test-Path -LiteralPath $KeyPath)) {
    Write-Host ''
    Write-Host 'One Google approval is still required: create a Firebase Admin key for this project.' -ForegroundColor Yellow
    Write-Host 'A browser tab will open. Sign in to Google if asked, then choose Project settings > Service accounts > Generate new private key.'
    Write-Host 'This is a service-account download; do not enter payment or bank details.'
    Start-Process 'https://console.firebase.google.com/project/spaceline-87f04/settings/serviceaccounts/adminsdk'

    $downloadDir = Join-Path $env:USERPROFILE 'Downloads'
    $deadline = (Get-Date).AddSeconds(150)
    $found = $null
    Write-Host ''
    Write-Host 'Waiting for the project JSON key to appear in your Downloads folder (up to 2.5 minutes)...'
    while ((Get-Date) -lt $deadline -and -not $found) {
        if (Test-Path -LiteralPath $downloadDir) {
            foreach ($file in (Get-ChildItem -LiteralPath $downloadDir -Filter '*.json' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)) {
                try {
                    $data = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
                    if ($data.type -eq 'service_account' -and $data.project_id -eq $ProjectId -and $data.private_key) {
                        $found = $file
                        break
                    }
                } catch { }
            }
        }
        if (-not $found) { Start-Sleep -Seconds 2 }
    }
    if (-not $found) {
        Write-Host 'No matching key was detected. Download the JSON key to your normal Downloads folder and run QUICK_SETUP.bat again.' -ForegroundColor Red
        exit 1
    }

    New-Item -ItemType Directory -Force -Path $SecretDir | Out-Null
    Move-Item -LiteralPath $found.FullName -Destination $KeyPath -Force
    Write-Host 'Firebase key saved outside the project folder.' -ForegroundColor Green
}

$env:GOOGLE_APPLICATION_CREDENTIALS = $KeyPath
$env:GOOGLE_CLOUD_PROJECT = $ProjectId

if (-not (Test-Path -LiteralPath 'start.bat')) {
    Write-Host 'Could not find start.bat. Extract these quick-setup files into the main Spaceline project folder.' -ForegroundColor Red
    exit 1
}

Write-Host ''
Write-Host 'Launching Spaceline. Leave this window open while using it.' -ForegroundColor Green
& $env:ComSpec /d /c 'call start.bat'
exit $LASTEXITCODE
