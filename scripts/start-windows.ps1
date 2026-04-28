$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$ImageName = "pm-mvp"
$ContainerName = "pm-mvp"
$Port = if ($env:PORT) { $env:PORT } else { "9000" }

Set-Location $RootDir

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
    docker run -d --name $ContainerName -p "${Port}:8000" @EnvArgs $ImageName
} finally {
    if ($TempEnvFile) {
        Remove-Item $TempEnvFile -ErrorAction SilentlyContinue
    }
}

Write-Output "Server running at http://localhost:$Port"
