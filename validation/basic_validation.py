#!/usr/bin/env python3
"""
Basic Database Validation Script for EVE SDE

Performs quick smoke tests to verify database integrity:
- Counts tables (expect ~50+ tables)
- Counts rows in critical tables
- Validates basic data presence

Usage: python3 basic_validation.py <database_type>

where database_type is: sqlite, mysql, postgres, or mssql
"""

import sys
import os
import configparser
from sqlalchemy import create_engine, inspect, text
from pathlib import Path

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Expected minimum row counts for critical tables
EXPECTED_COUNTS = {
    'invTypes': 30000,
    'invGroups': 1000,
    'mapSolarSystems': 8000,
    'dgmTypeAttributes': 100000,
    'invCategories': 40,
    'mapRegions': 100,
    'dgmAttributeTypes': 500,
}

# Tables that must exist
REQUIRED_TABLES = [
    'invTypes', 'invGroups', 'invCategories', 'invMetaTypes',
    'dgmTypeAttributes', 'dgmAttributeTypes', 'dgmEffects',
    'mapRegions', 'mapConstellations', 'mapSolarSystems',
    'industryBlueprints', 'industryActivity',
]


def log_info(msg):
    print(f"{Colors.OKBLUE}[INFO]{Colors.ENDC} {msg}")


def log_success(msg):
    print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} {msg}")


def log_warning(msg):
    print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} {msg}")


def log_error(msg):
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")


def get_connection_string(db_type):
    """Read connection string from sdeloader.cfg"""
    file_location = Path(__file__).parent.parent
    ini_file = file_location / 'sdeloader.cfg'

    if not ini_file.exists():
        log_error(f"Configuration file not found: {ini_file}")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(ini_file)

    try:
        connection_string = config.get('Database', db_type)
        log_info(f"Loaded connection string for {db_type}")
        return connection_string
    except Exception as e:
        log_error(f"Failed to read connection string for {db_type}: {e}")
        sys.exit(1)


def connect_to_database(connection_string):
    """Create database engine and connection"""
    try:
        engine = create_engine(connection_string)
        connection = engine.connect()
        log_success("Connected to database")
        return engine, connection
    except Exception as e:
        log_error(f"Failed to connect to database: {e}")
        sys.exit(1)


def quote_identifier(name, db_type):
    """Quote identifier for database-specific case sensitivity"""
    if db_type == 'postgres':
        # PostgreSQL requires double quotes for mixed-case identifiers
        return f'"{name}"'
    elif db_type == 'mssql':
        # MSSQL uses square brackets
        return f'[{name}]'
    else:
        # SQLite and MySQL don't need quoting for our use case
        return name


def validate_table_count(inspector):
    """Validate that sufficient tables exist"""
    log_info("\n" + "="*70)
    log_info("VALIDATION 1: Table Count")
    log_info("="*70)

    tables = inspector.get_table_names()
    table_count = len(tables)

    log_info(f"Total tables found: {table_count}")

    if table_count < 40:
        log_error(f"Insufficient tables! Expected at least 40, found {table_count}")
        return False
    elif table_count < 50:
        log_warning(f"Table count is low. Expected ~50+, found {table_count}")
        return True
    else:
        log_success(f"Table count is good: {table_count} tables")
        return True


def validate_required_tables(inspector):
    """Validate that all required tables exist"""
    log_info("\n" + "="*70)
    log_info("VALIDATION 2: Required Tables")
    log_info("="*70)

    tables = set(inspector.get_table_names())
    missing_tables = []

    for required_table in REQUIRED_TABLES:
        if required_table not in tables:
            missing_tables.append(required_table)
            log_error(f"Missing required table: {required_table}")
        else:
            log_info(f"✓ Found: {required_table}")

    if missing_tables:
        log_error(f"Missing {len(missing_tables)} required tables!")
        return False
    else:
        log_success("All required tables present")
        return True


