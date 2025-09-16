from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import psutil
import json
import requests
from datetime import datetime
import os

class MetricHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            metrics = []
            
            # Get configuration from environment variables
            tautulli_url = os.getenv('TAUTULLI_URL', 'http://localhost:8181')
            tautulli_api_key = os.getenv('TAUTULLI_API_KEY', '')
            
            # Tautulli/Plex metrics
            if tautulli_api_key:
                try:
                    # Get activity data
                    response = requests.get(f'{tautulli_url}/api/v2?apikey={tautulli_api_key}&cmd=get_activity')
                    print(f"Tautulli API response: {response.status_code}")
                    if response.status_code == 200:
                        data = response.json()['response']['data']

                        # Stream counts
                        stream_count = data.get('stream_count', 0) if data else 0
                        direct_play = data.get('stream_count_direct_play', 0) if data else 0
                        direct_stream = data.get('stream_count_direct_stream', 0) if data else 0
                        transcode = data.get('stream_count_transcode', 0) if data else 0

                        metrics.extend([
                            '# HELP plex_streams_total Total number of active Plex streams',
                            '# TYPE plex_streams_total gauge',
                            f'plex_streams_total {stream_count}',
                            '# HELP plex_streams_direct_play Number of Plex streams using direct play',
                            '# TYPE plex_streams_direct_play gauge',
                            f'plex_streams_direct_play {direct_play}',
                            '# HELP plex_streams_direct_stream Number of Plex streams using direct stream',
                            '# TYPE plex_streams_direct_stream gauge',
                            f'plex_streams_direct_stream {direct_stream}',
                            '# HELP plex_streams_transcode Number of Plex streams using transcoding',
                            '# TYPE plex_streams_transcode gauge',
                            f'plex_streams_transcode {transcode}'
                        ])

                        # Bandwidth metrics
                        total_bandwidth = data.get('total_bandwidth', 0) if data else 0
                        lan_bandwidth = data.get('lan_bandwidth', 0) if data else 0
                        wan_bandwidth = total_bandwidth - lan_bandwidth  # Calculate WAN bandwidth

                        metrics.extend([
                            '# HELP plex_bandwidth_total Total bandwidth usage in Kbps',
                            '# TYPE plex_bandwidth_total gauge',
                            f'plex_bandwidth_total {total_bandwidth}',
                            '# HELP plex_bandwidth_lan LAN bandwidth usage in Kbps',
                            '# TYPE plex_bandwidth_lan gauge',
                            f'plex_bandwidth_lan {lan_bandwidth}',
                            '# HELP plex_bandwidth_wan WAN bandwidth usage in Kbps',
                            '# TYPE plex_bandwidth_wan gauge',
                            f'plex_bandwidth_wan {wan_bandwidth}'
                        ])

                        # Parse sessions for stream quality metrics
                        sessions = data.get('sessions', []) if data else []
                        unique_users = set()
                        resolution_counts = {}
                        total_bitrate = 0
                        stream_count_for_bitrate = 0

                        for session in sessions:
                            # Count unique users
                            user = session.get('user')
                            if user:
                                unique_users.add(user)

                            # Count resolutions
                            if 'stream_video_resolution' in session:
                                resolution = session['stream_video_resolution']
                                resolution_counts[resolution] = resolution_counts.get(resolution, 0) + 1

                            # Sum bitrates
                            if 'stream_bitrate' in session:
                                bitrate = session.get('stream_bitrate', 0)
                                if bitrate:
                                    total_bitrate += bitrate
                                    stream_count_for_bitrate += 1

                        # User activity metrics
                        metrics.extend([
                            '# HELP plex_active_users Number of unique users currently streaming',
                            '# TYPE plex_active_users gauge',
                            f'plex_active_users {len(unique_users)}'
                        ])

                        # Stream quality distribution by resolution
                        for resolution, count in resolution_counts.items():
                            metrics.extend([
                                f'# HELP plex_streams_by_resolution Number of streams at {resolution} resolution',
                                f'# TYPE plex_streams_by_resolution gauge',
                                f'plex_streams_by_resolution{{resolution="{resolution}"}} {count}'
                            ])

                        # Average bitrate
                        avg_bitrate = total_bitrate / stream_count_for_bitrate if stream_count_for_bitrate > 0 else 0
                        metrics.extend([
                            '# HELP plex_avg_stream_bitrate Average bitrate across all streams in Kbps',
                            '# TYPE plex_avg_stream_bitrate gauge',
                            f'plex_avg_stream_bitrate {avg_bitrate}'
                        ])

                    # Get server info for version
                    response = requests.get(f'{tautulli_url}/api/v2?apikey={tautulli_api_key}&cmd=get_server_info')
                    if response.status_code == 200:
                        server_data = response.json()['response']['data']
                        if server_data:
                            plex_version = server_data.get('pms_version', 'unknown')
                            plex_platform = server_data.get('pms_platform', 'unknown')
                            metrics.extend([
                                '# HELP plex_server_info Plex server information',
                                '# TYPE plex_server_info gauge',
                                f'plex_server_info{{version="{plex_version}",platform="{plex_platform}"}} 1'
                            ])

                    # Get total users count
                    response = requests.get(f'{tautulli_url}/api/v2?apikey={tautulli_api_key}&cmd=get_users')
                    if response.status_code == 200:
                        users_data = response.json()['response']['data']
                        if users_data:
                            total_users = len(users_data)
                            metrics.extend([
                                '# HELP plex_total_users Total number of Plex users',
                                '# TYPE plex_total_users gauge',
                                f'plex_total_users {total_users}'
                            ])

                except Exception as e:
                    print(f"Tautulli API error: {e}")
            else:
                print("TAUTULLI_API_KEY not set, skipping Plex metrics")

            # System metrics
            metrics.extend([
                '# HELP ppth_system_cpu_percent CPU usage percentage',
                '# TYPE ppth_system_cpu_percent gauge',
                f'ppth_system_cpu_percent {psutil.cpu_percent()}'
            ])
            metrics.extend([
                '# HELP ppth_system_memory_percent Memory usage percentage',
                '# TYPE ppth_system_memory_percent gauge',
                f'ppth_system_memory_percent {psutil.virtual_memory().percent}'
            ])
            
            # CPU temperature (may not be available in containers)
            try:
                temps = psutil.sensors_temperatures()
                if temps and 'coretemp' in temps and len(temps['coretemp']) > 1:
                    metrics.extend([
                        '# HELP ppth_system_cpu_package_temp CPU package temperature in Celsius',
                        '# TYPE ppth_system_cpu_package_temp gauge',
                        f'ppth_system_cpu_package_temp {temps["coretemp"][1].current}'
                    ])
            except Exception as e:
                print(f"Could not read CPU temperature: {e}")


            # Add timestamps if you want them
            # timestamp = round(datetime.now().timestamp())
            # metrics = [f'{m} {timestamp}' for m in metrics]
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            # Add trailing newline for POSIX compliance
            self.wfile.write(('\n'.join(metrics) + '\n').encode())
        else:
            self.send_response(404)
            self.end_headers()

# Get configuration from environment
port = int(os.getenv('EXPORTER_PORT', '8000'))
bind_address = os.getenv('EXPORTER_BIND_ADDRESS', '0.0.0.0')

server = HTTPServer((bind_address, port), MetricHandler)
print(f"Metrics server started at http://{bind_address}:{port}/metrics")
server.serve_forever()
