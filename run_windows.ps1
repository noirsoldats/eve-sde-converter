<#
.SYNOPSIS
    Windows automation script for eve-sde-converter
#>

param(
    [string]$DbType = "sqlite"
)

$BASE_URL = "https://developers.eveonline.com/static-data/tranquility"
$SDE_DIR = "sde"
$JSONL_FILE = "$SDE_DIR\latest.jsonl"
$PYTHON_CMD = ".\.venv\Scripts\python.exe"

# Helper for cleanup
function Clean-Sde {
    param($Path)
    if (Test-Path "$Path\sde") {
         Write-Host "  -> Flattening nested structure..." -ForegroundColor DarkGray
         Get-ChildItem -Path "$Path\sde\*" -Recurse | Move-Item -Destination $Path -Force
         Remove-Item -Path "$Path\sde" -Force
    }
}

# Ensure directories
if (-not (Test-Path $SDE_DIR)) { New-Item -ItemType Directory -Path $SDE_DIR -Force | Out-Null }

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$LOGFILE = "sde_conversion_log_$TIMESTAMP.log"

function Log-Message {
    param(
        [Parameter(Mandatory=$true)] $Message,
        $ForegroundColor = "White",
        [switch]$NoNewline
    )
    if ($NoNewline) {
        Write-Host $Message -NoNewline -ForegroundColor $ForegroundColor
    } else {
        Write-Host $Message -ForegroundColor $ForegroundColor
    }
    # Clean ANSI codes for log file if necessary, or just log raw string
    $cleanMsg = $Message -replace "\x1B\[[0-9;]*[a-zA-Z]", ""
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LOGFILE -Value "[$timestamp] $cleanMsg"
}

# Start Log
Log-Message "=== EVE SDE Converter (Windows) ===" -ForegroundColor Cyan
Log-Message "Log File: $LOGFILE" -ForegroundColor DarkGray

# 1. Get Latest Build Number
Log-Message "[1/4] Checking Version Info..." -NoNewline
try {
    Invoke-WebRequest -Uri "$BASE_URL/latest.jsonl" -OutFile $JSONL_FILE -ErrorAction Stop
    $latestBuild = $null
    Get-Content $JSONL_FILE | ForEach-Object {
        try {
            $json = $_ | ConvertFrom-Json
            if ($json._key -eq "sde") { $latestBuild = $json.buildNumber }
        } catch {}
    }
} catch {
    Log-Message " Failed." -ForegroundColor Red
    $err = "Could not fetch version info. Check your internet connection."
    Write-Error $err
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LOGFILE -Value "[$timestamp] ERROR: $err"
    exit 1
}
Log-Message " Done. (Build $latestBuild)" -ForegroundColor Green

# 2. Download Specific SDE Version
$SDE_ZIP_NAME = "eve-online-static-data-$latestBuild-yaml.zip"
$SDE_ZIP_PATH = "$SDE_DIR\$SDE_ZIP_NAME"
$SDE_DOWNLOAD_URL = "$BASE_URL/$SDE_ZIP_NAME"

# Check if we need to download (Marker file check + Zip check)
if (-not (Test-Path "$SDE_DIR\typeBonus.yaml")) {
    
    if (-not (Test-Path $SDE_ZIP_PATH)) {
        Log-Message "[2/4] Downloading SDE..." 
        # Use Start-BitsTransfer for Progress Bar
        try {
            Import-Module BitsTransfer -ErrorAction SilentlyContinue
            Start-BitsTransfer -Source $SDE_DOWNLOAD_URL -Destination $SDE_ZIP_PATH -DisplayName "Downloading EVE SDE"
        } catch {
             # Fallback if BITS not available
             Invoke-WebRequest -Uri $SDE_DOWNLOAD_URL -OutFile $SDE_ZIP_PATH
        }
    } else {
        Log-Message "[2/4] SDE Zip already present." -ForegroundColor Yellow
    }

    Log-Message "      Extracting..." -NoNewline
    Expand-Archive -Path $SDE_ZIP_PATH -DestinationPath $SDE_DIR -Force
    Clean-Sde -Path $SDE_DIR
    Log-Message " Done." -ForegroundColor Green

} else {
    Log-Message "[2/4] SDE data already extracted." -ForegroundColor Green
}

# 3. Copy Assets
Log-Message "[3/4] preparing Assets..." -NoNewline
Copy-Item "invVolumes1.csv" -Destination $SDE_DIR -Force
Copy-Item "invVolumes2.csv" -Destination $SDE_DIR -Force
Log-Message " Done." -ForegroundColor Green

# 4. Run Conversion with Progress Bar
if (-not (Test-Path $PYTHON_CMD)) {
    $err = "Virtual environment python NOT found at $PYTHON_CMD. Please create .venv first."
    Write-Error $err
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LOGFILE -Value "[$timestamp] ERROR: $err"
    exit 1
}

