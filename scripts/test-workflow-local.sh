#!/bin/bash

# Local GitHub Actions Workflow Testing Script
# This script helps test the multi-database workflow locally using act and docker-compose

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.test.yml"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose is not installed. Please install docker-compose first."
        exit 1
    fi

    # Check act
    if ! command -v act &> /dev/null; then
        print_warning "act is not installed. Install with: brew install act"
        echo "You can still use this script for manual testing without act."
    fi

    # Check actionlint
    if ! command -v actionlint &> /dev/null; then
        print_warning "actionlint is not installed. Install with: brew install actionlint"
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi

    print_success "Prerequisites check complete"
}

# Function to validate workflow syntax
validate_workflow() {
    print_info "Validating workflow syntax..."

    if command -v actionlint &> /dev/null; then
        cd "$PROJECT_ROOT"
        if actionlint .github/workflows/update-sde.yml; then
            print_success "Workflow syntax is valid"
        else
            print_error "Workflow syntax validation failed"
            exit 1
        fi
    else
        print_warning "actionlint not found, skipping syntax validation"
    fi
}

# Function to start service containers
start_services() {
    print_info "Starting database service containers..."
    cd "$PROJECT_ROOT"

    docker-compose -f "$COMPOSE_FILE" up -d

    print_info "Waiting for services to be healthy..."

    # Wait for MySQL
    print_info "Waiting for MySQL..."
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker exec eve-sde-mysql-test mysqladmin ping -h localhost -u evesde -pevesdepass --silent 2>/dev/null; then
            print_success "MySQL is ready"
            break
        fi
        attempt=$((attempt + 1))
        if [ $attempt -eq $max_attempts ]; then
            print_error "MySQL failed to start after ${max_attempts} attempts"
            docker logs eve-sde-mysql-test
            exit 1
        fi
        sleep 2
    done

    # Wait for PostgreSQL
    print_info "Waiting for PostgreSQL..."
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker exec eve-sde-postgres-test pg_isready -U evesde -d evesde 2>/dev/null; then
            print_success "PostgreSQL is ready"
            break
        fi
        attempt=$((attempt + 1))
        if [ $attempt -eq $max_attempts ]; then
            print_error "PostgreSQL failed to start after ${max_attempts} attempts"
            docker logs eve-sde-postgres-test
            exit 1
        fi
        sleep 2
    done

    # Wait for MSSQL (takes longer to start - needs to upgrade system databases)
    print_info "Waiting for MSSQL (this may take up to 2 minutes)..."
    max_attempts_mssql=60  # MSSQL takes longer to start (2 minutes)
    attempt=0
    while [ $attempt -lt $max_attempts_mssql ]; do
        # Note: -C flag disables certificate validation for local testing
        if docker exec eve-sde-mssql-test /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "YourStrong!Passw0rd" -Q "SELECT 1" -C &> /dev/null; then
            print_success "MSSQL is ready"
            # Give MSSQL a few extra seconds to fully initialize authentication
            sleep 3
            break
        fi
        attempt=$((attempt + 1))
        if [ $attempt -eq $max_attempts_mssql ]; then
            print_error "MSSQL failed to start after ${max_attempts_mssql} attempts (2 minutes)"
            print_warning "MSSQL often takes longer on first startup while upgrading system databases"
            docker logs eve-sde-mssql-test | tail -50
            exit 1
        fi
        # Show progress every 10 attempts (20 seconds)
        if [ $((attempt % 10)) -eq 0 ]; then
            print_info "Still waiting for MSSQL... (${attempt}/${max_attempts_mssql} attempts)"
        fi
        sleep 2
    done

    # Create MSSQL database
    print_info "Creating MSSQL database..."
    docker exec eve-sde-mssql-test /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "YourStrong!Passw0rd" -Q "CREATE DATABASE evesde" -C || {
        print_warning "Database might already exist or creation failed"
    }

    print_success "All services are running and healthy"
    docker-compose -f "$COMPOSE_FILE" ps
}

# Function to stop and cleanup services
cleanup_services() {
    print_info "Stopping and removing service containers..."
    cd "$PROJECT_ROOT"

    docker-compose -f "$COMPOSE_FILE" down -v

    print_success "Cleanup complete"
}

# Function to test with act
test_with_act() {
    local db_type="$1"

    if ! command -v act &> /dev/null; then
        print_error "act is not installed. Cannot run workflow tests."
        print_info "Install act with: brew install act"
        return 1
    fi

    print_warning "NOTE: act testing requires the full workflow context."
    print_warning "The build-databases job depends on check-and-update-sde outputs."
    print_warning "For testing database conversions, use: $0 test-manual <db_type>"
    echo ""
    print_info "Testing full workflow with act..."
    cd "$PROJECT_ROOT"

    # Run the full workflow (not just build-databases)
    # This simulates a workflow_dispatch event
    act workflow_dispatch -v
}

