# Plano de trabalho — ajsystem / app/

## Fase 0 — Documentar arquitetura (modelo de camadas) ✔ já executada
- Criar `app/ajsystem/ARCHITECTURE.md`: modelo de camadas
  - `defs/` = ESTRUTURA declarativa pura (Entity, Field, Query, Button,
    Report, ReportColumn, specs Form/List/Editor, FIELD_TYPES, VALIDATORS,
    constantes) — importada pelo app em cada página; só stdlib + core.utils.
  - `core/` = MOTOR (executado): orquestradores `do_*` (do_form, do_list,
    do_report, do_auth) + capacidades (form, list, query, pdf, filters,
    edits, crypto, ntfy, utils, auto, menu, app_config).
  - `handles/` = ELIMINADO (fundido em core/do_*).
  - Regras de dependência + teste prático + borrões B1–B4 + pendências.
- Atualizar docstrings: `core/__init__.py`, `defs/__init__.py`,
  `handles/__init__.py` (marcado DEPRECADO).

## Fase 1 — Remover arquivos mortos e shims ✔ executada
1. Deletar `app/buttons.py` — morto (0 importadores; app usa
   `ajsystem/defs/buttons` via context processor `app/__init__.py:223`
   e `core/form.py`).
2. `app/filters.py` — atualizar 8 importadores (transferencias, movimentos,
   producao, pedidos, recursos, transacao, compras, app/fields.py) para
   `ajsystem.defs.filters` + `ajsystem.core.filters`; deletar shim.
3. `app/pdf.py` — atualizar 4 importadores (pedidos, operacoes, compras,
   orcamentos) para `ajsystem.core.pdf`; deletar shim.
4. `app/report.py` — atualizar 4 relatórios (rep_orcamento, rep_compra,
   rep_operacao, rep_pedido) para `ajsystem.defs.report`; deletar shim.
5. `app/fields.py` — MANTER até pedidos/recursos/transacao migrarem para
   Entity + FIELD_TYPES; apenas o import de FILTER_* passa a vir de ajsystem.

## Fase 2 — Extensions para o framework ✔ executada
6. Criar `ajsystem/core/extensions.py`: `db`, `migrate`, `login_manager`
   (login_view=`auth.login`).
7. `core/app_config.py:8` importa de `core.extensions` (sem ciclo).
8. Atualizar os 44 arquivos `from app.extensions import …` →
   `from app.ajsystem.core.extensions import …` (models, rotas;
   `migrations/env.py` usa `current_app.extensions['migrate'].db`, ok).
9. Deletar `app/extensions.py`.

## Fase 3 — Config para o framework ✔ executada
10. Criar `ajsystem/core/config.py`: classe `Config` lendo `.env` com nomes
    documentados no docstring — `POSTGRES_USER/PASSWORD/HOST/PORT/DB`,
    `SECRET_KEY`, `SESSION_TIMEOUT`; manter defaults atuais (WTF_CSRF,
    MAX_CONTENT_LENGTH 5MB, cookies de sessão, PERMANENT_SESSION_LIFETIME 7d,
    SEND_FILE_MAX_AGE_DEFAULT 0).
11. `app/__init__.py:7,48` → `from app.ajsystem.core.config import Config`;
    deletar `app/config.py`.

## Verificação ✔ executada
12. compile + boot + smoke test (`/pedidos`, `/recursos/`, `/categorias/`,
    `/contas/`, `/movimentos/recebimentos`, `/transacao/pagar/`,
    `/relatorios/compras`, `/pedidos/<id>/pdf` 42KB, login).
13. `grep` final: zero imports de `app.extensions`, `app.filters`,
    `app.pdf`, `app.report` (só `app.reports.*`, válido), `app.buttons`,
    `app.config`.

## Riscos / notas
- Fase 2: 45 edits mecânicos (busca/reposição); sem mudança de comportamento.
- `migrate` continua registrado via `init_app`; `env.py` inalterado.
- Fase 1 item 2 depende da ordem: atualizar `app/fields.py` antes de deletar
  `app/filters.py`.
