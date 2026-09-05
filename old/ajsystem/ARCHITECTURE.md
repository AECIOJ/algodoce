# Arquitetura ajsystem — camadas

## Modelo (decisão 2026-08-10)

- `defs/` — ESTRUTURA declarativa pura, importada pelo app em cada página.
  `Entity`, `Field`, `Query`, `Button`, `Report`, `ReportColumn(s)`,
  `Form`, `List`, `Editor` (specs puros), `FIELD_TYPES`, `VALIDATORS`,
  constantes.
  Regra: só stdlib + `core.utils`; zero request/db/motor.
- `core/` — MOTOR executado, não importado para estrutura.
  Orquestradores `do_*`: `do_form`, `do_list`, `do_report`, `do_auth`
  (request → response; specs puros importados de `defs`).
  Capacidades: `form`, `list`, `query`, `pdf`, `filters`, `edits`,
  `crypto`, `ntfy`, `utils`, `auto`, `menu`, `adapter` (lógica
  reutilizável).
- `handles/` — ELIMINADO (fundido em `core/do_*`).

## Como as rotas usam

- Importam a estrutura de `defs` (specs).
- Chamam o orquestrador: `from core.do_form import do_form; return do_form(spec, id)`.
- Motor interno (`query`/`pdf`/`filters`) nunca é importado pela rota.

## Regra de dependência

- `defs` → stdlib + `core.utils` (somente)
- `core` → `defs` (capacidades consomem specs)
- rotas → `defs` + `core.do_*`
- `core` NÃO importa `handles` (resolvido; antes havia em `core/auto.py`)

## Teste prático

- "É estrutura que a página declara?" → `defs`
- "Executa sem request?" → capacidade em `core` (`form`/`list`/`query`/`pdf`)
- "Precisa de request → resposta?" → orquestrador `core/do_*`

## Confusões legítimas (relatadas)

1. `Form`/`List`/`Editor` eram dataclasses em `core/` — pareciam "definições",
   mas eram specs acoplados ao motor. Movidos para `defs/` (puros).
2. `core/` e `handles/` pareciam o mesmo propósito — eram. Fundidos em
   `core/do_*`.

## Borrões reais identificados

- B1. `defs/report.py`: `_ReportHeader`/`_ReportTable`/`_ReportFooter` são
  internos de renderização do PDF → mover para `core/pdf.py`.
- B2. `handle_form` (handler) em `core/form.py` → `core/do_form.py`.
- B3. `handles/render_list.py` mistura motor (`_resolve_cols`, etc.) + glue →
      motor para `core/list.py`, glue para `core/do_list.py`.
- B4. `core/auto.py` importava `handles.render_list` → passou a usar `core.do_*`.

## Histórico / pendências

- 2026-08-10: modelo definido; doc criada. Renames `report→query`/`pdf`
  concluídos; bug `'edit'`→`readonly` corrigido em `app/fields.py`.
- Pendente: Fases 1–4 (specs puros para `defs`, `do_*` em `core`, remover
  `handles/`).
- Pendente futuro: rotas custom (`pedidos.py` etc.) migrarem de engine helpers
  para declaração em `defs` + delegação a `do_list`/`do_form`.
