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
                    response = requests.get(f'{tautulli_url}/api/v2?apikey={tautulli_api_key}&cmd=get_activity')
                    print(f"Tautulli API response: {response.status_code}")
                    if response.status_code == 200:
                        data = response.json()['response']['data']
                        if data:
                            # Extract the three metrics we want
                            metrics.extend([
                                '# HELP plex_streams_total Total number of active Plex streams',
                                '# TYPE plex_streams_total gauge',
                                f'plex_streams_total {data["stream_count"]}',
                                '# HELP plex_streams_direct_play Number of Plex streams using direct play',
                                '# TYPE plex_streams_direct_play gauge',
                                f'plex_streams_direct_play {data["stream_count_direct_play"]}',
                                '# HELP plex_streams_direct_stream Number of Plex streams using direct stream',
                                '# TYPE plex_streams_direct_stream gauge',
                                f'plex_streams_direct_stream {data["stream_count_direct_stream"]}',
                                '# HELP plex_streams_transcode Number of Plex streams using transcoding',
                                '# TYPE plex_streams_transcode gauge',
                                f'plex_streams_transcode {data["stream_count_transcode"]}'
                            ])
                        else:
                            metrics.extend([
                                '# HELP plex_streams_total Total number of active Plex streams',
                                '# TYPE plex_streams_total gauge',
                                'plex_streams_total 0',
                                '# HELP plex_streams_direct_play Number of Plex streams using direct play',
                                '# TYPE plex_streams_direct_play gauge',
                                'plex_streams_direct_play 0',
                                '# HELP plex_streams_direct_stream Number of Plex streams using direct stream',
                                '# TYPE plex_streams_direct_stream gauge',
                                'plex_streams_direct_stream 0',
                                '# HELP plex_streams_transcode Number of Plex streams using transcoding',
                                '# TYPE plex_streams_transcode gauge',
                                'plex_streams_transcode 0'
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