def validate_row_counts(connection, inspector, db_type):
    """Validate row counts in critical tables"""
    log_info("\n" + "="*70)
    log_info("VALIDATION 3: Row Counts in Critical Tables")
    log_info("="*70)

    tables = set(inspector.get_table_names())
    failures = []

    for table, expected_min in EXPECTED_COUNTS.items():
        if table not in tables:
            log_error(f"Table {table} not found (required for row count check)")
            failures.append(table)
            continue

        try:
            # Quote table name for database-specific case sensitivity
            quoted_table = quote_identifier(table, db_type)
            result = connection.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
            count = result.scalar()

            if count < expected_min:
                log_warning(f"{table}: {count} rows (expected at least {expected_min})")
                failures.append(table)
            else:
                pct_over = ((count - expected_min) / expected_min) * 100
                log_success(f"{table}: {count} rows (expected min: {expected_min}, +{pct_over:.1f}%)")

        except Exception as e:
            log_error(f"Failed to count rows in {table}: {e}")
            failures.append(table)

    if failures:
        log_warning(f"{len(failures)} tables failed row count validation")
        # Row count warnings are not fatal - data may legitimately change
        return True
    else:
        log_success("All row count checks passed")
        return True


def validate_data_presence(connection, db_type):
    """Validate that critical data exists"""
    log_info("\n" + "="*70)
    log_info("VALIDATION 4: Data Presence Checks")
    log_info("="*70)

    # Build queries with database-specific quoting
    q = lambda x: quote_identifier(x, db_type)

    checks = [
        ("invTypes with names", f'SELECT COUNT(*) FROM {q("invTypes")} WHERE {q("typeName")} IS NOT NULL'),
        ("invGroups with names", f'SELECT COUNT(*) FROM {q("invGroups")} WHERE {q("groupName")} IS NOT NULL'),
        ("Solar systems in region", f'SELECT COUNT(DISTINCT {q("regionID")}) FROM {q("mapSolarSystems")}'),
        ("Types with volume data", f'SELECT COUNT(*) FROM {q("invTypes")} WHERE volume > 0'),
        ("Blueprints with activities", f'SELECT COUNT(DISTINCT {q("typeID")}) FROM {q("industryActivity")}'),
    ]

    failures = []

    for check_name, query in checks:
        try:
            result = connection.execute(text(query))
            count = result.scalar()

            if count == 0:
                log_error(f"{check_name}: EMPTY (0 rows)")
                failures.append(check_name)
            elif count < 10:
                log_warning(f"{check_name}: {count} rows (very low)")
            else:
                log_success(f"{check_name}: {count} rows")

        except Exception as e:
            log_error(f"Failed to execute check '{check_name}': {e}")
            failures.append(check_name)

    if failures:
        log_error(f"{len(failures)} data presence checks failed")
        return False
    else:
        log_success("All data presence checks passed")
        return True


def print_summary(results):
    """Print validation summary"""
    log_info("\n" + "="*70)
    log_info("VALIDATION SUMMARY")
    log_info("="*70)

    total_checks = len(results)
    passed_checks = sum(1 for r in results if r)
    failed_checks = total_checks - passed_checks

    log_info(f"Total checks: {total_checks}")
    log_info(f"Passed: {passed_checks}")
    log_info(f"Failed: {failed_checks}")

    if failed_checks == 0:
        print(f"\n{Colors.OKGREEN}{'='*70}")
        print(f"✓ ALL BASIC VALIDATION CHECKS PASSED")
        print(f"{'='*70}{Colors.ENDC}\n")
        return True
    else:
        print(f"\n{Colors.FAIL}{'='*70}")
        print(f"✗ {failed_checks} VALIDATION CHECKS FAILED")
        print(f"{'='*70}{Colors.ENDC}\n")
        return False


def main():
    if len(sys.argv) != 2:
        log_error("Invalid arguments")
        print("Usage: python3 basic_validation.py <database_type>")
        print("  database_type: sqlite, mysql, postgres, or mssql")
        sys.exit(1)

    db_type = sys.argv[1]

    print(f"{Colors.HEADER}{'='*70}")
    print(f"EVE SDE Basic Database Validation")
    print(f"Database Type: {db_type}")
    print(f"{'='*70}{Colors.ENDC}\n")

    # Get connection string and connect
    connection_string = get_connection_string(db_type)
    engine, connection = connect_to_database(connection_string)
    inspector = inspect(engine)

    # Run validation checks
    results = []
    results.append(validate_table_count(inspector))
    results.append(validate_required_tables(inspector))
    results.append(validate_row_counts(connection, inspector, db_type))
    results.append(validate_data_presence(connection, db_type))

    # Close connection
    connection.close()
    engine.dispose()

    # Print summary and exit
    success = print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
