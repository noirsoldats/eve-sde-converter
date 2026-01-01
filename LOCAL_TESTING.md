# Local Testing Guide for GitHub Actions

This guide explains how to test the GitHub Actions workflows locally without pushing to GitHub.

## Prerequisites

- Docker installed and running
- Homebrew (macOS) or appropriate package manager

## Tools Overview

### 1. act - Run GitHub Actions Locally
The primary tool for executing workflows locally using Docker.

### 2. actionlint - Validate Workflow Syntax
Static checker that catches errors before execution.

### 3. docker-compose - Service Container Testing
Replicates the CI database service environment locally.

---

## Installation

### Install act
```bash
brew install act
```

### Install actionlint
```bash
brew install actionlint
```

### Verify Docker
```bash
docker --version
docker-compose --version
```

---

## Quick Start

### 1. Validate Workflow Syntax
Before running workflows, check for syntax errors:

```bash
actionlint .github/workflows/update-sde.yml
```

### 2. List Available Workflows
```bash
act -l
```

### 3. Run Specific Job
```bash
# Run the check-and-update-sde job
act -j check-and-update-sde

# Dry run to see what would happen
act -j check-and-update-sde -n
```

---

## Testing the Multi-Database Workflow

### Option A: Using act with Manual Service Containers

Since act has limited service container support, start databases manually first:

#### 1. Start Service Containers
```bash
# Start MySQL
docker run -d --name mysql-test \
  -e MYSQL_DATABASE=evesde \
  -e MYSQL_USER=evesde \
  -e MYSQL_PASSWORD=evesdepass \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -p 3306:3306 \
  --health-cmd="mysqladmin ping -h localhost" \
  --health-interval=10s \
  mysql:8.0

# Start PostgreSQL
docker run -d --name postgres-test \
  -e POSTGRES_DB=evesde \
  -e POSTGRES_USER=evesde \
  -e POSTGRES_PASSWORD=evesdepass \
  -p 5432:5432 \
  --health-cmd="pg_isready -U evesde" \
  --health-interval=10s \
  postgres:15

# Start MSSQL
docker run -d --name mssql-test \
  -e ACCEPT_EULA=Y \
  -e SA_PASSWORD='YourStrong!Passw0rd' \
  -e MSSQL_PID=Developer \
  -p 1433:1433 \
  mcr.microsoft.com/mssql/server:2022-latest

# Wait for services to be healthy
docker ps
```

#### 2. Run act
```bash
# Test specific matrix combination
act -j build-databases --matrix database.type:mysql -v

# Test all matrix combinations (runs sequentially)
act -j build-databases -v
```

#### 3. Cleanup
```bash
docker stop mysql-test postgres-test mssql-test
docker rm mysql-test postgres-test mssql-test
```

### Option B: Using docker-compose (Recommended)

Easier service management using the included docker-compose file.

#### 1. Start All Services
```bash
docker-compose -f docker-compose.test.yml up -d

# Check service health
docker-compose -f docker-compose.test.yml ps
```

#### 2. Test Manually
```bash
# Test MySQL conversion
python3 Load.py mysql en

# Test PostgreSQL conversion
python3 Load.py postgres en

# Test MSSQL conversion (create database first)
docker exec mssql-test /opt/mssql-tools/bin/sqlcmd \
  -S localhost -U sa -P 'YourStrong!Passw0rd' \
  -Q "CREATE DATABASE evesde"
python3 Load.py mssql en
```

#### 3. Test with act
```bash
act -j build-databases --matrix database.type:mysql -v
```

#### 4. Cleanup
```bash
docker-compose -f docker-compose.test.yml down -v
```

### Option C: Using the Test Script (Easiest)

Use the included test script for automated testing:

```bash
# Make script executable
chmod +x scripts/test-workflow-local.sh

# Run full test suite
./scripts/test-workflow-local.sh

# Test specific database
./scripts/test-workflow-local.sh mysql

# Cleanup only
./scripts/test-workflow-local.sh cleanup
```

---

## Testing Individual Components

### Test Check and Update Job
```bash
# This job checks for new SDE versions
act -j check-and-update-sde
```

### Test Matrix Builds
```bash
# Test SQLite build
act -j build-databases --matrix database.type:sqlite

# Test MySQL build (ensure MySQL container is running)
act -j build-databases --matrix database.type:mysql

# Test PostgreSQL build (ensure PostgreSQL container is running)
act -j build-databases --matrix database.type:postgresql

# Test MSSQL build (ensure MSSQL container is running)
act -j build-databases --matrix database.type:mssql
```

### Test Release Job
```bash
act -j create-release
```

---

## act Configuration

The `.actrc` file in the project root configures act behavior:

