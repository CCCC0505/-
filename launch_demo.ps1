$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

$serverUrl = "http://127.0.0.1:8000"
$healthUrl = "$serverUrl/api/ui/subjects?school_type=初中"

function Test-PythonCandidate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Candidate
    )

    if (-not (Test-Path $Candidate)) {
        return $false
    }

    try {
        & $Candidate -c "from backend.app import app; print(app.title)" 1>$null 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Get-PythonCandidates {
    $candidates = New-Object System.Collections.Generic.List[string]

    $localVenv = Join-Path $projectDir ".venv\Scripts\python.exe"
    if (Test-Path $localVenv) {
        $candidates.Add($localVenv)
    }

    $systemPython = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
    if ($systemPython) {
        $candidates.Add($systemPython)
    }

    $desktopDir = [Environment]::GetFolderPath("Desktop")
    $candidateDirs = Get-ChildItem -Path $desktopDir -Directory -ErrorAction SilentlyContinue
    foreach ($dir in $candidateDirs) {
        $candidate = Join-Path $dir.FullName ".venv\Scripts\python.exe"
        if (Test-Path $candidate) {
            $candidates.Add($candidate)
        }
    }

    return $candidates | Select-Object -Unique
}

function Wait-ServerReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSeconds = 15
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            return $true
        } catch {
            Start-Sleep -Milliseconds 800
        }
    }

    return $false
}

$pythonExe = $null
foreach ($candidate in Get-PythonCandidates) {
    if (Test-PythonCandidate -Candidate $candidate) {
        $pythonExe = $candidate
        break
    }
}

if (-not $pythonExe) {
    Write-Host "No usable Python runtime was found for this demo." -ForegroundColor Red
    Write-Host "Please prepare .venv or ensure the current python can import backend.app." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

$envFile = Join-Path $projectDir ".env"
$envExample = Join-Path $projectDir ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile -Force
}

if (Wait-ServerReady -Url $healthUrl -TimeoutSeconds 2) {
    Write-Host "Demo server is already running. Opening browser..." -ForegroundColor Green
    try {
        Start-Process $serverUrl
    } catch {
        Write-Host "Browser could not be opened automatically. Visit $serverUrl manually." -ForegroundColor Yellow
    }
    exit 0
}

Write-Host "Using Python: $pythonExe" -ForegroundColor Cyan
Write-Host "Starting Education AI Demo..." -ForegroundColor Cyan

$serverProcess = Start-Process -FilePath $pythonExe -ArgumentList @(
    "-m",
    "uvicorn",
    "backend.app:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000"
) -WorkingDirectory $projectDir -PassThru

if (Wait-ServerReady -Url $healthUrl -TimeoutSeconds 15) {
    Write-Host "Server started successfully. Opening browser..." -ForegroundColor Green
    try {
        Start-Process $serverUrl
    } catch {
        Write-Host "Browser could not be opened automatically. Visit $serverUrl manually." -ForegroundColor Yellow
    }
    exit 0
}

Write-Host "The demo server did not become ready in time." -ForegroundColor Red
if ($serverProcess -and $serverProcess.HasExited) {
    Write-Host "The Python process exited immediately." -ForegroundColor Yellow
} else {
    Write-Host "The Python process is still running, but the page is not responding yet." -ForegroundColor Yellow
}

Write-Host "You can try running this manually in the project directory:" -ForegroundColor Yellow
Write-Host "$pythonExe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000" -ForegroundColor White
Read-Host "Press Enter to exit"
exit 1
