# PPTH Metrics Exporter

A Prometheus exporter that collects system metrics and Tautulli/Plex streaming metrics.

## Features

- System metrics (CPU usage, memory usage, CPU temperature)
- Tautulli/Plex streaming metrics (total streams, direct play, direct stream, transcode)
- Prometheus-compatible output with TYPE and HELP annotations
- Docker support for easy deployment
- Environment variable configuration
- Multi-architecture Docker images (amd64, arm64)

## Quick Start

### Using Pre-built Docker Image (Recommended)

1. Copy the environment file and configure it:
```bash
cp .env.example .env
# Edit .env with your Tautulli URL and API key
```

2. Run with the pre-built image:
```bash
docker-compose up -d
```

3. Access metrics at: `http://localhost:8000/metrics`

### Local Development

For local development with building from source:
```bash
docker-compose -f docker-compose.local.yml up --build
```

## Configuration

All configuration is done via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TAUTULLI_URL` | URL of your Tautulli instance | `http://localhost:8181` |
| `TAUTULLI_API_KEY` | API key from Tautulli settings | (none - Plex metrics disabled) |
| `EXPORTER_PORT` | Port to expose metrics | `8000` |
| `EXPORTER_BIND_ADDRESS` | Bind address for the exporter | `0.0.0.0` |

## Deployment on TrueNAS Scale

For TrueNAS Scale custom app deployment:

1. Use the pre-built Docker image from GitHub Container Registry:
   - Image: `ghcr.io/jemus42/ppth_metrics:latest`
   
2. Set environment variables through the TrueNAS UI:
   - `TAUTULLI_URL`: Your Tautulli instance URL
   - `TAUTULLI_API_KEY`: Your Tautulli API key
   - `EXPORTER_PORT`: Port for metrics (default 8000)

3. Map port 8000 (or your chosen port) to access metrics

4. Consider using host networking if you need to:
   - Access a Tautulli instance running on the host
   - Get accurate host system metrics (CPU temp may not work in containers)

## Publishing to GitHub Container Registry

This repository includes GitHub Actions to automatically build and publish Docker images:

1. Push your code to GitHub:
```bash
git remote add origin https://github.com/jemus42/ppth_metrics.git
git push -u origin main
```

2. The image will be automatically built and published on:
   - Every push to main/master branch (tagged as `latest`)
   - Every tag push (e.g., `v1.0.0`)

3. Make the package public in your GitHub package settings for anonymous pulls

The workflow builds multi-architecture images (amd64 and arm64) for broad compatibility.

## Metrics Exported

### Plex/Tautulli Metrics
- `plex_streams_total` - Total number of active Plex streams
- `plex_streams_direct_play` - Number of streams using direct play
- `plex_streams_direct_stream` - Number of streams using direct stream
- `plex_streams_transcode` - Number of streams using transcoding

### System Metrics
- `ppth_system_cpu_percent` - CPU usage percentage
- `ppth_system_memory_percent` - Memory usage percentage
- `ppth_system_cpu_package_temp` - CPU package temperature in Celsius (if available)

## Development

Run locally with Python:
```bash
pip install -r requirements.txt
export TAUTULLI_API_KEY=your_api_key_here
export TAUTULLI_URL=http://your-tautulli:8181
python metrics.py
```

Or with uv:
```bash
export TAUTULLI_API_KEY=your_api_key_here
export TAUTULLI_URL=http://your-tautulli:8181
uv run metrics.py
```

## Docker Image Tags

- `latest` - Latest stable release from main/master branch
- `0.1.0` - Current stable version
- `v*.*.*` - Specific version tags (e.g., v0.1.0)
- `main`/`master` - Latest commit from the main branch

## Version Management

To update to a specific version in TrueNAS Scale:

1. **Set the VERSION environment variable:**
   ```bash
   VERSION=0.1.0
   ```

2. **Or update your .env file:**
   ```bash
   echo "VERSION=0.1.0" >> .env
   ```

3. **Pull the new version:**
   ```bash
   docker-compose pull && docker-compose up -d
   ```