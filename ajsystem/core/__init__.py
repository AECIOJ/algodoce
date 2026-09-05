"""Núcleo/motor do framework ajsystem.

`core/` agrupa o MOTOR do framework (executado, não importado pelo app para
estrutura):

- Orquestradores `do_*` — request → response (do_form, do_list, do_report,
  do_auth); consomem specs puros de `defs/`.
- Capacidades — lógica reutilizável sem request: `form`, `list`, `query`,
  `pdf`, `filters`, `crypto`, `ntfy`, `utils`, `auto`/`menu`
  (blueprints) e `adapter` (adaptador de acoplamento com o app host).

Estrutura declarativa pura fica em `defs/`; `handles/` foi eliminado e
fundido em `core/do_*`. Modelo completo em `ajsystem/ARCHITECTURE.md`.
"""
