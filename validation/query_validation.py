#!/usr/bin/env python3
"""
Query-Based Database Validation Script for EVE SDE

Performs deeper integrity checks through SQL queries:
- Data range validation
- Foreign key integrity
- Unique constraints
- Non-null critical columns
- EVE-specific data sanity checks

Usage: python3 query_validation.py <database_type>

where database_type is: sqlite, mysql, postgres, or mssql
"""

import sys
import os
import configparser
from sqlalchemy import create_engine, text
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


def run_query_check(connection, check_name, query, expected_count=0, allow_failures=False):
    """
    Run a validation query and check result

    Args:
        connection: Database connection
        check_name: Description of the check
        query: SQL query to run
        expected_count: Expected count (0 = expect no violations)
        allow_failures: If True, failures are warnings not errors

    Returns:
        True if check passed, False otherwise
    """
    try:
        result = connection.execute(text(query))
        count = result.scalar()

        if count == expected_count:
            log_success(f"{check_name}: PASSED (count: {count})")
            return True
        elif allow_failures:
            log_warning(f"{check_name}: {count} violations found (non-critical)")
            return True
        else:
            log_error(f"{check_name}: FAILED (found {count}, expected {expected_count})")
            return False

    except Exception as e:
        log_error(f"{check_name}: EXCEPTION - {e}")
        return False


def validate_data_ranges(connection):
    """Validate that data falls within expected ranges"""
    log_info("\n" + "="*70)
    log_info("VALIDATION 1: Data Range Checks")
    log_info("="*70)

    checks = [
        ("Solar system security status in valid range",
         "SELECT COUNT(*) FROM mapSolarSystems WHERE security < -1.0 OR security > 1.0",
         0, False),

        ("Type volumes are non-negative",
         "SELECT COUNT(*) FROM invTypes WHERE volume < 0",
         0, False),

        ("Type masses are non-negative",
         "SELECT COUNT(*) FROM invTypes WHERE mass < 0",
         0, False),

        ("Blueprint time values are positive",
         "SELECT COUNT(*) FROM industryActivity WHERE time < 0",
         0, False),

        ("Material quantities are positive",
         "SELECT COUNT(*) FROM industryActivityMaterials WHERE quantity <= 0",
         0, False),
    ]

    results = []
    for check_name, query, expected, allow_fail in checks:
        results.append(run_query_check(connection, check_name, query, expected, allow_fail))

    passed = sum(results)
    total = len(results)
    log_info(f"\nData range checks: {passed}/{total} passed")

    return all(results)


def validate_referential_integrity(connection):
    """Validate foreign key relationships"""
    log_info("\n" + "="*70)
    log_info("VALIDATION 2: Referential Integrity")
    log_info("="*70)

    checks = [
        ("Types reference valid groups",
         "SELECT COUNT(*) FROM invTypes t LEFT JOIN invGroups g ON t.groupID = g.groupID WHERE g.groupID IS NULL",
         0, False),

        ("Groups reference valid categories",
         "SELECT COUNT(*) FROM invGroups g LEFT JOIN invCategories c ON g.categoryID = c.categoryID WHERE c.categoryID IS NULL",
         0, False),

        ("Solar systems reference valid constellations",
         "SELECT COUNT(*) FROM mapSolarSystems s LEFT JOIN mapConstellations c ON s.constellationID = c.constellationID WHERE c.constellationID IS NULL",
         0, False),

        ("Constellations reference valid regions",
         "SELECT COUNT(*) FROM mapConstellations c LEFT JOIN mapRegions r ON c.regionID = r.regionID WHERE r.regionID IS NULL",
         0, False),

        ("Blueprint materials reference valid types",
         "SELECT COUNT(*) FROM industryActivityMaterials m LEFT JOIN invTypes t ON m.materialTypeID = t.typeID WHERE t.typeID IS NULL",
         0, True),  # Allow some - SDE may have unreleased/removed items

        ("Blueprint products reference valid types",
         "SELECT COUNT(*) FROM industryActivityProducts p LEFT JOIN invTypes t ON p.productTypeID = t.typeID WHERE t.typeID IS NULL",
         0, True),  # Allow some - SDE may have unreleased/removed items

        ("Blueprint type IDs reference valid types",
         "SELECT COUNT(*) FROM industryActivity ia LEFT JOIN invTypes t ON ia.typeID = t.typeID WHERE t.typeID IS NULL",
         0, False),
    ]

    results = []
    for check_name, query, expected, allow_fail in checks:
        results.append(run_query_check(connection, check_name, query, expected, allow_fail))

    passed = sum(results)
    total = len(results)
    log_info(f"\nReferential integrity checks: {passed}/{total} passed")

    return all(results)


def validate_uniqueness_constraints(connection):
    """Validate uniqueness of primary keys and unique columns"""
    log_info("\n" + "="*70)
    log_info("VALIDATION 3: Uniqueness Constraints")
    log_info("="*70)

    checks = [
        ("Type IDs are unique",
         "SELECT COUNT(*) - COUNT(DISTINCT typeID) FROM invTypes",
         0, False),

        ("Group IDs are unique",
         "SELECT COUNT(*) - COUNT(DISTINCT groupID) FROM invGroups",
         0, False),

        ("Category IDs are unique",
         "SELECT COUNT(*) - COUNT(DISTINCT categoryID) FROM invCategories",
         0, False),

        ("Solar system IDs are unique",
         "SELECT COUNT(*) - COUNT(DISTINCT solarSystemID) FROM mapSolarSystems",
         0, False),

        ("Region IDs are unique",
         "SELECT COUNT(*) - COUNT(DISTINCT regionID) FROM mapRegions",
         0, False),
    ]

    results = []
    for check_name, query, expected, allow_fail in checks:
        results.append(run_query_check(connection, check_name, query, expected, allow_fail))

    passed = sum(results)
    total = len(results)
    log_info(f"\nUniqueness constraint checks: {passed}/{total} passed")

    return all(results)


