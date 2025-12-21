# EVE SDE Converter (Windows Optimized)

[![Build Status](https://github.com/noirsoldats/eve-sde-converter/actions/workflows/update-sde.yml/badge.svg)](https://github.com/noirsoldats/eve-sde-converter/actions)
[![Releases](https://img.shields.io/github/v/release/noirsoldats/eve-sde-converter)](https://github.com/noirsoldats/eve-sde-converter/releases)

A modern, cross-platform tool to convert the EVE Online Static Data Export (SDE) from YAML into a usable SQLite (or SQL) database.

> **Attribution:** This project is a fork of [fuzzysteve/yamlloader](https://github.com/fuzzysteve/yamlloader). It has been modernized to support the latest 2024/2025+ SDE format, fix file encoding issues, and include robust automation for Windows.

## Key Features

*   **Modern SDE Support**: Compatible with the latest EVE SDE format (including `npcCharacters`, `graphics`, and `icons` name changes).
*   **Robust Conversion**: Uses **Name-based Lookup** for critical groups (Stargates, Planets, etc.), making it resilient to future ID changes by CCP.
*   **Windows Automation**: Includes a "One-Click" PowerShell script that handles everything (Download, Extract, Convert).
*   **Cross-Platform**: Tested on Windows, but the core Python logic is compatible with macOS and Linux.

## Requirements

*   **Python 3.12+**
*   `libyaml` (optional, for faster YAML parsing)

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
    *   **Generates** a ready-to-use `eve.db` (SQLite) in the `sde` folder.
    *   **Logs** all activity to `sde_conversion_log_<TIMESTAMP>.log`.

## Manual Installation (macOS / Linux / Custom)

If you prefer to run things manually or are on a non-Windows platform:

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Download SDE**:
    Download the "SDE" (Static Data Export) from [CCP's Developer Site](https://developers.eveonline.com/resource/resources) and extract it into a folder named `sde` in the project root.

3.  **Run Loader**:
    ```bash
    python Load.py sqlite
    ```
    *(You can also use arguments for `mysql`, `postgres`, or `mssql` - check `sdeloader.cfg` for configuration).*

## Automatic Builds

This repository is configured with GitHub Actions to automatically verify the code and build releases. You can find the latest automated builds and source code snapshots under the [Releases](https://github.com/noirsoldats/eve-sde-converter/releases) tab.
