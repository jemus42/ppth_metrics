# Claude Code Instructions

This file contains instructions for Claude Code when working on this project.

## Project Overview

Prometheus exporter for the PPTH home server. Collects:

- System metrics (CPU%, memory%, CPU package temp)
- ZFS metrics (per-dataset used/avail/referenced bytes, ARC size + ceiling + hits/misses)
- Tautulli/Plex streaming metrics — **opt-in** via `ENABLE_TAUTULLI=true`; emits a `ppth_tautulli_up` gauge whenever enabled so a broken upstream is observable as 0, not silent absence

Jellyfin session / transcode / item-count metrics are deliberately **not** here — the community `drkhsh/jellyfin-exporter` already covers them on PPTH. See the vault note `infra/ppth/Jellyfin monitoring design.md` for the scope split.

Docker container resource metrics existed briefly in v0.1.x (commit `b365669` "Remove docker stuff b/c too slow") and were removed. Don't re-add without checking that commit's rationale.

## Version Management

### Current Version

- Stored in the `VERSION` file (and mirrored in `pyproject.toml`)
- Latest stable version: see `VERSION`

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
# Run on a non-prod port. ZFS/ARC need the kernel surfaces to exist (Linux + ZFS).
EXPORTER_PORT=8005 uv run python metrics.py

# Enable Tautulli probe (defaults off; emits ppth_tautulli_up regardless of reachability)
EXPORTER_PORT=8005 ENABLE_TAUTULLI=true TAUTULLI_URL=https://... TAUTULLI_API_KEY=... uv run python metrics.py
```

### Tests
```bash
uv run --group dev pytest tests/ -v
```
Parsers (`parse_zfs_list_output`, `parse_arcstats`) are pure functions covered by fixtures captured from PPTH. The HTTP layer is not unit-tested — verify via `curl -4 http://127.0.0.1:8005/metrics` (note the `-4`: `localhost` over IPv6 fails because the docker-proxy is v4-only on TrueNAS Scale).

### Docker Development
```bash
# Build and test locally
docker-compose -f docker-compose.local.yml build
docker-compose -f docker-compose.local.yml up -d

# Use production image
docker-compose up -d
```

## Important Notes

### TrueNAS Scale Deployment
- Image: `ghcr.io/jemus42/ppth_metrics:<tag>`. App is `prometheus-ppth` under TrueNAS Apps.
- ZFS metrics depend on the container being able to run `zfs list` and read `/proc/spl/kstat/zfs/arcstats`. The current app runs privileged enough for both; if either fails the collector logs and skips its block (the rest of the endpoint stays healthy).
- Tautulli stays off unless `ENABLE_TAUTULLI=true` is set in the app's env config.

### Metrics Format
- Manual text-format string-building, not the `prometheus_client` library. Keep `# HELP` / `# TYPE` lines, gauge vs counter naming convention (`_total` suffix for counters).
- Output ends with a trailing newline (POSIX).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `EXPORTER_PORT` | `8000` | Port to expose metrics |
| `EXPORTER_BIND_ADDRESS` | `0.0.0.0` | Bind address |
| `ENABLE_TAUTULLI` | `false` | Opt-in for the Tautulli scrape. When true, emits `ppth_tautulli_up` regardless of result. |
| `TAUTULLI_URL` | `http://localhost:8181` | Tautulli instance URL (only consulted when ENABLE_TAUTULLI is set) |
| `TAUTULLI_API_KEY` | (none) | Tautulli API key (only consulted when ENABLE_TAUTULLI is set) |