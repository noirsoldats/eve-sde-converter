#!/usr/bin/env bash

#=============================================================
# EVE SDE Converter - Linux Automation Script
#=============================================================

set -euo pipefail

# Global variables
BASE_URL="https://developers.eveonline.com/static-data/tranquility"
SDE_DIR="sde"
JSONL_FILE="${SDE_DIR}/latest.jsonl"
LOGFILE="sde_conversion_log_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
CYAN=$'\033[0;36m'
NC=$'\033[0m' # No Color

# --- UI (log above, progress on bottom) ----------------------

IS_TTY=0
[[ -t 1 ]] && IS_TTY=1

LOG_HISTORY_SIZE=20  # Will be updated dynamically
LOG_HISTORY=()

PROGRESS_CURRENT=0
PROGRESS_TOTAL=1
PROGRESS_DESC=""

# --- UI helpers ---------------------------------------------

get_log_history_size() {
    local rows="$(tput lines 2>/dev/null || echo 24)"
    local max_lines=$((rows - 1))  # Reserve 1 line for progress bar
    (( max_lines < 5 )) && max_lines=5  # Minimum 5 lines
    (( max_lines > 50 )) && max_lines=50  # Cap at 50 for performance
    echo "$max_lines"
}

ui_init() {
    (( IS_TTY )) || return 0
    clear
}

ui_cleanup() {
    (( IS_TTY )) || return 0
    echo
}

