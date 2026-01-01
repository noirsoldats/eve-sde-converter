# Quick Start: Local GitHub Actions Testing

Get started testing your GitHub Actions workflows locally in under 5 minutes.

## Installation

```bash
# Install act and actionlint
brew install act actionlint

# Make test script executable
chmod +x scripts/test-workflow-local.sh

# Verify Docker is running
docker info
```

## Testing in 3 Steps

### Step 1: Validate Syntax
```bash
./scripts/test-workflow-local.sh validate
```

### Step 2: Start Database Services
```bash
./scripts/test-workflow-local.sh setup
```

This starts MySQL, PostgreSQL, and MSSQL containers in the background.

### Step 3: Test a Database Conversion
```bash
# Test MySQL manually
./scripts/test-workflow-local.sh test-manual mysql

# Or test with act
./scripts/test-workflow-local.sh test-act mysql
```

## Cleanup
```bash
./scripts/test-workflow-local.sh cleanup
```

## Common Commands

```bash
# Show all available commands
./scripts/test-workflow-local.sh help

# Check service status
./scripts/test-workflow-local.sh status

# View logs
./scripts/test-workflow-local.sh logs mysql

# Test each database type
./scripts/test-workflow-local.sh test-manual sqlite
./scripts/test-workflow-local.sh test-manual mysql
./scripts/test-workflow-local.sh test-manual postgres
./scripts/test-workflow-local.sh test-manual mssql
```

## Files Created

- **LOCAL_TESTING.md** - Complete testing documentation
- **.actrc** - act configuration file
- **docker-compose.test.yml** - Database service containers
- **scripts/test-workflow-local.sh** - Test automation script
- **.secrets.example** - Example secrets file (copy to .secrets if needed)

## Next Steps

For detailed documentation, see [LOCAL_TESTING.md](LOCAL_TESTING.md)
