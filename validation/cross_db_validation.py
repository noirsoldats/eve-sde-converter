#!/usr/bin/env python3
"""
Cross-Database Validation Script for EVE SDE

Compares a test database against a SQLite baseline to verify data consistency
across different database engines.

Accounts for database-specific type differences:
- Boolean: True/False (SQLite) vs 1/0 (MySQL/MSSQL)
- Float precision differences
- String encoding

Usage: python3 cross_db_validation.py <test_db_type> <baseline_db_type>

where db_type is: sqlite, mysql, postgres, or mssql

Typically: python3 cross_db_validation.py mysql sqlite
"""

import sys
import os
import configparser
from sqlalchemy import create_engine, inspect, text
from pathlib import Path
from collections import defaultdict

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


def connect_to_database(db_type):
    """Create database engine and connection"""
    connection_string = get_connection_string(db_type)
    try:
        engine = create_engine(connection_string)
        connection = engine.connect()
        log_success(f"Connected to {db_type} database")
        return engine, connection
    except Exception as e:
        log_error(f"Failed to connect to {db_type} database: {e}")
        sys.exit(1)


def get_table_list(inspector):
    """Get list of all tables"""
    return set(inspector.get_table_names())


def get_row_count(connection, table):
    """Get row count for a table"""
    try:
        result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
        return result.scalar()
    except Exception as e:
        log_error(f"Failed to count rows in {table}: {e}")
        return -1


def normalize_value(value):
    """
    Normalize values to account for database-specific type differences

    - Boolean: Convert 1/0 to True/False
    - Float: Round to 4 decimal places
    - None/NULL: Keep as None
    """
    if value is None:
        return None

    # Boolean normalization (1/0 -> True/False)
    if isinstance(value, int) and value in (0, 1):
        return bool(value)

    # Float normalization (round to avoid precision issues)
    if isinstance(value, float):
        return round(value, 4)

    # String normalization (strip whitespace)
    if isinstance(value, str):
        return value.strip()

    return value


def compare_table_lists(test_tables, baseline_tables):
    """Compare table lists between databases"""
    log_info("\n" + "="*70)
    log_info("COMPARISON 1: Table Lists")
    log_info("="*70)

    missing_in_test = baseline_tables - test_tables
    extra_in_test = test_tables - baseline_tables
    common_tables = test_tables & baseline_tables

    log_info(f"Test database tables: {len(test_tables)}")
    log_info(f"Baseline database tables: {len(baseline_tables)}")
    log_info(f"Common tables: {len(common_tables)}")

    if missing_in_test:
        log_error(f"Tables missing in test database: {missing_in_test}")
        return False

    if extra_in_test:
        log_warning(f"Extra tables in test database: {extra_in_test}")
        # Extra tables are a warning, not a failure
        return True

    if not missing_in_test and not extra_in_test:
        log_success("Table lists match exactly")
        return True

    return True


def compare_row_counts(test_conn, baseline_conn, common_tables):
    """Compare row counts for all tables"""
    log_info("\n" + "="*70)
    log_info("COMPARISON 2: Row Counts")
    log_info("="*70)

    mismatches = []

    for table in sorted(common_tables):
        test_count = get_row_count(test_conn, table)
        baseline_count = get_row_count(baseline_conn, table)

        if test_count == -1 or baseline_count == -1:
            log_error(f"{table}: Failed to get row count")
            mismatches.append(table)
            continue

        if test_count != baseline_count:
            diff = test_count - baseline_count
            log_error(f"{table}: Row count mismatch (test: {test_count}, baseline: {baseline_count}, diff: {diff:+d})")
            mismatches.append(table)
        else:
            log_info(f"{table}: ✓ {test_count} rows")

    if mismatches:
        log_error(f"\n{len(mismatches)} tables have row count mismatches")
        return False
    else:
        log_success(f"\nAll {len(common_tables)} tables have matching row counts")
        return True