ui_add_log() {
    local line="$1"
    local cols="$(tput cols 2>/dev/null || echo 80)"

    # Truncate if too long (simple approach)
    # Note: This counts ANSI color codes as characters, so may truncate slightly early
    if (( ${#line} > cols )); then
        line="${line:0:$((cols - 3))}..."
    fi

    LOG_HISTORY+=("$line")
    if (( ${#LOG_HISTORY[@]} > LOG_HISTORY_SIZE )); then
        LOG_HISTORY=("${LOG_HISTORY[@]:1}")
    fi
}

ui_render() {
    (( IS_TTY )) || return 0

    # Detect current terminal size
    local cols="$(tput cols 2>/dev/null || echo 80)"
    local rows="$(tput lines 2>/dev/null || echo 24)"

    # Update log history size dynamically
    LOG_HISTORY_SIZE=$(get_log_history_size)

    # Trim LOG_HISTORY if terminal shrunk
    while (( ${#LOG_HISTORY[@]} > LOG_HISTORY_SIZE )); do
        LOG_HISTORY=("${LOG_HISTORY[@]:1}")
    done

    # Reserve space: log history + progress bar
    local reserved=$(( LOG_HISTORY_SIZE + 1 ))
    local start_row=$(( rows - reserved + 1 ))
    (( start_row < 1 )) && start_row=1

    # Save cursor
    printf '\0337'

    # Clear render area
    for (( r=start_row; r<=rows; r++ )); do
        printf '\033[%d;1H\033[2K' "$r"
    done

    # Render logs
    local row="$start_row"
    for line in "${LOG_HISTORY[@]}"; do
        printf '\033[%d;1H%s' "$row" "$line"
        ((row++))
    done

    # Render progress bar (last line)
    ui_render_progress "$rows"

    # Restore cursor
    printf '\0338'
}

ui_render_progress() {
    local row="${1-}"

    local current="$PROGRESS_CURRENT"
    local total="$PROGRESS_TOTAL"
    local desc="$PROGRESS_DESC"

    (( total > 0 )) || total=1
    (( current > total )) && current="$total"

    local percent=$(( current * 100 / total ))

    # Detect current terminal width
    local cols="$(tput cols 2>/dev/null || echo 80)"

    # Calculate bar and description space
    local overhead=9  # [, ], space, and " 100%"
    local desc_reserve=30  # Try to reserve ~30 chars for description
    local bar_width=$((cols - overhead - desc_reserve))
    (( bar_width < 15 )) && bar_width=15  # Minimum bar width

    local filled=$(( percent * bar_width / 100 ))
    local empty=$(( bar_width - filled ))

    local bar empty_bar
    bar="$(printf '%*s' "$filled" '' | tr ' ' '#')"
    empty_bar="$(printf '%*s' "$empty" '' | tr ' ' '-')"

    # Calculate actual space for description
    local max_desc=$(( cols - bar_width - overhead ))
    (( max_desc < 10 )) && max_desc=10
    desc="${desc:0:max_desc}"

    printf '\033[%d;1H[%s%s] %3d%% %s' \
        "$row" "$bar" "$empty_bar" "$percent" "$desc"
}


# --- Logging -------------------------------------------------

log_message() {
    local message="$1"
    local color="${2:-$NC}"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

    local line="${color}${message}${NC}"
    ui_add_log "$line"
    ui_render

    echo "[${timestamp}] ${message}" >> "${LOGFILE}"
}

log_error() {
    local message="$1"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

    ui_add_log "${RED}ERROR: ${message}${NC}"
    ui_render

    echo "[${timestamp}] ERROR: ${message}" >> "${LOGFILE}"
    ui_cleanup
    exit 1
}

require_cmd() {
    local cmd="$1"
    command -v "$cmd" >/dev/null 2>&1 || log_error "Required command not found: $cmd"
}

# Ensure we clean up the progress bar on exit (success or failure)
trap 'ui_cleanup' EXIT

# --- Script start --------------------------------------------

ui_init

log_message "=== EVE SDE Converter (Linux) ===" "${CYAN}"
log_message "Log File: ${LOGFILE}" "${BLUE}"

# Dependencies
require_cmd curl
require_cmd unzip

# Source virtual environment if available
if [[ -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

require_cmd python3

# Make sure SDE directory exists
if [[ ! -d "$SDE_DIR" ]]; then
    mkdir -p "$SDE_DIR"
    log_message "Created SDE directory: $SDE_DIR" "${BLUE}"
fi

# 1. Get Latest Build Number
log_message "[1/5] Checking Version Info..." "${BLUE}"

if ! curl -fsS -o "$JSONL_FILE" "${BASE_URL}/latest.jsonl"; then
    log_error "Could not fetch version info. Check your internet connection."
fi

BUILD_NUMBER="$(grep -Eo '"buildNumber"[[:space:]]*:[[:space:]]*[0-9]+' "$JSONL_FILE" \
    | head -n1 \
    | grep -Eo '[0-9]+' || true)"

if [[ -z "${BUILD_NUMBER}" ]]; then
    log_error "Could not get build number from latest.jsonl."
fi

log_message "Done. (Build ${BUILD_NUMBER})" "${GREEN}"

# 2. Download SDE
SDE_ZIP_NAME="eve-online-static-data-${BUILD_NUMBER}-yaml.zip"
SDE_ZIP_PATH="${SDE_DIR}/${SDE_ZIP_NAME}"
SDE_DOWNLOAD_URL="${BASE_URL}/${SDE_ZIP_NAME}"

if [[ ! -f "$SDE_DIR/typeBonus.yaml" ]]; then
    if [[ ! -f "$SDE_ZIP_PATH" ]]; then
        log_message "[2/5] Downloading SDE..." "${BLUE}"
        if ! curl -fL --retry 3 --retry-delay 2 -o "$SDE_ZIP_PATH" "$SDE_DOWNLOAD_URL"; then
            log_error "Failed to download SDE: $SDE_DOWNLOAD_URL"
        fi
    else
        log_message "[2/5] SDE Zip already present: $SDE_ZIP_PATH" "${YELLOW}"
    fi

    log_message "      Extracting..." "${BLUE}"
    if ! unzip -o "$SDE_ZIP_PATH" -d "$SDE_DIR" >/dev/null; then
        log_error "Failed to extract SDE."
    fi

    # Clean up nested structure if needed
    if [[ -d "$SDE_DIR/sde" ]]; then
        log_message "      Flattening nested structure..." "${BLUE}"
        while IFS= read -r -d '' item; do
            mv "$item" "$SDE_DIR/"
        done < <(find "$SDE_DIR/sde" -mindepth 1 -maxdepth 1 -print0)
        rm -rf "$SDE_DIR/sde"
    fi

    log_message "Done." "${GREEN}"
else
    log_message "[2/5] SDE data already extracted." "${GREEN}"
fi

# 3. Copy Assets
log_message "[3/5] Preparing Assets..." "${BLUE}"

[[ -f "invVolumes1.csv" ]] || log_error "Required file not found: invVolumes1.csv"
[[ -f "invVolumes2.csv" ]] || log_error "Required file not found: invVolumes2.csv"

cp -f "invVolumes1.csv" "$SDE_DIR/" || log_error "Failed to copy invVolumes1.csv"
cp -f "invVolumes2.csv" "$SDE_DIR/" || log_error "Failed to copy invVolumes2.csv"

log_message "Done." "${GREEN}"

# 4. Run Conversion with Progress Tracking
log_message "[4/5] Converting Database to SQLite..." "${BLUE}"

STEPS=(
    "Factions" "Ancestries" "Bloodlines" "NPC Corporations" "NPC Divisions" "Character Attributes"
    "Agents" "AgentsInSpace" "Research Agents" "Agent Types"
    "Type Materials" "Dogma Types" "Dogma Effects" "Dogma Attributes" "Dogma Attribute Categories"
    "Blueprints" "Market Groups" "Meta Groups" "Control Tower Resources"
    "Categories" "Graphics" "Groups" "Certificates" "Icons" "Skins" "Types" "Type Bonuses"
    "Masteries" "Units"
    "Planetary"
    "Volumes"
    "Universe" "Regions" "Constellations" "Solar Systems" "Stargates" "Planets" "Moons" "Asteroid Belts" "Stars"
    "Stations" "Station Operations" "NPC Stations" "Station Services"
    "Inventory Names" "Inventory Items"
    "Rig Mappings"
)
totalSteps=${#STEPS[@]}
log_message "      Processing ~${totalSteps} steps..." "${BLUE}"
log_message "      Starting conversion process..." "${BLUE}"

# Initialize progress bar state
PROGRESS_CURRENT=0
PROGRESS_TOTAL="$totalSteps"
PROGRESS_DESC="Starting..."
ui_render_progress

set +e
python3 -u Load.py sqlite --create-stripped 2>&1 | while IFS= read -r line; do
    echo "$line" >> "${LOGFILE}"

    if [[ "$line" =~ ^[Ii]mporting[[:space:]]+(.+) ]]; then
        item="${BASH_REMATCH[1]}"
        PROGRESS_CURRENT=$((PROGRESS_CURRENT + 1))
        (( PROGRESS_CURRENT > PROGRESS_TOTAL )) && PROGRESS_CURRENT="$PROGRESS_TOTAL"
        PROGRESS_DESC="Processing: $item"
        ui_render
    else
        ui_add_log "$line"
        ui_render
    fi
done
py_status=${PIPESTATUS[0]}
set -e

if (( py_status == 0 )); then
    PROGRESS_CURRENT="$PROGRESS_TOTAL"
    PROGRESS_DESC="Conversion complete"
    ui_render_progress

    log_message "[4/5] Conversion Done." "${GREEN}"

    if [[ -f "eve.db" ]]; then
      log_message "eve.db detected." "${GREEN}"
#        log_message "      Moving eve.db to ${SDE_DIR}/eve.db..." "${BLUE}"
#        if mv -f "eve.db" "${SDE_DIR}/eve.db"; then
#            log_message "      Move successful." "${GREEN}"
#        else
#            log_error "Failed to move eve.db."
#        fi
    else
        log_message "      Note: eve.db not found after conversion." "${YELLOW}"
    fi
else
    log_error "[4/5] Conversion Failed. (python3 exit code: ${py_status})"
fi

# 5. Run ESI Data Updates
log_message "[5/5] Running ESI Data Updates..." "${BLUE}"

log_message "      Updating items via ESI..." "${BLUE}"
# python3 getitems-esi.py mysql
# python3 getitems-esi.py sqlite
# python3 getitems-esi.py postgres
# python3 getitems-esi.py postgresschema

log_message "      Updating groups via ESI..." "${BLUE}"
# python3 getgroups-esi.py mysql
# python3 getgroups-esi.py sqlite
# python3 getgroups-esi.py postgres
# python3 getgroups-esi.py postgresschema

log_message "      Type export to JSON..." "${BLUE}"
# python3 TypesToJson.py >typestojson.log

log_message "      Type export to Excel..." "${BLUE}"
# python3 exportTypesxlsx.py

PROGRESS_DESC="All steps complete"
ui_render_progress
log_message "All Steps Complete." "${GREEN}"
