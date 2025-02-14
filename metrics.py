from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import psutil
import json
import requests
from datetime import datetime

class MetricHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            metrics = []
            
            # Your original API metric
            try: 
                response = requests.get('http://tautulli.ppth/api/v2?apikey=YOUR_API_KEY_HERE&cmd=get_activity')
                print(response)
                if response.status_code == 200:
                    data = response.json()['response']['data']
                    if data:
                        # Extract the three metrics we want
                        metrics.extend([
                            f'plex_streams_total {data["stream_count"]}',
                            f'plex_streams_direct_play {data["stream_count_direct_play"]}',
                            f'plex_streams_direct_stream {data["stream_count_direct_stream"]}',
                            f'plex_streams_transcode {data["stream_count_transcode"]}'
                        ])
                    else:
                        metrics.extend([
                            'plex_streams_total 0',
                            'plex_streams_direct_play 0',
                            'plex_streams_direct_stream 0',
                            'plex_streams_transcode 0'
                        ])
            except Exception as e:
                print(f"API error: {e}")

            # System metrics
            metrics.append(f'ppth_system_cpu_percent {psutil.cpu_percent()}')
            metrics.append(f'ppth_system_memory_percent {psutil.virtual_memory().percent}')
            
            # Add timestamps if you want them
            # timestamp = round(datetime.now().timestamp())
            # metrics = [f'{m} {timestamp}' for m in metrics]
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('\n'.join(metrics).encode())
        else:
            self.send_response(404)
            self.end_headers()

server = HTTPServer(('0.0.0.0', 8000), MetricHandler)
print("Metrics server started at http://0.0.0.0:8000/metrics")
server.serve_forever()