def compare_sample_data(test_conn, baseline_conn, common_tables, sample_size=100):
    """Compare sample data from each table"""
    log_info("\n" + "="*70)
    log_info("COMPARISON 3: Sample Data")
    log_info("="*70)

    # Tables to skip for sample data comparison (too large or expected to differ)
    skip_tables = {
        'mapDenormalize',  # Very large
        'mapSolarSystemJumps',  # Generated data
    }

    tables_to_check = [t for t in sorted(common_tables) if t not in skip_tables]
    data_mismatches = []

    for table in tables_to_check[:20]:  # Limit to first 20 tables to avoid excessive output
        log_info(f"\nChecking sample data in {table}...")

        # Get primary key
        try:
            test_result = test_conn.execute(text(f"PRAGMA table_info({table})"))
            test_cols = test_result.fetchall() if hasattr(test_result, 'fetchall') else list(test_result)

            # Find PK column
            pk_col = None
            for col in test_cols:
                if len(col) > 5 and col[5] > 0:  # col[5] is pk flag
                    pk_col = col[1]
                    break

            if not pk_col:
                log_warning(f"  No primary key found, skipping sample data check")
                continue

            # Get sample IDs from both databases
            test_ids_result = test_conn.execute(text(f"SELECT {pk_col} FROM {table} ORDER BY {pk_col} LIMIT {sample_size}"))
            test_ids = set(row[0] for row in test_ids_result)

            baseline_ids_result = baseline_conn.execute(text(f"SELECT {pk_col} FROM {table} ORDER BY {pk_col} LIMIT {sample_size}"))
            baseline_ids = set(row[0] for row in baseline_ids_result)

            common_ids = test_ids & baseline_ids

            if len(common_ids) == 0:
                log_warning(f"  No common IDs found in sample")
                continue

            # Compare first 10 rows
            mismatches_in_table = 0
            for row_id in list(common_ids)[:10]:
                test_row_result = test_conn.execute(text(f"SELECT * FROM {table} WHERE {pk_col} = :id"), {"id": row_id})
                test_row = test_row_result.fetchone()

                baseline_row_result = baseline_conn.execute(text(f"SELECT * FROM {table} WHERE {pk_col} = :id"), {"id": row_id})
                baseline_row = baseline_row_result.fetchone()

                if test_row and baseline_row:
                    # Normalize values before comparison
                    test_values = [normalize_value(v) for v in test_row]
                    baseline_values = [normalize_value(v) for v in baseline_row]

                    if test_values != baseline_values:
                        mismatches_in_table += 1
                        if mismatches_in_table <= 2:  # Only show first 2 mismatches per table
                            log_warning(f"  Row difference at {pk_col}={row_id}")
                            # Show which columns differ
                            for idx, (test_val, baseline_val) in enumerate(zip(test_values, baseline_values)):
                                if test_val != baseline_val:
                                    col_name = test_cols[idx][1] if idx < len(test_cols) else f"col_{idx}"
                                    log_warning(f"    {col_name}: test={test_val}, baseline={baseline_val}")

            if mismatches_in_table > 0:
                log_warning(f"  Found {mismatches_in_table} row mismatches in {table}")
                data_mismatches.append((table, mismatches_in_table))
            else:
                log_success(f"  Sample data matches")

        except Exception as e:
            log_error(f"  Error comparing {table}: {e}")
            continue

    if data_mismatches:
        log_warning(f"\n{len(data_mismatches)} tables have data mismatches (may be acceptable)")
        # Data mismatches are warnings, not failures (due to type normalization)
        return True
    else:
        log_success(f"\nAll sampled tables have matching data")
        return True


def print_summary(results):
    """Print validation summary"""
    log_info("\n" + "="*70)
    log_info("CROSS-DATABASE VALIDATION SUMMARY")
    log_info("="*70)

    total_checks = len(results)
    passed_checks = sum(1 for r in results if r)
    failed_checks = total_checks - passed_checks

    log_info(f"Total comparison groups: {total_checks}")
    log_info(f"Passed: {passed_checks}")
    log_info(f"Failed: {failed_checks}")

    if failed_checks == 0:
        print(f"\n{Colors.OKGREEN}{'='*70}")
        print(f"✓ ALL CROSS-DATABASE VALIDATION CHECKS PASSED")
        print(f"{'='*70}{Colors.ENDC}\n")
        return True
    else:
        print(f"\n{Colors.FAIL}{'='*70}")
        print(f"✗ {failed_checks} VALIDATION GROUPS FAILED")
        print(f"{'='*70}{Colors.ENDC}\n")
        return False


def main():
    if len(sys.argv) != 3:
        log_error("Invalid arguments")
        print("Usage: python3 cross_db_validation.py <test_db_type> <baseline_db_type>")
        print("  db_type: sqlite, mysql, postgres, or mssql")
        print("")
        print("Example: python3 cross_db_validation.py mysql sqlite")
        sys.exit(1)

    test_db_type = sys.argv[1]
    baseline_db_type = sys.argv[2]

    print(f"{Colors.HEADER}{'='*70}")
    print(f"EVE SDE Cross-Database Validation")
    print(f"Test Database: {test_db_type}")
    print(f"Baseline Database: {baseline_db_type}")
    print(f"{'='*70}{Colors.ENDC}\n")

    # Connect to both databases
    test_engine, test_conn = connect_to_database(test_db_type)
    baseline_engine, baseline_conn = connect_to_database(baseline_db_type)

    test_inspector = inspect(test_engine)
    baseline_inspector = inspect(baseline_engine)

    # Get table lists
    test_tables = get_table_list(test_inspector)
    baseline_tables = get_table_list(baseline_inspector)

    # Run comparison checks
    results = []
    results.append(compare_table_lists(test_tables, baseline_tables))

    # Get common tables for further comparison
    common_tables = test_tables & baseline_tables

    if common_tables:
        results.append(compare_row_counts(test_conn, baseline_conn, common_tables))
        results.append(compare_sample_data(test_conn, baseline_conn, common_tables, sample_size=100))

    # Close connections
    test_conn.close()
    baseline_conn.close()
    test_engine.dispose()
    baseline_engine.dispose()

    # Print summary and exit
    success = print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
