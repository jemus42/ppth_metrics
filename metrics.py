from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import psutil
import requests
import os


# ─── Parsers (pure functions, unit-tested) ──────────────────────────────────

def parse_zfs_list_output(text):
    """Parse `zfs list -p -H -o name,used,avail,referenced` tab-separated output.

    Returns a list of dicts. Skips blank lines so trailing newlines don't
    produce an empty trailing row.
    """
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        name, used, avail, referenced = line.split("\t")
        rows.append({
            "name": name,
            "used": int(used),
            "avail": int(avail),
            "referenced": int(referenced),
        })
    return rows


def parse_arcstats(text):
    """Parse /proc/spl/kstat/zfs/arcstats — two-line preamble then `name type value`.

    Drops the `name type data` column-header line.
    """
    stats = {}
    for line in text.splitlines()[2:]:
        parts = line.split()
        if len(parts) != 3:
            continue
        try:
            stats[parts[0]] = int(parts[2])
        except ValueError:
            continue
    return stats


# ─── Collectors (each returns a list of Prometheus text-format lines) ───────

def collect_system():
    lines = [
        "# HELP ppth_system_cpu_percent CPU usage percentage",
        "# TYPE ppth_system_cpu_percent gauge",
        f"ppth_system_cpu_percent {psutil.cpu_percent()}",
        "# HELP ppth_system_memory_percent Memory usage percentage",
        "# TYPE ppth_system_memory_percent gauge",
        f"ppth_system_memory_percent {psutil.virtual_memory().percent}",
    ]
    try:
        temps = psutil.sensors_temperatures()
        if temps and "coretemp" in temps and len(temps["coretemp"]) > 1:
            lines += [
                "# HELP ppth_system_cpu_package_temp CPU package temperature in Celsius",
                "# TYPE ppth_system_cpu_package_temp gauge",
                f"ppth_system_cpu_package_temp {temps['coretemp'][1].current}",
            ]
    except Exception as e:
        print(f"Could not read CPU temperature: {e}")
    return lines


def collect_zfs():
    """Per-dataset bytes and ARC stats. Pure shell-out + file read, no API."""
    lines = []
    try:
        out = subprocess.check_output(
            ["zfs", "list", "-p", "-H", "-o", "name,used,avail,referenced"],
            text=True, timeout=5,
        )
        rows = parse_zfs_list_output(out)
        lines += [
            "# HELP ppth_zfs_used_bytes Bytes used by the dataset",
            "# TYPE ppth_zfs_used_bytes gauge",
        ]
        lines += [f'ppth_zfs_used_bytes{{dataset="{r["name"]}"}} {r["used"]}' for r in rows]
        lines += [
            "# HELP ppth_zfs_avail_bytes Bytes available in the dataset's pool",
            "# TYPE ppth_zfs_avail_bytes gauge",
        ]
        lines += [f'ppth_zfs_avail_bytes{{dataset="{r["name"]}"}} {r["avail"]}' for r in rows]
        lines += [
            "# HELP ppth_zfs_referenced_bytes Bytes referenced by the dataset",
            "# TYPE ppth_zfs_referenced_bytes gauge",
        ]
        lines += [f'ppth_zfs_referenced_bytes{{dataset="{r["name"]}"}} {r["referenced"]}' for r in rows]
    except Exception as e:
        print(f"zfs list failed: {e}")

    try:
        with open("/proc/spl/kstat/zfs/arcstats") as f:
            stats = parse_arcstats(f.read())
        # Headline ARC counters worth dashboards: current size, ceiling, hit/miss totals.
        # data_size + metadata_size together explain "what is the ARC currently holding".
        emit = {
            "size": "Current ARC size in bytes",
            "c_max": "ARC target maximum size in bytes",
            "c": "ARC target size in bytes (auto-tuned)",
            "data_size": "Bytes of ARC consumed by data blocks",
            "metadata_size": "Bytes of ARC consumed by metadata blocks",
            "hits": "Cumulative ARC hits",
            "misses": "Cumulative ARC misses",
        }
        for key, help_text in emit.items():
            if key in stats:
                metric = f"ppth_zfs_arc_{key}_bytes" if key in ("size", "c_max", "c", "data_size", "metadata_size") else f"ppth_zfs_arc_{key}_total"
                mtype = "gauge" if metric.endswith("_bytes") else "counter"
                lines += [
                    f"# HELP {metric} {help_text}",
                    f"# TYPE {metric} {mtype}",
                    f"{metric} {stats[key]}",
                ]
    except Exception as e:
        print(f"arcstats read failed: {e}")
    return lines


def collect_tautulli():
    """Gated on ENABLE_TAUTULLI=true. Always emits ppth_tautulli_up when enabled
    so a broken upstream is observable as a gauge=0, not silent absence."""
    if os.getenv("ENABLE_TAUTULLI", "false").lower() not in ("1", "true", "yes"):
        return []
    url = os.getenv("TAUTULLI_URL", "http://localhost:8181")
    api_key = os.getenv("TAUTULLI_API_KEY", "")
    up = 0
    lines = []
    if not api_key:
        print("ENABLE_TAUTULLI set but TAUTULLI_API_KEY missing; emitting up=0")
    else:
        try:
            r = requests.get(
                f"{url}/api/v2",
                params={"apikey": api_key, "cmd": "get_activity"},
                timeout=5,
            )
            if r.status_code == 200:
                data = r.json()["response"]["data"] or {}
                up = 1
                lines += [
                    "# HELP plex_streams_total Total number of active Plex streams",
                    "# TYPE plex_streams_total gauge",
                    f"plex_streams_total {data.get('stream_count', 0)}",
                    "# HELP plex_streams_direct_play Plex streams using direct play",
                    "# TYPE plex_streams_direct_play gauge",
                    f"plex_streams_direct_play {data.get('stream_count_direct_play', 0)}",
                    "# HELP plex_streams_direct_stream Plex streams using direct stream",
                    "# TYPE plex_streams_direct_stream gauge",
                    f"plex_streams_direct_stream {data.get('stream_count_direct_stream', 0)}",
                    "# HELP plex_streams_transcode Plex streams using transcoding",
                    "# TYPE plex_streams_transcode gauge",
                    f"plex_streams_transcode {data.get('stream_count_transcode', 0)}",
                ]
            else:
                print(f"Tautulli API response: {r.status_code}")
        except Exception as e:
            print(f"Tautulli API error: {e}")
    lines = [
        "# HELP ppth_tautulli_up 1 if the Tautulli scrape succeeded, 0 otherwise",
        "# TYPE ppth_tautulli_up gauge",
        f'ppth_tautulli_up{{instance="{url}"}} {up}',
    ] + lines
    return lines


# ─── HTTP handler + entry point ─────────────────────────────────────────────

class MetricHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        metrics = []
        metrics += collect_system()
        metrics += collect_zfs()
        metrics += collect_tautulli()
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(("\n".join(metrics) + "\n").encode())


def main():
    port = int(os.getenv("EXPORTER_PORT", "8000"))
    bind_address = os.getenv("EXPORTER_BIND_ADDRESS", "0.0.0.0")
    server = HTTPServer((bind_address, port), MetricHandler)
    print(f"Metrics server started at http://{bind_address}:{port}/metrics")
    server.serve_forever()


if __name__ == "__main__":
    main()
