$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$uiPath = Join-Path $repoRoot "yu_test1\index.html"

function Get-PythonCandidatePaths {
    $paths = New-Object System.Collections.Generic.List[string]
    $seen = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)

    function Add-CandidatePath {
        param([string]$Path)

        if ([string]::IsNullOrWhiteSpace($Path)) {
            return
        }

        if ($seen.Add($Path)) {
            $paths.Add($Path)
        }
    }

    $candidateRoots = @($repoRoot)
    $parentRoot = Split-Path -Parent $repoRoot
    if (-not [string]::IsNullOrWhiteSpace($parentRoot) -and $parentRoot -ne $repoRoot) {
        $candidateRoots += $parentRoot
    }

    if ($env:VIRTUAL_ENV) {
        Add-CandidatePath (Join-Path $env:VIRTUAL_ENV "Scripts\python.exe")
    }

    foreach ($root in $candidateRoots) {
        Add-CandidatePath (Join-Path $root ".venv\Scripts\python.exe")
        Add-CandidatePath (Join-Path $root "dyp\Scripts\python.exe")
    }

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

if (-not $pythonExe) {
    $attempted = (Get-PythonCandidatePaths | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join ", "
    Show-Failure "No repo Python environment found. Tried: $attempted"
}

if (-not (Test-Path $uiPath)) {
    Show-Failure "Missing yu_test1\index.html. Run this script from the repository root."
}

$escapedPythonExe = $pythonExe.Replace("'", "''")
$trackerCommand = "Set-Location -LiteralPath '$repoRoot'; & '$escapedPythonExe' -m runner.run_live_tracker"

Write-Host "Starting live demo services..." -ForegroundColor Cyan
Write-Host "Using Python: $pythonExe" -ForegroundColor DarkGray

Start-PowerShellWindow -WorkingDirectory $repoRoot -Command $trackerCommand
Start-Process $uiPath

Write-Host "Browser opened at $uiPath" -ForegroundColor Green
