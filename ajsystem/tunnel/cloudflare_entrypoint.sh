#!/bin/sh
set -e

URL_FILE=/tmp/cloudflare_url.txt
LOG_FILE=/tmp/cloudflare.log
FORWARD_HOST=${FORWARD_HOST:-algodoce}
FORWARD_PORT=${FORWARD_PORT:-5000}
API_PORT=${API_PORT:-4040}

rm -f "$URL_FILE"

start_tunnel() {
    : > "$LOG_FILE"
    # QUIC (default) cai por timeout de UDP em redes domésticas; HTTP/2 é estável.
    cloudflared tunnel --protocol http2 --url "http://${FORWARD_HOST}:${FORWARD_PORT}" >> "$LOG_FILE" 2>&1 &
    TUNNEL_PID=$!
}

publish_url() {
    # Só a linha do banner do quick Tunnel ("INF |  https://..."): o regex
    # antigo casava também "https://api.trycloudflare.com" de linha de erro.
    URL=$(grep -oE 'INF \|  https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$LOG_FILE" \
          | grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' | tail -1)
    if [ -n "$URL" ]; then
        echo "$URL" > "$URL_FILE"
    fi
}

# O banner diz "may take some time to be reachable": só publica a URL depois
# do registro da conexão.
wait_ready() {
    i=0
    while [ "$i" -lt 45 ]; do
        if grep -q 'Registered tunnel connection' "$LOG_FILE" 2>/dev/null; then
            publish_url
            if [ -s "$URL_FILE" ]; then
                return 0
            fi
        fi
        kill -0 "$TUNNEL_PID" 2>/dev/null || return 1
        sleep 1
        i=$((i + 1))
    done
    return 1
}

# O processo pode continuar vivo com a conexão morta (reconectando em loop).
# Testa a URL pública: status < 500 significa que a borda alcançou o túnel.
healthy() {
    python3 - "$URL_FILE" <<'PY'
import sys, urllib.error, urllib.request
try:
    url = open(sys.argv[1]).read().strip()
    if not url:
        sys.exit(1)
    req = urllib.request.Request(url, method='HEAD')
    with urllib.request.urlopen(req, timeout=5) as r:
        sys.exit(0 if r.status < 500 else 1)
except urllib.error.HTTPError as e:
    sys.exit(0 if e.code < 500 else 1)
except Exception:
    sys.exit(1)
PY
}

monitor() {
    fails=0
    while kill -0 "$TUNNEL_PID" 2>/dev/null; do
        sleep 20
        if healthy; then
            fails=0
        else
            fails=$((fails + 1))
            if [ "$fails" -ge 3 ]; then
                echo "Cloudflare tunnel sem resposta; reiniciando"
                return 0
            fi
        fi
    done
    return 0
}

(
    while true; do
        start_tunnel
        if wait_ready; then
            echo "Cloudflare tunnel: $(cat "$URL_FILE")"
            monitor
        fi
        rm -f "$URL_FILE"
        kill "$TUNNEL_PID" 2>/dev/null || true
        wait "$TUNNEL_PID" 2>/dev/null || true
        sleep 2
    done
) &

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
            URL = u if u.startswith('https://') else ''
        except Exception:
            URL = ''
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
