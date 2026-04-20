$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $repoRoot "react_frontend"
$nodeModulesDir = Join-Path $frontendDir "node_modules"
$nodeBinDir = Join-Path $nodeModulesDir ".bin"
$trackerScript = Join-Path $repoRoot "scripts\run-live-tracker.cjs"
$uiUrl = "http://localhost:5173"

function Get-PythonCandidatePaths {
    $paths = New-Object System.Collections.Generic.List[string]

    if ($env:VIRTUAL_ENV) {
        $paths.Add((Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"))
    }

    $paths.Add((Join-Path $repoRoot ".venv\Scripts\python.exe"))
    $paths.Add((Join-Path $repoRoot "dyp\Scripts\python.exe"))

    return $paths
}

function Resolve-PythonExecutable {
    foreach ($candidate in Get-PythonCandidatePaths) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        if (-not (Test-Path $candidate)) {
            continue
        }

        try {
            $null = & $candidate --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
            continue
        }
    }

    return $null
}

function Show-Failure {
    param([string]$Message)

    Write-Host ""
    Write-Host "[launch_live_demo] $Message" -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 1
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            return $true
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    return $false
}

function Start-PowerShellWindow {
    param(
        [string]$WorkingDirectory,
        [string]$Command
    )

    $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    Start-Process -FilePath "powershell.exe" -WorkingDirectory $WorkingDirectory -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", $encodedCommand
    )
}

$pythonExe = Resolve-PythonExecutable

if (-not (Test-Path $frontendDir)) {
    Show-Failure "Missing react_frontend folder. Run this script from the repository root."
}

if (-not $pythonExe) {
    $attempted = (Get-PythonCandidatePaths | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join ", "
    Show-Failure "No repo Python environment found. Tried: $attempted"
}

if (-not (Test-Path $nodeModulesDir)) {
    Show-Failure "Missing react_frontend\node_modules. Run npm install in react_frontend first."
}

$concurrentlyCmd = Join-Path $nodeBinDir "concurrently.cmd"
$viteCmd = Join-Path $nodeBinDir "vite.cmd"

if (-not (Test-Path $viteCmd)) {
    Show-Failure "Missing Vite binary in react_frontend\node_modules\.bin. Run npm install in react_frontend first."
}

if (-not (Test-Path $trackerScript)) {
    Show-Failure "Missing scripts\run-live-tracker.cjs. The live launcher cannot start."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Show-Failure "npm was not found in PATH. Install Node.js first."
}

$escapedPythonExe = $pythonExe.Replace("'", "''")

# Test-friendly defaults:
# - DYP_FREE_MOVE=1 removes pathfinding constraints for move_unit (free placement).
#   You can override by setting DYP_FREE_MOVE=0 in the environment before launching.
if (-not $env:DYP_FREE_MOVE) {
    $env:DYP_FREE_MOVE = "1"
}

$devLiveCommand = "`$env:DEFEND_YOUR_PIXELS_PYTHON = '$escapedPythonExe'; `$env:DYP_FREE_MOVE = '$($env:DYP_FREE_MOVE)'; Set-Location -LiteralPath '$frontendDir'; npm run dev:live"
$viteCommand = "`$env:DYP_FREE_MOVE = '$($env:DYP_FREE_MOVE)'; Set-Location -LiteralPath '$frontendDir'; npm run dev"
$trackerCommand = "`$env:DYP_FREE_MOVE = '$($env:DYP_FREE_MOVE)'; Set-Location -LiteralPath '$repoRoot'; & '$escapedPythonExe' -m runner.run_live_tracker"

Write-Host "Starting live demo services..." -ForegroundColor Cyan
Write-Host "Using Python: $pythonExe" -ForegroundColor DarkGray

if (Test-Path $concurrentlyCmd) {
    Start-PowerShellWindow -WorkingDirectory $frontendDir -Command $devLiveCommand
} else {
    Write-Host "concurrently not found. Starting frontend and tracker in separate windows." -ForegroundColor Yellow
    Start-PowerShellWindow -WorkingDirectory $frontendDir -Command $viteCommand
    Start-PowerShellWindow -WorkingDirectory $repoRoot -Command $trackerCommand
}

Write-Host "Waiting for UI at $uiUrl ..." -ForegroundColor Cyan
if (Wait-ForUrl -Url $uiUrl) {
    Start-Process $uiUrl
    Write-Host "Browser opened at $uiUrl" -ForegroundColor Green
} else {
    Write-Host "UI did not respond in time. Open $uiUrl manually after the dev server finishes starting." -ForegroundColor Yellow
}
