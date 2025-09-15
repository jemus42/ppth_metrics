# Claude Code Instructions

This file contains instructions for Claude Code when working on this project.

## Project Overview

This is a Prometheus metrics exporter that collects:
- System metrics (CPU, memory, temperature)
- Tautulli/Plex streaming metrics
- Docker container resource metrics (CPU, memory, network)

## Version Management

### Current Version
- Current version is stored in the `VERSION` file
- Latest stable version: `0.1.0`

### Creating New Versions

When implementing significant changes or fixes:

1. **Update the VERSION file:**
   ```bash
   echo "0.2.0" > VERSION
   ```

2. **Commit changes:**
   ```bash
   git add -A
   git commit -m "Release 0.2.0 - [describe changes]

   🤖 Generated with [Claude Code](https://claude.ai/code)

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

3. **Create and push git tag:**
   ```bash
   git tag v0.2.0
   git push --tags origin main
   ```

4. **GitHub Actions will automatically:**
   - Build multi-architecture Docker images (amd64, arm64)
   - Publish to `ghcr.io/jemus42/ppth_metrics` with tags:
     - `latest`
     - `0.2.0`
     - `v0.2.0`

### Version Semantics

Use semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes to metrics format or configuration
- **MINOR**: New features (new metrics, configuration options)
- **PATCH**: Bug fixes, improvements

## Development Commands

### Local Development
```bash
# Without Docker metrics (no permission issues)
EXPORTER_PORT=8005 ENABLE_DOCKER_METRICS=false uv run metrics.py

# With Docker metrics (requires sudo or docker group)
sudo EXPORTER_PORT=8005 ENABLE_DOCKER_METRICS=true uv run metrics.py
```

### Docker Development
```bash
# Build and test locally
docker-compose -f docker-compose.local.yml build
docker-compose -f docker-compose.local.yml up -d

# Use production image
docker-compose up -d
```

### Testing
```bash
# Test metrics endpoint
curl -4 http://localhost:8000/metrics

# Check for Docker metrics
curl -4 http://localhost:8000/metrics | grep docker_container

# Check for all metric types
curl -4 http://localhost:8000/metrics | grep "# TYPE"
```

## Important Notes

### Docker Configuration
- Container runs as root for Docker socket access
- Requires `/var/run/docker.sock:/var/run/docker.sock:ro` volume mount
- Uses proper error handling for missing CPU stats (common issue)

### TrueNAS Scale Deployment
- Uses `ghcr.io/jemus42/ppth_metrics:latest` by default
- Can pin to specific versions with `VERSION` environment variable
- Requires Docker socket access for container metrics

### Metrics Format
- All metrics include proper Prometheus TYPE and HELP annotations
- Output ends with trailing newline (POSIX compliant)
- Docker metrics include container and image labels

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TAUTULLI_URL` | `http://localhost:8181` | Tautulli instance URL |
| `TAUTULLI_API_KEY` | (none) | Tautulli API key |
| `EXPORTER_PORT` | `8000` | Port to expose metrics |
| `EXPORTER_BIND_ADDRESS` | `0.0.0.0` | Bind address |
| `ENABLE_DOCKER_METRICS` | `true` | Enable Docker metrics |
| `VERSION` | `latest` | Docker image version |