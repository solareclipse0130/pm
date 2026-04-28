$ContainerName = "pm-mvp"

$Existing = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $ContainerName }
if ($Existing) {
    docker rm -f $ContainerName | Out-Null
    Write-Output "Stopped $ContainerName"
} else {
    Write-Output "$ContainerName is not running"
}
