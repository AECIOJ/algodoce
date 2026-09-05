#!/bin/sh
set -e

URL_FILE=/tmp/pinggy_url.txt
SSH_HOST=a.pinggy.io
SSH_PORT=443
FORWARD_HOST=algodoce
FORWARD_PORT=5000
API_PORT=4040

ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -p $SSH_PORT -R0:${FORWARD_HOST}:${FORWARD_PORT} qr@$SSH_HOST \
    > $URL_FILE 2>&1 &
SSH_PID=$!

for i in $(seq 1 30); do
    URL=$(grep -oE 'https://[^[:space:]]+' $URL_FILE 2>/dev/null | grep -i pinggy | grep -v dashboard | head -1)
    if [ -n "$URL" ]; then
        echo "$URL" > $URL_FILE
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
            if u and ('http://' in u or 'https://' in u):
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