Log-Message "[4/4] Converting Database to $DbType..." 
Log-Message "      (This may take a few minutes. See progress bar above.)" -ForegroundColor DarkGray

# Setup process to capture output and show progress
$p = New-Object System.Diagnostics.Process
$p.StartInfo.FileName = (Resolve-Path $PYTHON_CMD).Path
$p.StartInfo.Arguments = "-u Load.py $DbType" # Pass dynamic DbType
$p.StartInfo.RedirectStandardOutput = $true
$p.StartInfo.RedirectStandardError = $true
$p.StartInfo.UseShellExecute = $false
$p.StartInfo.CreateNoWindow = $true
$p.StartInfo.WorkingDirectory = (Get-Location).Path

$p.Start() | Out-Null

$steps = @(
    # Character data
    "Factions", "Ancestries", "Bloodlines", "NPC Corporations", "NPC Divisions", "Character Attributes",
    # Agents
    "Agents", "AgentsInSpace", "Research Agents", "Agent Types",
    # Type/Dogma data
    "Type Materials", "Dogma Types", "Dogma Effects", "Dogma Attributes", "Dogma Attribute Categories",
    # Industry & Market
    "Blueprints", "Market Groups", "Meta Groups", "Control Tower Resources",
    # Categories, Groups, Types
    "Categories", "Graphics", "Groups", "Certificates", "Icons", "Skins", "Types", "Type Bonuses",
    # Masteries & Units
    "Masteries", "Units",
    # Planetary
    "Planetary",
    # Volumes
    "Volumes",
    # Universe data
    "Universe", "Regions", "Constellations", "Solar Systems", "Stargates", "Planets", "Moons", "Asteroid Belts", "Stars",
    # Stations
    "Stations", "Station Operations", "NPC Stations", "Station Services",
    # Inventory
    "Inventory Names", "Inventory Items",
    # Rig mappings
    "Rig Mappings"
)
$totalSteps = $steps.Count
$currentStepIdx = 0

# Loop until process exits
while (-not $p.HasExited) {
    # Non-blocking check to see if we have lines? 
    # ReadLine will block, but that's okay if output is trickling.
    # We use Peek to avoid blocking indefinitely if process hangs without output? 
    # Actually, simpler to just read line. If it blocks, it blocks until python prints or exits.
    
    $line = $p.StandardOutput.ReadLine()
    if ($line) {
        # Log to file
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path $LOGFILE -Value "[$timestamp] $line"

        # Check for Import lines to update progress
        if ($line -match "^[Ii]mporting (.*)") {
            $item = $Matches[1].Trim()
            $currentStepIdx++
            $percent = [math]::Min(100, [int](($currentStepIdx / $totalSteps) * 100))
            
            Write-Progress -Activity "Converting EVE SDE to $DbType" -Status "Processing: $item" -PercentComplete $percent
        }
    }
}
$p.WaitForExit()

# Clean up progress bar
Write-Progress -Activity "Converting EVE SDE to $DbType" -Completed

# Check Exit Code
if ($p.ExitCode -eq 0) {
    Log-Message "[4/4] Conversion Done." -ForegroundColor Green
    
    # Only move 'eve.db' if we are in sqlite mode
    if ($DbType -eq "sqlite") {
        if (Test-Path "eve.db") {
            Log-Message "      Moving eve.db to $SDE_DIR..." -ForegroundColor DarkGray
            
            # Retry loop for file move
            $maxRetries = 5
            $retryDelay = 2
            for ($i = 0; $i -lt $maxRetries; $i++) {
                try {
                    Move-Item -Path "eve.db" -Destination "$SDE_DIR\eve.db" -Force -ErrorAction Stop
                    Log-Message "      Move successful." -ForegroundColor Green
                    break
                } catch {
                    if ($i -eq $maxRetries - 1) {
                        $err = "Failed to move eve.db after $maxRetries attempts: $_"
                        Write-Error $err
                        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                        Add-Content -Path $LOGFILE -Value "[$timestamp] ERROR: $err"
                    } else {
                        Log-Message "      File locked, retrying in $retryDelay seconds..." -ForegroundColor Yellow
                        Start-Sleep -Seconds $retryDelay
                        # Force Garbage Collection just in case
                        [System.GC]::Collect()
                        [System.GC]::WaitForPendingFinalizers()
                    }
                }
            }
        }
    } else {
        Log-Message "      Data inserted into $DbType server." -ForegroundColor Green
    }

} else {
    Log-Message "[4/4] Conversion Failed." -ForegroundColor Red
    # Dump stderr if failed
    $err = $p.StandardError.ReadToEnd()
    Write-Host $err -ForegroundColor Red
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LOGFILE -Value "[$timestamp] STDERR OUTPUT:"
    Add-Content -Path $LOGFILE -Value $err
}

Log-Message "All Steps Complete." -ForegroundColor Green
