$ErrorActionPreference = 'Stop'
$stockRoot = Split-Path -Parent $PSScriptRoot
$stockLocalDirectory = Join-Path $stockRoot '.local'
$stockKeyFile = Join-Path $stockLocalDirectory 'stock.env'

try {
    Set-Location -LiteralPath $stockRoot
    Write-Host 'STOCK - local stock research screener' -ForegroundColor Cyan
    Write-Host 'Checking Docker Desktop...'
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Install Docker Desktop from https://www.docker.com/products/docker-desktop/ and open it. Then run Start STOCK.bat again.'
    }
    & docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Open Docker Desktop and wait until its engine is running. Then run Start STOCK.bat again.'
    }
    & docker compose version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Compose is unavailable. Install or update Docker Desktop, then try again.'
    }

    if (-not (Test-Path -LiteralPath (Join-Path $stockRoot '.env'))) {
        Copy-Item -LiteralPath (Join-Path $stockRoot '.env.example') -Destination (Join-Path $stockRoot '.env')
    }
    if (-not (Test-Path -LiteralPath $stockLocalDirectory)) {
        New-Item -ItemType Directory -Path $stockLocalDirectory | Out-Null
    }
    if (-not (Test-Path -LiteralPath $stockKeyFile)) {
        $stockPlainKey = $env:MASSIVE_API_KEY
        if ([string]::IsNullOrWhiteSpace($stockPlainKey)) {
            Write-Host 'Enter your Massive API key here. It is hidden while you type.'
            $stockSecureKey = Read-Host 'Massive API key' -AsSecureString
            $stockPlainKey = [System.Net.NetworkCredential]::new('', $stockSecureKey).Password
        }
        $stockPlainKey = $stockPlainKey.Trim()
        if ([string]::IsNullOrWhiteSpace($stockPlainKey) -or $stockPlainKey -match "[\r\n']") {
            throw 'Paste only your Massive API key, without quotes or a Bearer prefix, then try again.'
        }
        $stockKeyContents = "MASSIVE_API_KEY='$stockPlainKey'" + [Environment]::NewLine
        [System.IO.File]::WriteAllText($stockKeyFile, $stockKeyContents, [System.Text.UTF8Encoding]::new($false))
        $stockPlainKey = $null
        $stockKeyContents = $null
        $stockSecureKey = $null
        Write-Host 'Key saved on this computer in .local\stock.env. Keep that file private.'
    }

    $stockComposeArguments = @(
        'compose', '--project-name', 'stock-local',
        '--env-file', $stockKeyFile,
        '--file', (Join-Path $stockRoot 'compose.yaml'),
        '--file', (Join-Path $stockRoot 'compose.local.yaml')
    )
    Write-Host 'Starting the database, stock-data backend and website. The first build can take several minutes.'
    & docker @stockComposeArguments up --build --detach --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker could not start the screener. Read the Docker error above. Ports 3000 and 8000 must be free. Your database has not been deleted.'
    }

    $stockWebsiteReady = $false
    for ($stockAttempt = 0; $stockAttempt -lt 30; $stockAttempt++) {
        try {
            $stockHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/web-health' -TimeoutSec 3
            if ($stockHealth.status -eq 'ok') {
                $stockWebsiteReady = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $stockWebsiteReady) {
        throw 'The website is still starting. Leave Docker Desktop open and run Start STOCK.bat again shortly.'
    }

    Write-Host 'Opening the screener in your browser.' -ForegroundColor Green
    Start-Process 'http://127.0.0.1:3000'
    Write-Host 'The first real-stock download takes several minutes. Reload the page after it finishes.'
    Write-Host 'The app keeps running after this window closes. Keep Docker Desktop open.'
    Write-Host 'Use Stop STOCK.bat to stop the app. Your database is kept for the next launch.'
    exit 0
} catch {
    Write-Host ''
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
