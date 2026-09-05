# CodeFlow 本地开发环境启动脚本（重启电脑后一键恢复）
# 用法: powershell -File scripts/start-all.ps1
# 前置: docker compose up -d (postgres/redis/kafka)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root ".logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (-not (Test-Path (Join-Path $root ".env"))) {
    Write-Host "ERROR: .env not found. Copy .env.example to .env and set SECRET_KEY." -ForegroundColor Red
    exit 1
}
# 读取 .env 中的 SECRET_KEY
$secKey = (Get-Content (Join-Path $root ".env") | Where-Object { $_ -match "^SECRET_KEY=" }) -replace "^SECRET_KEY=", ""
if (-not $secKey -or $secKey -match "change-me") {
    Write-Host "ERROR: set a real SECRET_KEY in .env" -ForegroundColor Red
    exit 1
}

$services = @(
    @("user-service", "user_service", "8001"),
    @("project-service", "project_service", "8002"),
    @("notification-service", "notification_service", "8003"),
    @("ci-service", "ci_service", "8004"),
    @("ai-service", "ai_service", "8005"),
    @("gateway-service", "gateway_service", "8000")
)

# 先停掉已有实例
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "main:app" -and $_.Name -match "python|uvicorn" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

foreach ($item in $services) {
    $name = $item[0]; $pkg = $item[1]; $port = $item[2]
    $cmd = "@echo off`r`nset KAFKA_ENABLED=true`r`nset KAFKA_BOOTSTRAP_SERVERS=localhost:9092`r`nset SECRET_KEY=$secKey`r`nset RATE_LIMIT_PER_MINUTE=10000`r`ncd /d $root\services\$name`r`nuv run uvicorn $pkg.main:app --port $port > $logDir\$name.log 2>&1`r`n"
    $scriptPath = Join-Path $logDir "start-$name.cmd"
    [System.IO.File]::WriteAllText($scriptPath, $cmd)
    Start-Process -FilePath $scriptPath -WindowStyle Hidden
    Write-Host "started $name on :$port"
}

Write-Host "waiting for services..."
Start-Sleep -Seconds 18
foreach ($item in $services) {
    $port = $item[2]
    try {
        $h = Invoke-RestMethod "http://localhost:$port/health" -TimeoutSec 3
        Write-Host "port ${port}: $($h.service)" -ForegroundColor Green
    } catch {
        Write-Host "port ${port}: DOWN (see .logs\$($item[0]).log)" -ForegroundColor Red
    }
}
Write-Host "gateway: http://localhost:8000/docs"
