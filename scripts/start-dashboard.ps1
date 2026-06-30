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
  # Native commands (git/npm) write normal progress to stderr. Under Windows
  # PowerShell with $ErrorActionPreference = "Stop", capturing that stderr via
  # PowerShell redirection is treated as a terminating error, so we route these
  # calls through cmd.exe, which redirects both streams to the log itself.
  if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Log "Checking latest GitHub changes."
    cmd /c "git pull --ff-only origin main >> `"$LogPath`" 2>&1"
  } else {
    Write-Log "Git was not found. Skipping GitHub update."
  }

  if (Test-Path (Join-Path $ProjectRoot "package-lock.json")) {
    Write-Log "Installing dependencies with npm ci."
    cmd /c "npm ci >> `"$LogPath`" 2>&1"
  } else {
    Write-Log "Installing dependencies with npm install."
    cmd /c "npm install >> `"$LogPath`" 2>&1"
  }

  Write-Log "Launching local server."
  cmd /c "npm start >> `"$LogPath`" 2>&1"
} catch {
  Write-Log ("Startup failed: " + $_.Exception.Message)
  throw
}
