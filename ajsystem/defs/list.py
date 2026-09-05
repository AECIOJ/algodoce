"""List — spec puro de listagem (camada de dados, padrão `Field`/`Form`/`Page`).

Movido de `core/list.py` (que continua com os helpers data-agnósticos — colunas,
filtros, largura). `parse_list` é idempotente (dict | List → List) e é o ponto
único de entrada do motor (`core.do_list`).
"""
from dataclasses import dataclass
from typing import Any, Optional, Union

from ajsystem.defs.buttons import resolve_buttons as _resolve_buttons
from ajsystem.defs.data import Field, _entidade_fields, _resolve_fieldset


@dataclass
class List:
    """Config de listagem — objeto consumido por `pages/list.html`."""
    fields: Union[list, dict]
    fields_master: Optional[list] = None
    edit_endpoint: Optional[str] = None
    edit_id_field: str = 'id'
    detail_data: Optional[str] = None
    buttons: Optional[list] = None
    template: Optional[str] = None
    linha: Optional[list] = None
    card_idx: Optional[list] = None

    def __post_init__(self):
        if isinstance(self.fields, dict):
            if 'fields' in self.fields:
                self.fields = _resolve_fieldset(self.fields)
            else:
                self.fields = [Field(name=k, **v) for k, v in _entidade_fields(self.fields).items()]

    def resolve_buttons(self, bp_name=None):
        return _resolve_buttons(self.buttons, bp_name)

    @property
    def master_fields(self):
        if self.fields_master is not None:
            return [self.fields[i - 1] for i in self.fields_master]
        return self.fields

    @property
    def card_fields(self):
        if self.card_idx:
            return [self.fields[i - 1] for i in self.card_idx]
        return None


_LIST_KEYS = frozenset(List.__dataclass_fields__)


def parse_list(spec: Any) -> List:
    """Normaliza a config de listagem (dict | List) para `List` (idempotente)."""
    if isinstance(spec, List):
        return spec
    if isinstance(spec, dict):
        return List(**{k: v for k, v in spec.items() if k in _LIST_KEYS})
    raise TypeError(f"spec de listagem deve ser dict ou List, veio {type(spec).__name__}")