# Function to test manually
test_manual() {
    local db_type="$1"

    # Handle 'all' option
    if [ "$db_type" = "all" ]; then
        print_info "Running all database conversions sequentially..."
        echo ""

        # Arrays to track results
        local -a successful_dbs=()
        local -a failed_dbs=()
        local -a error_messages=()

        for db in sqlite mysql postgres mssql; do
            print_info "================================================"
            print_info "Starting $db conversion..."
            print_info "================================================"
            echo ""

            # Run conversion and capture exit code (show output in real-time)
            # Use a temporary file to capture errors
            local error_log="/tmp/eve-sde-conversion-${db}-$$.log"

            if test_manual_single "$db" 2>"$error_log"; then
                successful_dbs+=("$db")
                echo ""
                print_success "Completed $db conversion"
                echo ""
                rm -f "$error_log"
            else
                local exit_code=$?
                failed_dbs+=("$db")
                # Capture last 20 lines of error for summary
                local error_summary=$(tail -20 "$error_log" 2>/dev/null || echo "No error output captured")
                error_messages+=("$db|$error_summary")
                echo ""
                print_error "Failed $db conversion (exit code: $exit_code)"
                echo ""
                rm -f "$error_log"
            fi
        done

        # Print summary
        echo ""
        echo "========================================"
        print_info "CONVERSION SUMMARY"
        echo "========================================"
        echo ""

        if [ ${#successful_dbs[@]} -gt 0 ]; then
            print_success "Successful conversions (${#successful_dbs[@]}/4):"
            for db in "${successful_dbs[@]}"; do
                echo "  ✓ $db"
            done
            echo ""
        fi

        if [ ${#failed_dbs[@]} -gt 0 ]; then
            print_error "Failed conversions (${#failed_dbs[@]}/4):"
            for db in "${failed_dbs[@]}"; do
                echo "  ✗ $db"
            done
            echo ""

            print_error "Error details:"
            for error_msg in "${error_messages[@]}"; do
                local db_name="${error_msg%%|*}"
                local error_text="${error_msg#*|}"
                echo ""
                print_error "[$db_name] Last 20 lines of error:"
                echo "$error_text"
            done
            echo ""
        fi

        if [ ${#successful_dbs[@]} -gt 0 ]; then
            print_info "Generated files:"
            ls -lh eve*.db eve*.sql.gz 2>/dev/null || print_warning "No output files found"
        fi

        echo ""

        # Return error if any conversion failed
        if [ ${#failed_dbs[@]} -gt 0 ]; then
            print_error "Overall status: FAILED (${#failed_dbs[@]} of 4 conversions failed)"
            return 1
        else
            print_success "Overall status: SUCCESS (all 4 conversions completed)"
            return 0
        fi
    fi

    test_manual_single "$db_type"
}

# Function to test a single database manually
test_manual_single() {
    local db_type="$1"

    print_info "Testing database conversion manually: $db_type"
    cd "$PROJECT_ROOT"

    # Check for virtual environment and activate it
    if [ -d ".venv" ]; then
        print_info "Activating Python virtual environment..."
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        print_info "Activating Python virtual environment..."
        source venv/bin/activate
    else
        print_warning "No virtual environment found. Using system Python."
    fi

    # Check if SDE directory exists
    if [ ! -d "sde" ]; then
        print_error "SDE directory not found. Please download the SDE first:"
        print_info "Run: ./runconversion.sh"
        print_info "Or manually download from https://developers.eveonline.com/resource/resources"
        exit 1
    fi

    case "$db_type" in
        sqlite)
            print_info "Running SQLite conversion..."
            if ! python3 Load.py sqlite en --create-stripped; then
                print_error "SQLite conversion failed"
                return 1
            fi
            print_success "SQLite conversion complete"
            ls -lh eve*.db
            ;;
        mysql)
            print_info "Running MySQL conversion..."
            if ! python3 Load.py mysql en; then
                print_error "MySQL conversion failed"
                return 1
            fi
            print_success "MySQL conversion complete"

            # Export to SQL dump
            print_info "Exporting MySQL database to SQL dump..."
            if ! docker exec eve-sde-mysql-test mysqldump \
                --host=localhost \
                --user=evesde \
                --password=evesdepass \
                --single-transaction \
                --quick \
                --lock-tables=false \
                --no-tablespaces \
                --routines \
                --triggers \
                --events \
                evesde > eve-mysql.sql; then
                print_error "MySQL export failed"
                return 1
            fi

            print_info "Compressing SQL dump..."
            if ! gzip -f eve-mysql.sql; then
                print_error "MySQL compression failed"
                return 1
            fi
            print_success "MySQL export complete: eve-mysql.sql.gz"
            ls -lh eve-mysql.sql.gz
            ;;
        postgres)
            print_info "Running PostgreSQL conversion..."
            if ! python3 Load.py postgres en; then
                print_error "PostgreSQL conversion failed"
                return 1
            fi
            print_success "PostgreSQL conversion complete"

            # Export to SQL dump
            print_info "Exporting PostgreSQL database to SQL dump..."
            if ! docker exec eve-sde-postgres-test pg_dump \
                --host=localhost \
                --username=evesde \
                --format=plain \
                --no-owner \
                --no-privileges \
                --clean \
                --if-exists \
                evesde > eve-postgresql.sql; then
                print_error "PostgreSQL export failed"
                return 1
            fi

            print_info "Compressing SQL dump..."
            if ! gzip -f eve-postgresql.sql; then
                print_error "PostgreSQL compression failed"
                return 1
            fi
            print_success "PostgreSQL export complete: eve-postgresql.sql.gz"
            ls -lh eve-postgresql.sql.gz
            ;;
        mssql)
            print_info "Running MSSQL conversion..."
            if ! python3 Load.py mssql en; then
                print_error "MSSQL conversion failed"
                return 1
            fi
            print_success "MSSQL conversion complete"

            # Export to SQL dump using mssql-scripter
            print_info "Checking if mssql-scripter is installed..."
            if ! command -v mssql-scripter &> /dev/null; then
                print_warning "mssql-scripter not found, installing..."
                if ! pip install -q mssql-scripter; then
                    print_error "Failed to install mssql-scripter"
                    return 1
                fi
            fi

            print_info "Exporting MSSQL database to SQL dump..."
            # mssql-scripter requires absolute path and directory must exist
            local mssql_output="$PROJECT_ROOT/eve-mssql.sql"
            if ! mssql-scripter \
                -S 127.0.0.1 \
                -U sa \
                -P 'YourStrong!Passw0rd' \
                -d evesde \
                --schema-and-data \
                --script-create \
                --file-path "$mssql_output"; then
                print_error "MSSQL export failed"
                return 1
            fi

            print_info "Compressing SQL dump..."
            if ! gzip -f eve-mssql.sql; then
                print_error "MSSQL compression failed"
                return 1
            fi
            print_success "MSSQL export complete: eve-mssql.sql.gz"
            ls -lh eve-mssql.sql.gz
            ;;
        *)
            print_error "Unknown database type: $db_type"
            print_info "Valid types: sqlite, mysql, postgres, mssql"
            return 1
            ;;
    esac
}

# Function to show service logs
show_logs() {
    local service="$1"
    cd "$PROJECT_ROOT"

    if [ -n "$service" ]; then
        docker-compose -f "$COMPOSE_FILE" logs "$service"
    else
        docker-compose -f "$COMPOSE_FILE" logs
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Local GitHub Actions workflow testing script for EVE SDE Converter

COMMANDS:
    setup               Start database service containers
    cleanup             Stop and remove all service containers
    validate            Validate workflow syntax with actionlint
    test-act            Run full workflow with act (workflow_dispatch event)
    test-manual DB      Run database conversion manually (RECOMMENDED for testing)
    logs [SERVICE]      Show logs for service containers
    status              Show status of service containers
    help                Show this help message

DATABASE TYPES:
    sqlite              SQLite database (no service needed)
    mysql               MySQL database
    postgres            PostgreSQL database
    mssql               Microsoft SQL Server
    all                 Run all database conversions sequentially

EXAMPLES:
    $0 setup                    # Start all database services
    $0 validate                 # Check workflow syntax
    $0 test-manual postgres     # Test PostgreSQL conversion manually (creates SQL dump)
    $0 test-manual all          # Test all database conversions sequentially
    $0 test-act                 # Test full workflow with act (requires SDE download)
    $0 logs mysql               # Show MySQL container logs
    $0 cleanup                  # Stop and remove all containers

OUTPUTS:
    test-manual sqlite          # Creates: eve.db, eve-stripped.db
    test-manual mysql           # Creates: eve-mysql.sql.gz
    test-manual postgres        # Creates: eve-postgresql.sql.gz
    test-manual mssql           # Creates: eve-mssql.sql.gz
    test-manual all             # Creates: all of the above

FULL WORKFLOW:
    $0 validate                 # 1. Validate syntax
    $0 setup                    # 2. Start services
    $0 test-manual mysql        # 3. Test manually (creates SQL dump)
    $0 cleanup                  # 4. Cleanup

NOTE:
    - test-manual is RECOMMENDED for testing database conversions
    - test-act runs the full GitHub Actions workflow (including SDE download)
    - test-act may take 20+ minutes and download ~500MB of SDE data

EOF
}

# Main script logic
main() {
    local command="${1:-help}"
    local option="$2"

    case "$command" in
        setup)
            check_prerequisites
            start_services
            ;;
        cleanup)
            cleanup_services
            ;;
        validate)
            validate_workflow
            ;;
        test-act)
            check_prerequisites
            test_with_act "$option"
            ;;
        test-manual)
            if [ -z "$option" ]; then
                print_error "Database type required for manual test"
                print_info "Usage: $0 test-manual [sqlite|mysql|postgres|mssql|all]"
                exit 1
            fi
            check_prerequisites
            test_manual "$option"
            ;;
        logs)
            show_logs "$option"
            ;;
        status)
            cd "$PROJECT_ROOT"
            docker-compose -f "$COMPOSE_FILE" ps
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
