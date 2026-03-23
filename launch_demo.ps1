$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

$pythonExe = $null
$localVenv = Join-Path $projectDir ".venv\Scripts\python.exe"

if (Test-Path $localVenv) {
    $pythonExe = $localVenv
}

if (-not $pythonExe) {
    $desktopDir = [Environment]::GetFolderPath("Desktop")
    $candidateDirs = Get-ChildItem -Path $desktopDir -Directory -ErrorAction SilentlyContinue
    foreach ($dir in $candidateDirs) {
        $candidate = Join-Path $dir.FullName ".venv\Scripts\python.exe"
        if (Test-Path $candidate) {
            $pythonExe = $candidate
            break
        }
    }
}

if (-not $pythonExe) {
    Write-Host "No usable Python virtual environment was found." -ForegroundColor Red
    Write-Host "Please prepare .venv for this project or keep another Desktop project venv available." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

$envFile = Join-Path $projectDir ".env"
$envExample = Join-Path $projectDir ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile -Force
}

Write-Host "Starting Education AI Demo..." -ForegroundColor Cyan
Start-Process -FilePath $pythonExe -ArgumentList @(
    "-m",
    "uvicorn",
    "backend.app:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
    "--reload"
) -WorkingDirectory $projectDir

Start-Sleep -Seconds 2
try {
    Start-Process "http://127.0.0.1:8000"
} catch {
    Write-Host "Server started. Open http://127.0.0.1:8000 manually if the browser did not open." -ForegroundColor Yellow
}
