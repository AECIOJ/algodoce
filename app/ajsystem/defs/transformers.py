"""TRANSFORMERS — transformações puras de texto aplicadas a campos.

Sem efeito colateral (não tocam request/DB/render). Reúne a aplicação de
`transform` (`'title' | 'upper' | 'lower' | 'cap' | callable`) e a inferência
de transform default a partir de um `Field` resolvido.
"""
from app.ajsystem.core.utils import _title_case

__all__ = ['apply_transform_value', 'infer_transform', 'apply_field_transforms']


def apply_transform_value(val, transform, field=None):
    """Aplica `transform` a `val` (string). Tolerante a não-string/None."""
    if not val or not isinstance(val, str):
        return val
    if transform == 'upper':
        return val.strip().upper()
    if transform == 'lower':
        return val.strip().lower()
    if transform == 'cap':
        s = val.strip()
        return s[:1].upper() + s[1:] if s else s
    if transform == 'title':
        return _title_case(val.strip())
    if callable(transform):
        return transform(val, field)
    return val


# transform: None | 'none' | 'title' | 'upper' | 'lower' | 'cap' | callable(val, field)
#   None     → auto-inferido (ver `infer_transform`)
#   'none'   → sem transformação (number/boolean/options/readonly/hidden/default)
#   'title'  → primeira letra de cada palavra maiúscula (respeita CONECTORES)
#   'cap'    → apenas o 1º caractere em maiúsculo
def infer_transform(f) -> str:
    """Transform default de um `Field` resolvido (None → auto)."""
    if f.transform is not None:
        return f.transform
    if f.pos_form != 1 or f.readonly or f.hidden:
        return 'none'
    if f.input in ('number', 'boolean', 'checkbox', 'date', 'time', 'image'):
        return 'none'
    if f.options:
        return 'none'
    return 'title'


def apply_field_transforms(instance, fields):
    """Aplica `transform` sobre os campos (dict {nome: cfg} ou lista de Field)."""
    from app.ajsystem.defs.data import Field

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
        if tr == 'none':
            continue
        setattr(instance, f.name, apply_transform_value(val, tr, f))