- Uses larger runner image with more pre-installed tools
- Sets default event trigger
- Enables verbose logging
- Configures artifact path

### Custom act Commands

```bash
# Use specific runner image
act -P ubuntu-latest=catthehacker/ubuntu:full-latest

# Set secrets
act -s GITHUB_TOKEN=your_token_here

# Use secrets file
act --secret-file .secrets

# Specify workflow file
act -W .github/workflows/update-sde.yml

# Trigger specific event
act workflow_dispatch

# Debug mode
act -v -j build-databases
```

---

## Troubleshooting

### MSSQL First-Time Startup

MSSQL 2022 containers can take up to 2 minutes on first startup to upgrade system databases. The setup script waits for the healthcheck to pass, but MSSQL may need a few extra seconds to complete authentication initialization.

**If you experience MSSQL login failures immediately after setup:**

```bash
# Wait 10-15 seconds and try again, or restart the container
docker restart eve-sde-mssql-test
sleep 30

# Test connection (note: password contains special characters, use carefully in shell)
docker exec eve-sde-mssql-test /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P YourStrong!Passw0rd -Q "SELECT 1" -C
```

**Note:** MSSQL tools are located at `/opt/mssql-tools18/bin/sqlcmd` (version 18) in the 2022 container. The `-C` flag disables certificate validation for local testing.

Subsequent startups will be much faster (~10-15 seconds).

### Service Container Connection Issues

If workflows can't connect to services, verify containers are running:

```bash
# Check container status
docker ps

# Check logs
docker logs mysql-test
docker logs postgres-test
docker logs mssql-test

# Test connection manually
docker exec mysql-test mysql -u evesde -pevesdepass -e "SELECT 1"
docker exec postgres-test psql -U evesde -d evesde -c "SELECT 1"
```

### act Not Finding Workflows

```bash
# List all available jobs
act -l

# Verify workflow syntax
actionlint .github/workflows/update-sde.yml
```

### Docker Permission Issues

```bash
# Ensure Docker daemon is running
docker info

# Check Docker group membership (Linux)
groups $USER
```

### Artifact Path Issues

act stores artifacts differently than GitHub. Check `.actrc` for artifact path configuration.

---

## Best Practices

1. **Always validate syntax first**: Run `actionlint` before `act`
2. **Start services before act**: Manual container startup is more reliable
3. **Use verbose mode**: `-v` flag helps debug issues
4. **Clean up containers**: Always stop and remove test containers
5. **Test incrementally**: Test individual jobs before full workflow
6. **Use docker-compose**: Easier service management for complex setups

---

## Limitations of Local Testing

### What Works
- ✅ Job execution logic
- ✅ Matrix strategies
- ✅ Environment variables
- ✅ Basic actions (checkout, setup-python, etc.)
- ✅ Shell scripts and commands

### What Doesn't Work Perfectly
- ❌ Service containers (need manual workaround)
- ❌ GitHub-specific contexts (github.token, etc.)
- ❌ Artifact upload/download between jobs
- ❌ Some third-party actions
- ❌ Secrets (need manual configuration)

### Workarounds
- Use manual Docker containers for services
- Mock GitHub context variables in `.actrc`
- Share artifacts via filesystem instead of upload/download
- Test third-party actions in actual GitHub Actions first

---

## Testing Workflow

Recommended testing sequence:

```bash
# 1. Validate syntax
actionlint .github/workflows/update-sde.yml

# 2. Start services
./scripts/test-workflow-local.sh setup

# 3. Test SQLite (no service needed)
act -j build-databases --matrix database.type:sqlite -v

# 4. Test MySQL
act -j build-databases --matrix database.type:mysql -v

# 5. Test PostgreSQL
act -j build-databases --matrix database.type:postgresql -v

# 6. Test MSSQL
act -j build-databases --matrix database.type:mssql -v

# 7. Cleanup
./scripts/test-workflow-local.sh cleanup
```

---

## GitHub Actions vs Local Testing

| Feature | GitHub Actions | Local (act) |
|---------|---------------|-------------|
| Execution Speed | 2-5 min | 5-20 sec |
| Service Containers | Native | Manual setup |
| Artifacts | Full support | Limited |
| Secrets | Encrypted | Manual config |
| Cost | CI minutes | Free |
| Matrix Builds | Parallel | Sequential |
| Debugging | Logs only | Interactive |

---

## Additional Resources

- [act Documentation](https://nektosact.com/)
- [act GitHub Repository](https://github.com/nektos/act)
- [actionlint Documentation](https://github.com/rhysd/actionlint)
- [GitHub Actions Service Containers](https://docs.github.com/actions/guides/creating-postgresql-service-containers)
- [Testing GitHub Actions Locally (Red Hat)](https://www.redhat.com/en/blog/testing-github-actions-locally)
