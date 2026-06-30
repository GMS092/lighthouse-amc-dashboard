$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$LogDir = Join-Path $ProjectRoot "logs"
$LogPath = Join-Path $LogDir "startup.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
  param([string]$Message)
  $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $LogPath -Value "[$Timestamp] $Message" -Encoding UTF8
}

Set-Location $ProjectRoot
Write-Log "Starting Lighthouse AMC dashboard startup flow."

try {
  if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Log "Checking latest GitHub changes."
    git pull --ff-only origin main *>> $LogPath
  } else {
    Write-Log "Git was not found. Skipping GitHub update."
  }

  if (Test-Path (Join-Path $ProjectRoot "package-lock.json")) {
    Write-Log "Installing dependencies with npm ci."
    npm ci *>> $LogPath
  } else {
    Write-Log "Installing dependencies with npm install."
    npm install *>> $LogPath
  }

  Write-Log "Launching local server."
  npm start *>> $LogPath
} catch {
  Write-Log ("Startup failed: " + $_.Exception.Message)
  throw
}
