# EVE SDE Converter

[![Build Status](https://github.com/noirsoldats/eve-sde-converter/actions/workflows/update-sde.yml/badge.svg)](https://github.com/noirsoldats/eve-sde-converter/actions)
[![Releases](https://img.shields.io/github/v/release/noirsoldats/eve-sde-converter)](https://github.com/noirsoldats/eve-sde-converter/releases)

A modern, cross-platform tool to convert the EVE Online Static Data Export (SDE) from YAML into a usable SQLite database. Also supports MySQL, PostgreSQL, and MS SQL Server.

> **Attribution:** This project is a fork of [fuzzysteve/yamlloader](https://github.com/fuzzysteve/yamlloader). It has been modernized to support the latest 2024/2025+ SDE format, fix file encoding issues, and include robust automation for Windows.

## Key Features

*   **Modern SDE Support**: Compatible with the latest EVE SDE format (including consolidated `npcCharacters.yaml`, renamed `graphics.yaml`/`icons.yaml`, and new certificate/mastery structure).
*   **Robust Conversion**: Uses **Name-based Lookup** for critical groups (Stargates, Planets, etc.), making it resilient to future ID changes by CCP.
*   **Multiple Database Targets**: Outputs to SQLite (default), MySQL, PostgreSQL, or MS SQL Server.
*   **Windows Automation**: Includes a "One-Click" PowerShell script that handles everything (Download, Extract, Convert).
*   **Cross-Platform**: Tested on Windows, but the core Python logic is compatible with macOS and Linux.

## Requirements

*   **Python 3.12+**
*   `libyaml` (optional but recommended - enables CSafeLoader for ~5x faster YAML parsing)

## Quick Start (Windows)

We provide a fully automated script that does all the work for you.

1.  **Clone the repository**:
    ```powershell
    git clone https://github.com/noirsoldats/eve-sde-converter.git
    cd eve-sde-converter
    ```

2.  **Setup Environment**:
    Create a virtual environment (must be named `.venv`) and install dependencies:
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Run the Windows Script**:
    ```powershell
    .\run_windows.ps1
    ```

    **What this script does:**
    *   Checks the latest SDE version from CCP.
    *   **Downloads** the correct SDE zip file automatically.
    *   **Extracts** and organizes the files into the `sde` folder (cleaning up nested directories).
    *   **Runs** the conversion process with a visual progress bar.
    *   **Generates** a ready-to-use `eve.db` (SQLite) in the project root.
    *   **Logs** all activity to `sde_conversion_log_<TIMESTAMP>.log`.

## Quick Start (macOS / Linux)

Follow these steps to set up and run the SDE converter on macOS or Linux:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/noirsoldats/eve-sde-converter.git
    cd eve-sde-converter
    ```

2.  **Install libyaml** (optional but recommended for 5x faster YAML parsing):

    **macOS (Homebrew)**:
    ```bash
    brew install libyaml
    ```

    **macOS (MacPorts)**:
    ```bash
    sudo port install libyaml
    export C_INCLUDE_PATH=/opt/local/include
    ```

    **Ubuntu/Debian**:
    ```bash
    sudo apt-get update
    sudo apt-get install -y libyaml-dev
    ```

    **Fedora/RHEL**:
    ```bash
    sudo dnf install -y libyaml-devel
    ```

3.  **Setup Python Environment**:
    Create a virtual environment and install dependencies:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

4.  **Run the Conversion**:
    ```bash
    chmod +x runconversion.sh
    ./runconversion.sh
    ```

    This will create `eve.db` in the project root. The process takes 5-15 minutes depending on your system.
    **What this script does:**
    *   Checks the latest SDE version from CCP.
    *   **Downloads** the correct SDE zip file automatically.
    *   **Extracts** and organizes the files into the `sde` folder (cleaning up nested directories).
    *   **Runs** the conversion process with a visual progress bar.
    *   **Generates** a ready-to-use `eve.db` (SQLite) in the project root.
    *   **Logs** all activity to `sde_conversion_log_<TIMESTAMP>.log`.

5.  **Verify the Database**:
    ```bash
    ls -lh eve.db
    sqlite3 eve.db "SELECT COUNT(*) FROM invTypes;"
    ```

## Database Configuration

The converter supports multiple database backends. Edit `sdeloader.cfg` to configure connection strings:

| Target        | Command                   | Notes                                                         |
|---------------|---------------------------|---------------------------------------------------------------|
| SQLite        | `python Load.py sqlite`   | Default. Creates `eve.db` in the project root.                |
| MySQL         | `python Load.py mysql`    | Requires `pymysql`. Configure connection in `sdeloader.cfg`.  |
| PostgreSQL    | `python Load.py postgres` | Requires `psycopg2`. Configure connection in `sdeloader.cfg`. |
| MS SQL Server | `python Load.py mssql`    | Requires `pymssql`. Configure connection in `sdeloader.cfg`.  |

## Automatic Builds

This repository is configured with GitHub Actions to automatically verify the code and build releases. You can find the latest automated builds and source code snapshots under the [Releases](https://github.com/noirsoldats/eve-sde-converter/releases) tab.

## Data Included

The converter imports the following data from the SDE:

- **Character Data**: Factions, races, bloodlines, ancestries, attributes
- **Corporations**: NPC corporations, divisions
- **Agents**: Agent locations, types, research agents
- **Items**: Types, groups, categories, market groups, meta groups, packaged volumes
- **Dogma**: Attributes, effects, type attributes/effects
- **Industry**: Blueprints, materials, activities, Station Rig Effect Mappings
- **Certificates & Masteries**: Certificate definitions and ship mastery requirements
- **Universe**: Regions, constellations, solar systems, stargates, planets, moons, asteroid belts, stars
- **Stations**: NPC stations, operations, services
- **Skins**: Skin definitions, licenses, materials
- **Misc**: Icons, graphics, units, control tower resources
