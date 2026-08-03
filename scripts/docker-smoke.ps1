$ErrorActionPreference = 'Stop'
$frontendUrl = if ($env:FRONTEND_URL) { $env:FRONTEND_URL.TrimEnd('/') } else { 'http://localhost:5173' }

docker compose config | Out-Null
docker compose up --build -d

for ($attempt = 0; $attempt -lt 90; $attempt++) {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "$frontendUrl/healthz" -TimeoutSec 3 | Out-Null
        Invoke-WebRequest -UseBasicParsing -Uri "$frontendUrl/api/v1/health/ready/" -TimeoutSec 3 | Out-Null
        Write-Host "HamAmoz stack is ready: $frontendUrl"
        Write-Host 'Local login: admin / Admin123!ChangeMe'
        docker compose ps
        exit 0
    }
    catch {
        Start-Sleep -Seconds 2
    }
}

Write-Error 'Stack did not become ready in time.'
docker compose ps
docker compose logs --tail=120 release bootstrap web frontend db redis-cache redis-broker
exit 1
