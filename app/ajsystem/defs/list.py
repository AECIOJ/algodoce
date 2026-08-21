"""Spec `List` — configuração declarativa de listagens (camada de dados).

Agrupa a dataclass `List` e os helpers de resolução pura de campos. Não
depende de renderização (`core/list.py`), de request nem do motor. Regra de
dependência: stdlib + `app.ajsystem.core.utils` (helpers genéricos).
"""
from dataclasses import dataclass
from typing import Optional, Union

from app.ajsystem.defs.fields import Field
from app.ajsystem.defs.entities import _resolve_fieldset
from app.ajsystem.defs.buttons import resolve_buttons


@dataclass
class List:
    fields: Union[list, dict]
    fields_master: Optional[list[int]] = None
    fields_detail: Optional[list[int]] = None
    master_key: Optional[str] = None
    edit_endpoint: Optional[str] = None
    edit_id_field: str = 'id'
    edit_if_field: Optional[str] = None
    edit_endpoint_map: Optional[dict] = None
    edit_endpoint_key: Optional[str] = None
    detail_data: Optional[str] = None
    send_endpoint: Optional[str] = None
    reports: Optional[list] = None
    buttons: Optional[list] = None
    template: Optional[str] = None
    linha: Optional[list[int]] = None
    card_idx: Optional[list[int]] = None
    tags: Optional[list] = None

    def __post_init__(self):
        if isinstance(self.fields, dict):
            if 'fields' in self.fields:
                self.fields = _resolve_fieldset(self.fields)
            else:
                self.fields = [Field(name=k, **v) for k, v in self.fields.items()]

    def resolve_buttons(self, bp_name=None):
        """Resolve `buttons` para `Button` objects (mesma semântica do Form)."""
        if getattr(self, '_resolved_buttons', None) is None:
            self._resolved_buttons = resolve_buttons(self.buttons, bp_name)
        return self._resolved_buttons

    @property
    def master_fields(self):
        if self.fields_master is not None:
            return [self.fields[i-1] for i in self.fields_master]
        return self.fields

    @property
    def detail_fields(self):
        if self.fields_detail:
            return [self.fields[i-1] for i in self.fields_detail]
        return None

    @property
    def linha_fields(self):
        if self.linha:
            return [self.master_fields[i] for i in self.linha]
        return self.master_fields

    @property
    def card_fields(self):
        if self.card_idx:
            return [self.fields[i-1] for i in self.card_idx]
        return None
