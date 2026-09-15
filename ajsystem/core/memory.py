"""Memória server-side entre páginas (carry serializado).

Quando um botão de sessão com ``carry`` é clicado, o JS serializa todo o
``#main-form`` e faz POST ao endpoint (com ``__carry_map`` se houver map de
renome). O endpoint chama ``store_carry(request.form)`` e redireciona com
``?carry=<token>``.

A página destino lê via ``carry_get(token)`` (peek) ou ``carry_take(token)``
(pop). Valores chegam keyed pelos ``input_name`` da origem; o map de renome
``{'dest_field': 'source_input_name'}`` declarado no botão viaja no token e é
aplicado automaticamente pelo ``carry_get`` / ``carry_take``."""

import json
import secrets
import time
from typing import Optional

_CARRY: dict = {}
_TTL = 600  # 10 min


def store_carry(payload: dict, ttl: int = _TTL) -> str:
    """Grava ``payload`` (``request.form``) em memória; devolve token.

    A chave ``__carry_map`` (JSON com ``{dest: source_input_name}``) é
    separada do payload e guardada no entry para a leitura na página
    destino já aplicar os renames."""
    data = dict(payload)
    raw_map = data.pop('__carry_map', None)
    if raw_map:
        try:
            renames = json.loads(raw_map)
            renames = {k: v for k, v in renames.items() if isinstance(k, str) and isinstance(v, str)}
        except Exception:
            renames = {}
    else:
        renames = {}
    token = secrets.token_urlsafe(16)
    _CARRY[token] = {'ts': time.time(), 'ttl': ttl,
                     'values': data, 'renames': renames}
    _gc()
    return token


def carry_get(token: Optional[str]) -> Optional[dict]:
    """Leitura (peek) dos valores carry (renames do botão já aplicados)."""
    entry = _CARRY.get(token) if token else None
    if entry is None:
        return None
    entry['ts'] = time.time()
    return _apply_renames(entry['values'], entry.get('renames'))


def carry_take(token: Optional[str]) -> Optional[dict]:
    """Pop — remove do store e retorna valores (renames aplicados)."""
    entry = _CARRY.pop(token, None) if token else None
    if entry is None:
        return None
    return _apply_renames(entry['values'], entry.get('renames'))


def carry_renames(token: Optional[str]) -> dict:
    """Renames declarados na origem (``{dest: source_input_name}``)."""
    entry = _CARRY.get(token) if token else None
    return dict(entry.get('renames') or {}) if entry else {}


def _apply_renames(values: dict, renames: Optional[dict]) -> dict:
    """Aplica renames: ``{'valor': 'eTotal'}`` → chave ``eTotal`` vira ``valor``.
    Campos sem rename ficam com o nome original."""
    if not renames:
        return dict(values)
    out = {}
    for src_name, val in values.items():
        dest_name = None
        for d, s in renames.items():
            if s == src_name:
                dest_name = d
                break
        out[dest_name or src_name] = val
    return out


def _gc():
    """Limpa entradas expiradas."""
    now = time.time()
    expired = [k for k, v in _CARRY.items()
               if now - v['ts'] > v.get('ttl', _TTL)]
    for k in expired:
        _CARRY.pop(k, None)