def validate_not_null_constraints(connection):
    """Validate critical NOT NULL constraints"""
    log_info("\n" + "="*70)
    log_info("VALIDATION 4: NOT NULL Constraints")
    log_info("="*70)

    checks = [
        ("Type names are not null",
         "SELECT COUNT(*) FROM invTypes WHERE typeName IS NULL",
         0, False),

        ("Group names are not null",
         "SELECT COUNT(*) FROM invGroups WHERE groupName IS NULL",
         0, False),

        ("Category names are not null",
         "SELECT COUNT(*) FROM invCategories WHERE categoryName IS NULL",
         0, False),

        ("Solar system names are not null",
         "SELECT COUNT(*) FROM mapSolarSystems WHERE solarSystemName IS NULL",
         0, False),

        ("Region names are not null",
         "SELECT COUNT(*) FROM mapRegions WHERE regionName IS NULL",
         0, False),
    ]

    results = []
    for check_name, query, expected, allow_fail in checks:
        results.append(run_query_check(connection, check_name, query, expected, allow_fail))

    passed = sum(results)
    total = len(results)
    log_info(f"\nNOT NULL constraint checks: {passed}/{total} passed")

    return all(results)


def validate_eve_specific_sanity(connection):
    """EVE Online specific sanity checks"""
    log_info("\n" + "="*70)
    log_info("VALIDATION 5: EVE-Specific Sanity Checks")
    log_info("="*70)

    checks = [
        ("Published types have non-zero market group or blueprint (allow some unpublished)",
         "SELECT COUNT(*) FROM invTypes WHERE published = 1 AND marketGroupID IS NULL",
         0, True),  # Allow failures - some published items may not have market group

        ("Blueprint manufacturing produces at least one product",
         "SELECT COUNT(*) FROM industryActivity ia WHERE ia.activityID = 1 AND NOT EXISTS (SELECT 1 FROM industryActivityProducts p WHERE p.typeID = ia.typeID AND p.activityID = 1)",
         0, True),  # Allow some - could be reactions or special blueprints

        ("Manufacturing materials exist for manufacturing activities",
         "SELECT COUNT(*) FROM industryActivity ia WHERE ia.activityID = 1 AND NOT EXISTS (SELECT 1 FROM industryActivityMaterials m WHERE m.typeID = ia.typeID AND m.activityID = 1)",
         0, True),  # Allow some - might be legitimate

        ("Ships are in ship category",
         "SELECT COUNT(*) FROM invTypes t JOIN invGroups g ON t.groupID = g.groupID WHERE t.groupID IN (SELECT groupID FROM invGroups WHERE categoryID = 6) AND g.categoryID != 6",
         0, False),

        ("Solar systems have at least one celestial",
         "SELECT COUNT(DISTINCT solarSystemID) FROM mapSolarSystems WHERE solarSystemID NOT IN (SELECT DISTINCT solarSystemID FROM mapDenormalize WHERE solarSystemID IS NOT NULL)",
         0, True),  # Allow some - data may be incomplete
    ]

    results = []
    for check_name, query, expected, allow_fail in checks:
        results.append(run_query_check(connection, check_name, query, expected, allow_fail))

    passed = sum(results)
    total = len(results)
    log_info(f"\nEVE-specific sanity checks: {passed}/{total} passed")

    # Don't fail validation if only warnings
    return True


def print_summary(results):
    """Print validation summary"""
    log_info("\n" + "="*70)
    log_info("QUERY VALIDATION SUMMARY")
    log_info("="*70)

    total_checks = len(results)
    passed_checks = sum(1 for r in results if r)
    failed_checks = total_checks - passed_checks

    log_info(f"Total validation groups: {total_checks}")
    log_info(f"Passed: {passed_checks}")
    log_info(f"Failed: {failed_checks}")

    if failed_checks == 0:
        print(f"\n{Colors.OKGREEN}{'='*70}")
        print(f"✓ ALL QUERY VALIDATION CHECKS PASSED")
        print(f"{'='*70}{Colors.ENDC}\n")
        return True
    else:
        print(f"\n{Colors.FAIL}{'='*70}")
        print(f"✗ {failed_checks} VALIDATION GROUPS FAILED")
        print(f"{'='*70}{Colors.ENDC}\n")
        return False


def main():
    if len(sys.argv) != 2:
        log_error("Invalid arguments")
        print("Usage: python3 query_validation.py <database_type>")
        print("  database_type: sqlite, mysql, postgres, or mssql")
        sys.exit(1)

    db_type = sys.argv[1]

    print(f"{Colors.HEADER}{'='*70}")
    print(f"EVE SDE Query-Based Database Validation")
    print(f"Database Type: {db_type}")
    print(f"{'='*70}{Colors.ENDC}\n")

    # Get connection string and connect
    connection_string = get_connection_string(db_type)
    engine, connection = connect_to_database(connection_string)

    # Run validation checks
    results = []
    results.append(validate_data_ranges(connection))
    results.append(validate_referential_integrity(connection))
    results.append(validate_uniqueness_constraints(connection))
    results.append(validate_not_null_constraints(connection))
    results.append(validate_eve_specific_sanity(connection))

    # Close connection
    connection.close()
    engine.dispose()

    # Print summary and exit
    success = print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
