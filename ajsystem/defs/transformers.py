"""TRANSFORMERS — transformações puras de texto aplicadas a campos.

Sem efeito colateral (não tocam request/DB/render). A aplicação de `transform`
vive em `core/formats.py`; aqui fica a inferência do transform a partir de um
`Field` resolvido (comando `@U/L/C/T` da máscara) e a aplicação sobre
instâncias. Sem comando na máscara → `None` (salva como veio).
"""
from ajsystem.core.formats import _title_case, apply_transform_value  # noqa: F401

__all__ = ['apply_transform_value', 'infer_transform', 'apply_field_transforms']


# transform: 'title' | 'upper' | 'lower' | 'cap' | None
#   comando `@?` da máscara | sem comando → None (sem transform)
#   'title' → primeira letra de cada palavra maiúscula (respeita CONECTORES)
#   'cap'   → apenas o 1º caractere em maiúsculo
_MASK_TRANSFORM = {'U': 'upper', 'L': 'lower', 'C': 'cap', 'T': 'title'}


def infer_transform(f):
    """Transform de texto de um `Field` resolvido (None → sem transform)."""
    if f.pos_form != 1 or f.readonly or f.hidden:
        return None
    if f.input in ('number', 'boolean', 'checkbox', 'date', 'time', 'image'):
        return None
    if f.options:
        return None
    return _MASK_TRANSFORM.get(f.mask_text_command)


def apply_field_transforms(instance, fields):
    """Aplica o transform (comando de máscara `@U/L/C/T`) sobre os campos
    (dict {nome: cfg} ou lista de Field)."""
    from ajsystem.defs.data import Field

    field_list = fields
    if isinstance(fields, dict):
        if 'fields' in fields:
            field_list = fields['fields']
        else:
            field_list = [Field(name=k, **v) for k, v in fields.items()]
    for f in field_list:
        if not hasattr(instance, f.name):
            continue
        val = getattr(instance, f.name, None)
        if val is None or not isinstance(val, str):
            continue
        tr = infer_transform(f)
        if not tr:
            continue
        setattr(instance, f.name, apply_transform_value(val, tr, f))