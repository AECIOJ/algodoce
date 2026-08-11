"""Definições da estrutura (camada de dados) do framework ajsystem.

`defs/` agrupa a ESTRUTURA declarativa pura que o app importa em cada página:
dataclasses, tabelas de tipos, constantes e resolução de campos. Não depende
de renderização (`core/form`, `core/list`, `core/query`), de request nem do
motor (`core/auto`, `core/menu`).

Alvo (ver `app/ajsystem/ARCHITECTURE.md`): os specs `Form`/`List`/`Editor`
também passam a viver aqui (hoje estão em `core/`; migração pendente).

Dependências: apenas stdlib + `app.ajsystem.core.utils` (helpers genéricos).
"""
