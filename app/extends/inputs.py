"""Catálogo de inputs do app — gêmeo de `app/extends/buttons.py`.

O framework entrega o catálogo genérico (`ajsystem.defs.inputs.INPUT_TYPES`), com
`cpf`/`cnpj` ainda não existindo ali (são tipos de domínio). O app define, aqui,
como esses tipos se comportam: `type='text'` no HTML, com `mask` e `validate`.
Assim `FIELD_TYPES['CPF'] = {'input': 'cpf'}` funciona e `Field` traz máscara/
validador sem o model reescrevê-los.

Regra de merge (mesma dos botões): `INPUTS  <  Inputs (app)  <  input_props (uso)`
e `type` é metadado de base (sai do merge).

Exemplos:
    Inputs = {
        'cpf':  {'type': 'text', 'masked': True, 'mask': '999.999.999-99',
                 'validate': 'cpf', 'size': 14, 'filter_kind': 'text'},
        'cnpj': {'type': 'text', 'masked': True, 'mask': '99.999.999/9999-99',
                 'validate': 'cnpj', 'size': 18, 'filter_kind': 'text'},
    }
"""
# ── Aparência/tipo que é do app ──────────────────────────────────────────────
Inputs = {
    # Documentos: como `text` com máscara (HTML puro); validadores do framework
    # tratam `validate: 'cpf'`/`'cnpj'` em outro lugar (se houver). O importante
    # aqui é `masked` + `mask` + `size`.
    'cpf': {
        'type': 'text',
        'masked': True,
        'mask': '999.999.999-99',
        'validate': 'cpf',
        'size': 14,
        'filter_kind': 'text',
        'align': 'left',
    },
    'cnpj': {
        'type': 'text',
        'masked': True,
        'mask': '99.999.999/9999-99',
        'validate': 'cnpj',
        'size': 18,
        'filter_kind': 'text',
        'align': 'left',
    },
    # Telefone BR: traz máscara/validação via catálogo (o `FIELD_TYPES['FONE']`
    # aponta para `tel` — o app pode sobrescrever `tel` para BR, ou criar
    # `fone_br`. Como o plano diz override, vamos reforçar `tel` para BR.
    'tel': {
        'type': 'tel',
        'masked': True,
        'mask': '@R (99) 99999-9999',
        'validate': 'telefone',
        'size': 18,
        'filter_kind': 'text',
        'align': 'left',
    },
}
