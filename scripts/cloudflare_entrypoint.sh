#!/bin/sh
set -e

URL_FILE=/tmp/cloudflare_url.txt
FORWARD_HOST=algodoce
FORWARD_PORT=5000
API_PORT=4040

cloudflared tunnel --url http://${FORWARD_HOST}:${FORWARD_PORT} > /tmp/cloudflare.log 2>&1 &

for i in $(seq 1 30); do
    URL=$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' /tmp/cloudflare.log 2>/dev/null | head -1)
    if [ -n "$URL" ]; then
        echo "$URL" > $URL_FILE
        echo "Cloudflare tunnel: $URL"
        break
    fi
    sleep 1
done

exec python3 -c "
import http.server, json, threading, time

URL_FILE = '$URL_FILE'
URL = ''

def read_url():
    global URL
    while True:
        try:
            with open(URL_FILE) as f:
                u = f.read().strip()
            if u and 'https://' in u:
                URL = u
        except:
            pass
        time.sleep(5)

threading.Thread(target=read_url, daemon=True).start()

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if URL:
            data = {'tunnels': [{'public_url': URL}]}
        else:
            data = {'tunnels': []}
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    def log_message(self, fmt, *args):
        pass

httpd = http.server.HTTPServer(('0.0.0.0', $API_PORT), Handler)
httpd.serve_forever()
"
