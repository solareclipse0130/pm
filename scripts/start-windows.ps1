# Windows PowerShell entry point for the local Docker app.
# Docker Desktop on Windows abstracts host UID/GID so the image is built with
# its default APP_UID/APP_GID and bind mounts work via the WSL/Hyper-V layer.

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$ImageName = "pm-mvp"
$ContainerName = "pm-mvp"
$Port = if ($env:PORT) { $env:PORT } else { "9000" }
$DataDir = Join-Path $RootDir "data"

Set-Location $RootDir
New-Item -ItemType Directory -Force $DataDir | Out-Null

docker build -t $ImageName .

$Existing = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $ContainerName }
if ($Existing) {
    docker rm -f $ContainerName | Out-Null
}

$EnvArgs = @()
$TempEnvFile = $null
$EnvFile = Join-Path $RootDir ".env"
if (Test-Path $EnvFile) {
    $TempEnvFile = [System.IO.Path]::GetTempFileName()
    Get-Content $EnvFile |
        Where-Object { $_ -match "\S" -and $_ -notmatch "^\s*#" -and $_.Contains("=") } |
        ForEach-Object {
            $Index = $_.IndexOf("=")
            $Key = $_.Substring(0, $Index).Trim()
            $Value = $_.Substring($Index + 1).Trim()
            if ($Key) { "$Key=$Value" }
        } |
        Set-Content $TempEnvFile
    $EnvArgs = @("--env-file", $TempEnvFile)
}

try {
    docker run -d --name $ContainerName -p "${Port}:8000" -v "${DataDir}:/app/data" @EnvArgs $ImageName | Out-Null
} finally {
    if ($TempEnvFile) {
        Remove-Item $TempEnvFile -ErrorAction SilentlyContinue
    }
}

# Wait for the FastAPI health endpoint before declaring the server ready.
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:${Port}/api/health" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # Not ready yet.
    }
    Start-Sleep -Milliseconds 500
}

if ($ready) {
    Write-Output "Server running at http://localhost:$Port"
} else {
    Write-Error "Container started but /api/health did not respond within 30s. Check 'docker logs $ContainerName'."
    exit 1
}
