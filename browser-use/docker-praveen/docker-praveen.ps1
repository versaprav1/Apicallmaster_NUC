# Docker run helper for Browser-Use (Windows PowerShell)
# @file purpose: Provide a reusable script to run the browser-use Docker image with many LLM API keys.
#
# What this file does:
# - Reads API keys from a .env file (if present) and/or interactive prompts/params
# - Constructs a docker run command with all relevant -e KEY=... env vars
# - Mounts a local data directory to /data and sets recommended flags
#
# How it fits into the system:
# - Convenience launcher for the containerized CLI entrypoint `browser-use`
# - Keeps your secrets local and avoids repeating long commands
#
# Usage examples (PowerShell):
#   ./docker-praveen.ps1
#   ./docker-praveen.ps1 -ImageName browseruse -DataDir "${PWD}\data" -ShmSize "2g"
#   ./docker-praveen.ps1 -NoPrompt  # uses only values from .env and defaults
#
# Notes:
# - Place a .env file in the repository root with KEY=VALUE lines (no quotes)
# - This script ignores comment lines starting with '#'

param(
	[string]$ImageName = "browseruse",
	[string]$DataDir = "${PWD}\data",
	[string]$ShmSize = "2g",
	[switch]$NoPrompt
)

# Ensure data directory and subdirectories exist
if (-not (Test-Path -LiteralPath $DataDir)) {
	New-Item -ItemType Directory -Path $DataDir | Out-Null
}
$profilesDir = Join-Path $DataDir "profiles"
if (-not (Test-Path -LiteralPath $profilesDir)) {
	New-Item -ItemType Directory -Path $profilesDir | Out-Null
}
$defaultProfileDir = Join-Path $profilesDir "default"
if (-not (Test-Path -LiteralPath $defaultProfileDir)) {
	New-Item -ItemType Directory -Path $defaultProfileDir | Out-Null
}

# Known env keys supported by browser-use LLM integrations
$knownKeys = @(
	"OPENAI_API_KEY",
	"ANTHROPIC_API_KEY",
	"AZURE_OPENAI_ENDPOINT",
	"AZURE_OPENAI_KEY",
	"GOOGLE_API_KEY",
	"DEEPSEEK_API_KEY",
	"GROQ_API_KEY",
	"GROK_API_KEY",
	"NOVITA_API_KEY",
	"OPENROUTER_API_KEY",
	"BROWSERBASE_API_KEY",
	"POSTHOG_API_KEY",
	"POSTHOG_HOST"
)

# Load .env if present (simple KEY=VALUE parser)
$envMap = @{}
$envPath = Join-Path -Path $PSScriptRoot -ChildPath ".env"
if (Test-Path -LiteralPath $envPath) {
	Get-Content -LiteralPath $envPath | ForEach-Object {
		$line = $_.Trim()
		if (-not $line) { return }
		if ($line.StartsWith('#')) { return }
		$eq = $line.IndexOf('=')
		if ($eq -gt 0) {
			$key = $line.Substring(0, $eq).Trim()
			$value = $line.Substring($eq + 1).Trim()
			if ($key) { $envMap[$key] = $value }
		}
	}
}

# Merge with current process env (prefer .env values)
foreach ($k in $knownKeys) {
	$envValue = [System.Environment]::GetEnvironmentVariable($k)
	if (-not $envMap.ContainsKey($k) -and $envValue) {
		$envMap[$k] = $envValue
	}
}

# Prompt for missing keys unless -NoPrompt is set
if (-not $NoPrompt) {
	foreach ($k in $knownKeys) {
		if (-not $envMap.ContainsKey($k) -or [string]::IsNullOrWhiteSpace($envMap[$k])) {
			$val = Read-Host -Prompt "Enter $k (optional, press Enter to skip)"
			if ($val) { $envMap[$k] = $val }
		}
	}
}

# Build docker run arguments
$envArgs = @()
foreach ($pair in $envMap.GetEnumerator()) {
	if (-not [string]::IsNullOrWhiteSpace($pair.Value)) {
		$envArgs += @('-e', "$($pair.Key)=$($pair.Value)")
	}
}

# Final command
$cmd = @(
	'docker', 'run', '--rm', '-it',
	'--user', 'root',
	"--shm-size=$ShmSize",
	'-p', '9242:9242', '-p', '9222:9222',
	'-v', (($DataDir + ":/data") -replace "\\", "/" )
) + $envArgs + @(
	$ImageName
)

Write-Host "Running:" -ForegroundColor Cyan
Write-Host ("`n" + ($cmd -join ' ') + "`n") -ForegroundColor Yellow

# Execute
& $cmd[0] $cmd[1..($cmd.Count-1)]
