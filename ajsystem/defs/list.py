"""List — spec puro de listagem (camada de dados, padrão `Field`/`Form`/`Page`).

Movido de `core/list.py` (que continua com os helpers data-agnósticos — colunas,
filtros, largura). `parse_list` é idempotente (dict | List → List) e é o ponto
único de entrada do motor (`core.do_list`).

**Slots (`line` / `card` / `hidden`)** — onde cada field vai na listagem. São
props da PÁGINA (`Page.props.list`), nunca do `Field`: a lista é quem sabe o que
é coluna e o que é card, e a pergunta "esse campo aparece aqui?" só tem resposta
no lugar onde a lista é montada. Aceitam a mesma família de formatos de
`columns` (entidade, lista de nomes, `Entidade.campo`, dict agrupado) e são
resolvidos por `core.resolve.resolve_slots`. Precedência quando o mesmo campo é
citado em mais de um: `hidden` > `line` > `card`; quem não é citado em nenhum vai
para a linha.
"""
from dataclasses import dataclass
from typing import Any, Optional

from ajsystem.defs.buttons import resolve_buttons as _resolve_buttons


@dataclass
class List:
    """Config de listagem — objeto consumido por `pages/list.html`.

    `fields` deve ser lista de `Field` já resolvidos (o motor resolve via
    `normalize_fieldspec` antes de criar o List).
    """
    fields: list
    fields_master: Optional[list] = None
    edit_endpoint: Optional[str] = None
    edit_id_field: str = 'id'
    detail_data: Optional[str] = None
    buttons: Optional[list] = None
    template: Optional[str] = None
    master: Optional[str] = None
    line_idx: Optional[list] = None  # **computado** — índices em `master_fields`
                                     # das colunas pinadas pela prop `line`
    card_idx: Optional[list] = None  # **computado** — índices de `fields` no card

    def resolve_buttons(self, bp_name=None, botoes_tipos=None, botoes_page=None):
        return _resolve_buttons(self.buttons, bp_name, where='list', ctx='list',
                                types=(botoes_tipos, botoes_page))

    @property
    def master_fields(self):
        if self.fields_master is not None:
            return [self.fields[i - 1] for i in self.fields_master]
        return self.fields


_LIST_KEYS = frozenset(List.__dataclass_fields__)


def parse_list(spec: Any) -> List:
    """Normaliza a config de listagem (dict | List) para `List` (idempotente)."""
    if isinstance(spec, List):
        return spec
    if isinstance(spec, dict):
        return List(**{k: v for k, v in spec.items() if k in _LIST_KEYS})
    raise TypeError(f"spec de listagem deve ser dict ou List, veio {type(spec).__name__}")