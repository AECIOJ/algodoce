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
from app.extends.masks import MCPF, MCNPJ, MTEL

Inputs = {
    'cpf': {
        'type': 'text',
        'masked': True,
        'mask': MCPF,
        'validate': 'cpf',
        'size': 14,
        'filter_kind': 'text',
        'align': 'left',
    },
    'cnpj': {
        'type': 'text',
        'masked': True,
        'mask': MCNPJ,
        'validate': 'cnpj',
        'size': 18,
        'filter_kind': 'text',
        'align': 'left',
    },
    'tel': {
        'type': 'tel',
        'masked': True,
        'mask': MTEL,
        'validate': 'telefone',
        'size': 18,
        'filter_kind': 'text',
        'align': 'left',
    },
}
