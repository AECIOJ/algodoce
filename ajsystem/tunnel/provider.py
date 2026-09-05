"""Provedor de URL pública via sidecar de túnel (lado app, stdlib only).

Contrato do sidecar (entrypoint deste pacote):
  GET http://<host>:<port>/api/tunnels
  -> {"tunnels": [{"public_url": "https://..."}]}

Uso no app (3 linhas):
    from ajsystem.tunnel import provider as tunnel
    adapter.set_tunnel_url_provider(lambda: tunnel.get_tunnel_url())
"""
import json
import time
import urllib.request

TUNNEL_TTL = 3300

_cache = {"url": None, "ts": 0}


def api_url(host="algodoce_cloudflare", port=4040):
    """URL da API do sidecar."""
    return f"http://{host}:{port}/api/tunnels"


def fetch_tunnel_url(host="algodoce_cloudflare", port=4040, timeout=2):
    """Busca a URL uma vez e guarda em cache (silencioso em falha)."""
    try:
        with urllib.request.urlopen(api_url(host, port), timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        for t in data.get("tunnels", []):
            u = (t or {}).get("public_url", "")
            if isinstance(u, str) and u.startswith("https://"):
                _cache["url"] = u
                _cache["ts"] = time.time()
                return
    except Exception:
        pass


def get_tunnel_url(force=False, host="algodoce_cloudflare", port=4040, ttl=TUNNEL_TTL):
    """URL em cache (TTL); `force` ou vazio refaz a busca. Nunca levanta."""
    now = time.time()
    if force or _cache["url"] is None or (now - _cache["ts"]) > ttl:
        fetch_tunnel_url(host, port)
    return _cache["url"] or ""
