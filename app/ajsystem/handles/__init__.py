"""Ações de request (handlers) do framework ajsystem.

`handles/` agrupa os pontos de entrada que tratam uma requisição específica:
- `render_list` → renderização da página de listagem (`render_list`);
- `auth` → wiring do login manager + rotas de autenticação e painel de segurança.

Aqui não ficam definições de estrutura (essas vivem em `defs/`) nem o motor
(`core/auto`, `core/menu`).
"""
