"""Definições da estrutura (camada de dados) do framework ajsystem.

`defs/` agrupa a ESTRUTURA declarativa pura que o app importa em cada página:
dataclasses (`Field` em `fields`, `Query` em `query`, `Button`, `Report`,
`Form`, `List`, `Page` em `page`, `Editor`), a tipagem do config do app (`App`,
`Module`, `MenuItem`, `Tema` em `config`), tabelas de tipos, constantes e
resolução de campos. Não depende de renderização (`core/form`, `core/list`,
`core/query`), de request nem do motor (`core/auto`, `core/menu`).

Dependências: apenas stdlib + `app.ajsystem.core.utils` (helpers genéricos);
exceções pragmáticas aceitas: `flask.Blueprint` e `sqlalchemy.orm.MANYTOONE`
para auto-resolução declarativa em `defs/form.py`.
"""
