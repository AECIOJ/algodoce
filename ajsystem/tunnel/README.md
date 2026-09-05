"""Túnel de exposição pública (sidecar) — pacote portátil do framework.

Conteúdo:
- `cloudflare_entrypoint.sh`: ENTRYPOINT do container sidecar (sobe o
  `cloudflared`, captura a URL e serve `GET :4040/api/tunnels`).
- `provider.py`: lado app (`fetch/get_tunnel_url`, `api_url`) — sem
  dependências além da stdlib.

Para usar em outro app:
1. Copie `ajsystem/` (este pacote vai junto).
2. No compose, adicione o serviço sidecar (ver `Dockerfile.cloudflare` como
   exemplo — ajuste o `COPY` para o caminho do pacote):
     build: {context: ., dockerfile: Dockerfile.cloudflare}
3. No `create_app`, fiação em 3 linhas:
     from ajsystem.tunnel import provider as tunnel_provider
     adapter.set_tunnel_url_provider(lambda: tunnel_provider.get_tunnel_url())

Variáveis do entrypoint (com default = comportamento atual):
  `FORWARD_HOST` (algodoce), `FORWARD_PORT` (5000), `API_PORT` (4040).
"""
