# PPTH Metrics Exporter

Prometheus exporter for the PPTH home server. Emits ZFS / ARC / system metrics plus an optional Tautulli scrape.

## What it exports

### System
- `ppth_system_cpu_percent` — gauge, CPU usage %
- `ppth_system_memory_percent` — gauge, RAM usage %. On a ZFS host this looks alarmingly high; pair with the ARC gauges below for the real picture.
- `ppth_system_cpu_package_temp` — gauge, CPU package °C (when `sensors_temperatures()` returns `coretemp`)

### ZFS — per-dataset
- `ppth_zfs_used_bytes{dataset="..."}` — gauge
- `ppth_zfs_avail_bytes{dataset="..."}` — gauge
- `ppth_zfs_referenced_bytes{dataset="..."}` — gauge

### ZFS — ARC (read-cache state)
- `ppth_zfs_arc_size_bytes` — current footprint
- `ppth_zfs_arc_c_max_bytes` — RAM ceiling the ARC may grow to
- `ppth_zfs_arc_c_bytes` — current auto-tuned target size
- `ppth_zfs_arc_data_size_bytes`, `ppth_zfs_arc_metadata_size_bytes` — split of `size`
- `ppth_zfs_arc_hits_total`, `ppth_zfs_arc_misses_total` — cumulative counters

The `size` vs `c_max` ratio is the useful one: it tells you how full the ARC is relative to its allowed maximum.

### Tautulli/Plex (opt-in)
Off by default. Set `ENABLE_TAUTULLI=true` to enable.

- `ppth_tautulli_up{instance="..."}` — gauge, `1` if the scrape returned 200, else `0`. Emitted **whenever the integration is enabled**, regardless of upstream health, so a broken Tautulli is observable rather than silent.
- `plex_streams_total`, `plex_streams_direct_play`, `plex_streams_direct_stream`, `plex_streams_transcode` — gauges, only emitted when `up == 1`.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `EXPORTER_PORT` | `8000` | Port to expose metrics |
| `EXPORTER_BIND_ADDRESS` | `0.0.0.0` | Bind address |
| `ENABLE_TAUTULLI` | `false` | Opt-in for the Tautulli scrape |
| `TAUTULLI_URL` | `http://localhost:8181` | Tautulli URL (consulted only when enabled) |
| `TAUTULLI_API_KEY` | (none) | Tautulli API key (consulted only when enabled) |

## Running

### Pre-built image (recommended)
```bash
docker-compose up -d
# metrics at http://localhost:8000/metrics
```

### Local development
```bash
EXPORTER_PORT=8005 uv run python metrics.py
curl -4 http://127.0.0.1:8005/metrics
```
The `-4` matters on TrueNAS Scale: `localhost` over IPv6 hits the docker-proxy on a non-bound interface and fails.

### Tests
```bash
uv run --group dev pytest tests/ -v
```
Parsers are unit-tested against real captures from PPTH. The HTTP layer is verified by hand with `curl`.

## TrueNAS Scale deployment

Image: `ghcr.io/jemus42/ppth_metrics:<tag>`. Deployed as the `prometheus-ppth` custom app. ZFS metrics require the container to be able to `zfs list` and read `/proc/spl/kstat/zfs/arcstats` — the current app config grants that; if either fails the collector logs and skips its block while the rest of the endpoint stays healthy.

## Releasing

1. `echo "X.Y.Z" > VERSION` and bump `version` in `pyproject.toml`
2. `git commit -am "Release vX.Y.Z - ..."`
3. `git tag vX.Y.Z && git push --tags origin main`
4. GitHub Actions builds and publishes multi-arch images to `ghcr.io/jemus42/ppth_metrics:{latest,X.Y.Z,vX.Y.Z}`

Semver: MAJOR = breaking metric/config; MINOR = new metrics or env vars; PATCH = bug fixes.

## Scope

Jellyfin session / transcode / item-count metrics are **not** in scope here — the community `drkhsh/jellyfin-exporter` already covers them on PPTH. The next thing this exporter wants is per-library byte counts (mtime-gated filesystem walk under `/mnt/Primary/media/`); see the vault note `infra/ppth/Jellyfin monitoring design.md`.
