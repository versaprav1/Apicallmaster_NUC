# Start Browser-Use MCP Container (Idle Mode)
# This script starts a persistent container for browser-use MCP server.
# The container stays idle, and MCP processes are spawned via `docker exec -i` when needed.

param(
    [string]$ContainerName = "browseruse-mcp",
    [string]$ImageName = "browseruse",
    [string]$DataDir = ".\browser-use\data",
    [string]$EnvFile = ".\browser-use\docker-praveen\.env",
    [string]$ShmSize = "2g",
    [switch]$Force
)

Write-Host "Browser-Use MCP Container Setup" -ForegroundColor Cyan
Write-Host "=" * 60

# Check if container already exists
$existing = docker ps -a --filter "name=^${ContainerName}$" --format "{{.Names}}"

if ($existing -eq $ContainerName) {
    if ($Force) {
        Write-Host "Removing existing container '$ContainerName'..." -ForegroundColor Yellow
        docker rm -f $ContainerName | Out-Null
    } else {
        Write-Host "Container '$ContainerName' already exists." -ForegroundColor Yellow
        $status = docker ps --filter "name=^${ContainerName}$" --format "{{.Status}}"
        
        if ($status) {
            Write-Host "Status: $status" -ForegroundColor Green
            Write-Host ""
            Write-Host "Container is already running. You can use it with:" -ForegroundColor Green
            Write-Host "  docker exec -i $ContainerName browser-use --mcp" -ForegroundColor White
            Write-Host ""
            Write-Host "To restart: docker restart $ContainerName" -ForegroundColor Gray
            Write-Host "To stop: docker stop $ContainerName" -ForegroundColor Gray
            Write-Host "To remove: docker rm -f $ContainerName" -ForegroundColor Gray
            Write-Host ""
            Write-Host "Or run this script with -Force to recreate the container." -ForegroundColor Gray
            exit 0
        } else {
            Write-Host "Container exists but is not running. Starting it..." -ForegroundColor Yellow
            docker start $ContainerName
            Write-Host "✅ Container started!" -ForegroundColor Green
            exit 0
        }
    }
}

# Resolve paths
try {
    $DataDirResolved = (Resolve-Path $DataDir -ErrorAction Stop).Path
} catch {
    Write-Host "Creating data directory: $DataDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    $DataDirResolved = (Resolve-Path $DataDir).Path
}

try {
    $EnvFileResolved = (Resolve-Path $EnvFile -ErrorAction Stop).Path
} catch {
    Write-Host "❌ Error: .env file not found at: $EnvFile" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create a .env file with at least one LLM API key:" -ForegroundColor Yellow
    Write-Host "  OPENAI_API_KEY=sk-..." -ForegroundColor White
    Write-Host "  ANTHROPIC_API_KEY=..." -ForegroundColor White
    Write-Host "  OPENROUTER_API_KEY=..." -ForegroundColor White
    Write-Host ""
    Write-Host "See browser-use/docker-praveen/README.md for details." -ForegroundColor Gray
    exit 1
}

# Create data subdirectories if they don't exist
$profilesDir = Join-Path $DataDirResolved "profiles"
if (-not (Test-Path $profilesDir)) {
    New-Item -ItemType Directory -Path $profilesDir -Force | Out-Null
}

$defaultProfileDir = Join-Path $profilesDir "default"
if (-not (Test-Path $defaultProfileDir)) {
    New-Item -ItemType Directory -Path $defaultProfileDir -Force | Out-Null
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Container Name: $ContainerName"
Write-Host "  Image: $ImageName"
Write-Host "  Data Directory: $DataDirResolved"
Write-Host "  Env File: $EnvFileResolved"
Write-Host "  Shared Memory: $ShmSize"
Write-Host ""

# Start container in idle mode
Write-Host "Starting container in idle mode..." -ForegroundColor Yellow

$cmd = @(
    "docker", "run", "-d",
    "--name", $ContainerName,
    "--shm-size=$ShmSize",
    "--user", "root",
    "-v", "$($DataDirResolved):/data",
    "--env-file", $EnvFileResolved,
    "--entrypoint", "tail",
    $ImageName,
    "-f", "/dev/null"
)

Write-Host "Command:" -ForegroundColor Gray
Write-Host "  $($cmd -join ' ')" -ForegroundColor DarkGray
Write-Host ""

$containerId = & $cmd[0] $cmd[1..($cmd.Count-1)]

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container started successfully!" -ForegroundColor Green
    Write-Host "   Container ID: $containerId" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Verifying container status..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    
    $status = docker ps --filter "name=^${ContainerName}$" --format "{{.Status}}"
    if ($status) {
        Write-Host "✅ Container is running: $status" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Container may have stopped. Check logs:" -ForegroundColor Yellow
        Write-Host "   docker logs $ContainerName" -ForegroundColor White
        exit 1
    }
    
    Write-Host ""
    Write-Host "=" * 60
    Write-Host "🎉 Browser-Use MCP Container is Ready!" -ForegroundColor Green
    Write-Host "=" * 60
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Cyan
    Write-Host "  1. From Python code:" -ForegroundColor White
    Write-Host "     client = BrowserUseMCPClient(mode='docker', docker_container='$ContainerName')" -ForegroundColor Gray
    Write-Host "     await client.initialize()" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Manual testing:" -ForegroundColor White
    Write-Host "     docker exec -i $ContainerName browser-use --mcp" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  3. Run test script:" -ForegroundColor White
    Write-Host "     python scripts/examples/test_browser_mcp.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Management Commands:" -ForegroundColor Cyan
    Write-Host "  View logs:    docker logs $ContainerName" -ForegroundColor Gray
    Write-Host "  Stop:         docker stop $ContainerName" -ForegroundColor Gray
    Write-Host "  Restart:      docker restart $ContainerName" -ForegroundColor Gray
    Write-Host "  Remove:       docker rm -f $ContainerName" -ForegroundColor Gray
    Write-Host "  Shell access: docker exec -it $ContainerName /bin/bash" -ForegroundColor Gray
    Write-Host ""
    
} else {
    Write-Host "❌ Failed to start container" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check if image exists: docker images | Select-String $ImageName" -ForegroundColor White
    Write-Host "  2. Build image if needed: cd browser-use && docker build -t $ImageName ." -ForegroundColor White
    Write-Host "  3. Check .env file exists: $EnvFileResolved" -ForegroundColor White
    Write-Host "  4. Check Docker is running: docker ps" -ForegroundColor White
    exit 1
}


