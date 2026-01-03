#!/bin/bash
#
# Database Export Script for EVE SDE Converter
#
# Exports populated databases to SQL dump files with gzip compression
# Supports MySQL, PostgreSQL, and MSSQL
#
# Usage: export_database.sh <db_type> <connection_string> <output_file>
#
# Examples:
#   ./export_database.sh mysql "mysql+pymysql://user:pass@host/db" "eve-mysql.sql.gz"
#   ./export_database.sh postgresql "postgresql+psycopg2://user:pass@host/db" "eve-postgresql.sql.gz"
#   ./export_database.sh mssql "mssql+pymssql://user:pass@host/db" "eve-mssql.sql.gz"
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ $# -ne 3 ]; then
    log_error "Invalid number of arguments"
    echo "Usage: $0 <db_type> <connection_string> <output_file>"
    echo ""
    echo "Arguments:"
    echo "  db_type           - Database type: mysql, postgresql, or mssql"
    echo "  connection_string - SQLAlchemy connection string"
    echo "  output_file       - Output file path (e.g., eve-mysql.sql.gz)"
    exit 1
fi

DB_TYPE="$1"
CONNECTION_STRING="$2"
OUTPUT_FILE="$3"

log_info "Exporting $DB_TYPE database to $OUTPUT_FILE"

# Parse connection string to extract credentials and database info
# SQLAlchemy format: dialect+driver://username:password@host:port/database?options

# Extract components using regex
if [[ $CONNECTION_STRING =~ ([^:]+)://([^:]+):([^@]+)@([^:/]+):?([0-9]*)/([^?]+)(\?.*)?$ ]]; then
    PROTOCOL="${BASH_REMATCH[1]}"
    USERNAME="${BASH_REMATCH[2]}"
    PASSWORD="${BASH_REMATCH[3]}"
    HOST="${BASH_REMATCH[4]}"
    PORT="${BASH_REMATCH[5]}"
    DATABASE="${BASH_REMATCH[6]}"
    OPTIONS="${BASH_REMATCH[7]}"
else
    log_error "Failed to parse connection string"
    log_error "Expected format: dialect+driver://username:password@host:port/database"
    exit 1
fi

# Set default ports if not specified
if [ -z "$PORT" ]; then
    case "$DB_TYPE" in
        mysql)
            PORT=3306
            ;;
        postgresql)
            PORT=5432
            ;;
        mssql)
            PORT=1433
            ;;
    esac
fi

log_info "Database: $DATABASE"
log_info "Host: $HOST:$PORT"
log_info "Username: $USERNAME"

# Clean up partial file on exit if script fails
cleanup() {
    if [ $? -ne 0 ] && [ -f "$OUTPUT_FILE" ]; then
        log_warning "Cleaning up partial file: $OUTPUT_FILE"
        rm -f "$OUTPUT_FILE"
    fi
}
trap cleanup EXIT

# Export based on database type
case "$DB_TYPE" in
    mysql)
        log_info "Using mysqldump to export MySQL database..."

        # Check if mysqldump is available
        if ! command -v mysqldump &> /dev/null; then
            log_error "mysqldump command not found. Please install mysql-client."
            exit 1
        fi

        # Export with mysqldump
        # --single-transaction: Consistent snapshot without locking
        # --quick: Retrieve rows one at a time (memory efficient)
        # --no-tablespaces: Skip tablespace info (not needed for import)
        # --skip-lock-tables: Don't lock tables (works with single-transaction)
        # --set-gtid-purged=OFF: Don't include GTID info (causes import issues)
        mysqldump \
            -h "$HOST" \
            -P "$PORT" \
            -u "$USERNAME" \
            -p"$PASSWORD" \
            --single-transaction \
            --quick \
            --no-tablespaces \
            --skip-lock-tables \
            --set-gtid-purged=OFF \
            "$DATABASE" | gzip > "$OUTPUT_FILE"

        log_success "MySQL export completed"
        ;;

    postgresql)
        log_info "Using pg_dump to export PostgreSQL database..."

        # Check if pg_dump is available
        if ! command -v pg_dump &> /dev/null; then
            log_error "pg_dump command not found. Please install postgresql-client."
            exit 1
        fi

        # Set password via environment variable
        export PGPASSWORD="$PASSWORD"

        # Export with pg_dump
        # --format=plain: SQL script format
        # --clean: Include DROP statements
        # --if-exists: Use IF EXISTS with DROP
        # --no-owner: Don't set ownership
        # --no-acl: Don't dump privileges
        pg_dump \
            -h "$HOST" \
            -p "$PORT" \
            -U "$USERNAME" \
            --format=plain \
            --clean \
            --if-exists \
            --no-owner \
            --no-acl \
            "$DATABASE" | gzip > "$OUTPUT_FILE"

        # Unset password
        unset PGPASSWORD

        log_success "PostgreSQL export completed"
        ;;

    mssql)
        log_info "Using mssql-scripter to export MSSQL database..."

        # Check if mssql-scripter is available
        if ! command -v mssql-scripter &> /dev/null; then
            log_error "mssql-scripter command not found. Please install mssql-scripter via pip."
            exit 1
        fi

        # Export with mssql-scripter
        # --schema-and-data: Include both schema and data
        # --exclude-use-database: Don't include USE DATABASE statement
        # --check-for-existence: Add IF EXISTS checks
        # --target-server-version: Set to 2016 for compatibility
        mssql-scripter \
            -S "$HOST,$PORT" \
            -u "$USERNAME" \
            -p "$PASSWORD" \
            -d "$DATABASE" \
            --schema-and-data \
            --exclude-use-database \
            --check-for-existence \
            --target-server-version 2016 | gzip > "$OUTPUT_FILE"

        log_success "MSSQL export completed"
        ;;

    *)
        log_error "Unsupported database type: $DB_TYPE"
        log_error "Supported types: mysql, postgresql, mssql"
        exit 1
        ;;
esac

# Verify output file exists and has content
if [ ! -f "$OUTPUT_FILE" ]; then
    log_error "Output file was not created: $OUTPUT_FILE"
    exit 1
fi

FILE_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null)
if [ "$FILE_SIZE" -eq 0 ]; then
    log_error "Output file is empty: $OUTPUT_FILE"
    exit 1
fi

# Convert bytes to human-readable format
if [ "$FILE_SIZE" -lt 1024 ]; then
    SIZE_HUMAN="${FILE_SIZE}B"
elif [ "$FILE_SIZE" -lt 1048576 ]; then
    SIZE_HUMAN="$(($FILE_SIZE / 1024))KB"
else
    SIZE_HUMAN="$(($FILE_SIZE / 1048576))MB"
fi

log_success "Export successful!"
log_info "Output file: $OUTPUT_FILE"
log_info "File size: $SIZE_HUMAN ($FILE_SIZE bytes)"

# Add metadata comment
log_info "Metadata: Build $BUILD_NUMBER, Database type: $DB_TYPE, Export date: $(date)"

exit 0
