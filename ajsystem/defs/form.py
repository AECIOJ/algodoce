"""Form — spec puro de formulário (camada de dados).

Reescrito do zero. Props **declarativas** apenas; o motor (`core.auto`) injeta os
campos internos (`_entity_name`, `_model`, `_schema`) e chama `resolve()`, que
deriva campos/colunas a partir de `fields`, o `Schema` da página e as entitys
associadas. Não manipula request/DB nem engine.
"""
from dataclasses import dataclass, field, fields as dc_fields
from typing import Callable, Optional, Union

from ajsystem.core.list import resolve_column_configs, _resolve_model, _build_fields_from_merged
from ajsystem.defs.buttons import resolve_buttons
from ajsystem.defs.data import _auto_label, resolve_entity_fields, normalize_fieldspec


def _extract_entity_from_cols(cols, fallback_name: str) -> str:
    """Extrai o nome da entidade de `cols` suportando ambos formatos:
    - Old: ['Entity', 'field1', 'field2'] -> 'Entity'
    - New: {'Entity': ['field1', 'field2']} -> 'Entity'
    """
    if not cols:
        return fallback_name
    if isinstance(cols, list) and cols:
        first = cols[0]
        if isinstance(first, str) and first[0].isupper():
            return first
    elif isinstance(cols, dict):
        first_key = next(iter(cols.keys()))
        if first_key and first_key[0].isupper():
            return first_key
    return fallback_name


def _total_decimals(f, child_model, child_merged=None):
    """Casas decimais do total de uma coluna, iguais às da linha.

    Precedência: `decimals` declarado na Entity/Schema; senão a escala da
    coluna NUM no banco (ex.: NUM(12,3) → 3, igual ao exibido na linha).
    Sem informação → None (JS usa `String`, como antes)."""
    cfg = (child_merged or {}).get(getattr(f, 'name', None), {}) or {}
    if 'decimals' in cfg:
        return cfg['decimals']
    if child_model is not None:
        try:
            t = child_model.__table__.columns[getattr(f, 'name', None)].type
            scale = getattr(t, 'scale', None)
            if scale is not None:
                return scale
        except Exception:
            pass
    return None


@dataclass
class Form:
    # ── Props declarativas (o motor resolve o restante a partir de `fields`) ──
    fields: Union[str, list, dict, None] = None
    sessions: Optional[dict] = None
    template: Optional[str] = None        # 1ª prop: se setada, demais ignoradas
    flash_ok: Optional[str] = None
    flash_update: Optional[str] = None
    readonly: Union[bool, Callable, None] = False
    delete: Union[bool, Callable, set, list, tuple, dict, None] = False
    pre_save: Optional[Callable] = None
    post_save: Optional[Callable] = None
    buttons: Optional[list] = None
    spacing: float = 2
    max_width: Optional[Union[int, str]] = None

    # ── Campos internos (preenchidos pelo motor, não declarados) ──
    def __post_init__(self):
        self._bp_name = None
        self._entity_name = None
        self._model = None
        self._schema = None
        self._schema_orig = None
        self._redirect = None
        self._label = None
        self._resolved_fields = []
        self._resolved_sessions = []
        self._resolved_buttons = resolve_buttons(self.buttons, None)
        self._resolved_tags = []

    def resolve(self, entity_name: str, model, schema: dict, blueprint=None):
        """Motor: a partir da entity nomeada, do model e do Schema da página,
        deriva campos/colunas, label, redirect e sessões.

        `schema` é o Schema original da página (chaveado por entidade); dele é
        derivado o merged do form principal e aplicados os overrides aos filhos."""
        self._entity_name = entity_name
        self._model = model
        self._schema_orig = schema or {}
        self._schema = resolve_entity_fields(self._schema_orig, model, entity_name)
        if blueprint is not None:
            self._bp_name = blueprint
        if self.template:
            return
        if not self.flash_ok:
            self.flash_ok = f'{self._label} incluído!'
        if not self.flash_update:
            self.flash_update = f'{self._label} atualizado!'
        self._resolved_fields = self._resolve_fields()
        self._resolved_sessions = self._resolve_sessions()
        self._resolved_buttons = resolve_buttons(self.buttons, self._bp_name)

    # ── Resolução de campos ──
    def _resolve_fields(self):
        spec = self.fields if self.fields is not None else (self._entity_name or ['id'])
        merged = self._schema or {}
        if isinstance(spec, str):
            # Se merged já é single-entity (chaves são campos), expande direto
            # Se merged é multi-entity (chaves são entidades), usa normalize_fieldspec
            is_multi_entity = False
            if merged:
                first_key = next(iter(merged.keys()))
                # Heurística: chave de entidade começa com maiúscula
                if first_key and first_key[0].isupper():
                    is_multi_entity = True
            
            if is_multi_entity:
                # Schema multi-entity: usa normalize_fieldspec
                if spec in merged:
                    return normalize_fieldspec(spec, merged, merged)
                if self._model is None:
                    self._model = _resolve_model(spec)
                self._entity_name = spec
                if not merged:
                    self._schema = resolve_entity_fields({}, self._model, spec)
                if not self._label:
                    self._label = _auto_label(spec)
                    self._apply_flash_defaults()
                return normalize_fieldspec(spec, self._schema, self._schema)
            else:
                # Schema single-entity: spec é nome da entidade, expande merged direto
                if self._model is None:
                    self._model = _resolve_model(spec)
                self._entity_name = spec
                if not self._label:
                    self._label = _auto_label(spec)
                    self._apply_flash_defaults()
                # Expansão de entidade → pos_managed=True
                field_names = list(merged.keys())
                return _build_fields_from_merged(field_names, merged, pos_managed=True)
        return normalize_fieldspec(spec, merged, merged)

    def _apply_flash_defaults(self):
        if not self.flash_ok:
            self.flash_ok = f'{self._label} incluído!'
        if not self.flash_update:
            self.flash_update = f'{self._label} atualizado!'

    # ── Resolução de sessões (dict puro) ──
    def _resolve_sessions(self):
        if not self.sessions:
            return []
        resolved = []
        for s_name, s_cfg in self.sessions.items():
            if isinstance(s_cfg, dict):
                spec = s_cfg
                name = spec.get('name') or s_name
                spec_fields = spec.get('fields')
                spec_query = spec.get('query')
                spec_table = spec.get('table')
                spec_template = spec.get('template')
                spec_buttons = spec.get('buttons')
            else:
                spec = s_cfg
                name = getattr(spec, 'name', None) or s_name
                spec_fields = getattr(spec, 'fields', None)
                spec_query = getattr(spec, 'query', None)
                spec_table = getattr(spec, 'table', None)
                spec_template = getattr(spec, 'template', None)
                spec_buttons = getattr(spec, 'buttons', None)

            if spec_template:
                resolved.append({'name': name, 'template': spec_template})
                continue
            if spec_query is not None and spec_table:
                raise ValueError(
                    f"Session '{name}': 'query' e 'table' são mutuamente exclusivos."
                )

            resolved_query = None
            resolved_table = None
            resolved_cols = []
            resolved_fields = []
            child_model = None
            # Sessão só com `fields` (sem query/table). O primeiro item nomeia a
            # Entity do child (sessão 1:1, ex. `['Evento', 'data']`); quando o
            # item é um campo do próprio pai (ex. `['total', 'carteira_id']`), a
            # sessão agrupa campos do pai para exibição/edição (sem child).
            is_form = spec_fields is not None and spec_query is None and spec_table is None
            is_parent = False
            if is_form:
                col_specs = spec_fields if isinstance(spec_fields, list) else [spec_fields]
                parent_schema = self._schema or {}
                first = col_specs[0] if col_specs else None
                # Parent fields grouping: first item is a field name (snake_case) in parent schema
                # Child entity: first item is entity name (PascalCase) or not in parent schema
                is_parent = (
                    isinstance(first, str)
                    and first.islower()  # field names are snake_case
                    and first in parent_schema
                )
                if is_parent:
                    resolved_fields = resolve_column_configs(
                        parent_schema, col_specs, principal=parent_schema)
                else:
                    child_ent = _extract_entity_from_cols(col_specs, name)
                    if isinstance(child_ent, str):
                        child_merged, child_model = self._child_merged(child_ent)
                        resolved_fields = self._resolve_session_cols(child_merged, col_specs, child_ent)
            elif spec_query:
                if callable(spec_query):
                    resolved_query = spec_query
                else:
                    q_cols = spec_query.get('columns') if isinstance(spec_query, dict) else getattr(spec_query, 'columns', None)
                    child_ent = _extract_entity_from_cols(q_cols, name)
                    if isinstance(child_ent, str):
                        child_merged, child_model = self._child_merged(child_ent)
                        resolved_cols = self._resolve_session_cols(child_merged, q_cols, child_ent)
                    resolved_query = {**spec_query, 'columns': resolved_cols}
            elif spec_table:
                t_cols = spec_table.get('columns') if isinstance(spec_table, dict) else getattr(spec_table, 'columns', None)
                child_ent = _extract_entity_from_cols(t_cols, name)
                if isinstance(child_ent, str):
                    child_merged, child_model = self._child_merged(child_ent)
                    resolved_cols = self._resolve_session_cols(child_merged, t_cols, child_ent)
                t_dict = dict(spec_table) if isinstance(spec_table, dict) else {k: v for k, v in spec.__dict__.items() if not k.startswith('_')}
                t_dict['columns'] = resolved_cols
                # `totals` define a linha de totais do detalhe. Aceita:
                #   - lista de nomes:            ['qtd', 'valor']
                #   - lista mista:               ['qtd', {'valor': 'total'}]
                #     item string → totaliza a coluna (sem destino);
                #     item dict {coluna: campo_master} → totaliza E grava no
                #     input do master (celula `data-total-target`).
                #   - string única:              'valor'
                # Sem `totals` nenhuma coluna é totalizada.
                spec_totals = spec_table.get('totals') if isinstance(spec_table, dict) else getattr(spec_table, 'totals', None)
                if spec_totals:
                    entries = spec_totals if isinstance(spec_totals, list) else [spec_totals]
                    total_map = {}
                    for entry in entries:
                        if isinstance(entry, dict):
                            for col, target in entry.items():
                                f = next((x for x in resolved_cols if getattr(x, 'name', None) == col), None)
                                if f is None:
                                    continue
                                total_map[f.name] = {
                                    'fn': 'sum',
                                    'calc': f.calc if getattr(f, 'calc', None) else None,
                                    'currency': getattr(f, 'currency', None) or None,
                                    'decimals': _total_decimals(f, child_model, child_merged),
                                    'target': target or None,
                                }
                        else:
                            f = next((x for x in resolved_cols if getattr(x, 'name', None) == entry), None)
                            if f is None:
                                continue
                            total_map[f.name] = {
                                'fn': 'sum',
                                'calc': f.calc if getattr(f, 'calc', None) else None,
                                    'currency': bool(getattr(f, 'currency', None)),
                                    'decimals': _total_decimals(f, child_model, child_merged),
                            }
                    if total_map:
                        t_dict['total'] = total_map
                resolved_table = t_dict

            if is_parent:
                attr = None
                child_cols = []
            else:
                attr, child_cols = self._resolve_parent_link(child_model, resolved_cols, fallback=name.lower())

            resolved.append({
                'name': name,
                'label': name,
                'attr': attr,
                'model': child_model,
                'columns': child_cols,
                'fields': resolved_fields or (
                    resolve_column_configs(self._schema or {}, spec_fields,
                                           principal=self._schema or {}) if spec_fields else []),
                'query': resolved_query,
                'table': resolved_table,
                'buttons': resolve_buttons(spec_buttons, self._bp_name) if spec_buttons else [],
            })
        return resolved

    def _resolve_parent_link(self, child_model, cols, fallback=''):
        """Descobre o vínculo pai→filho da sessão: o `attr` (relationship no
        model pai que expõe os filhos) e as colunas com a FK do pai marcadas
        `pos_form: 0` (campo gerenciado pelo motor).

        Primário: FK column → tabela pai + relationship no mapper. Fallback:
        nome/plural da classe filha, senão `fallback` (nome da sessão).
        """
        cols = list(cols or [])
        parent = self._model
        attr = None

        parent_table = None
        try:
            parent_table = parent.__tablename__
        except Exception:
            pass

        fk_name = None
        if parent_table and child_model is not None:
            for col in child_model.__table__.columns:
                if col.foreign_keys:
                    for fk in col.foreign_keys:
                        try:
                            if fk.column.table.name == parent_table:
                                fk_name = col.name
                                break
                        except Exception:
                            continue
                    if fk_name:
                        break

        if not attr and child_model is not None and parent is not None:
            try:
                from sqlalchemy.orm import MANYTOONE
                for name, rel in parent.__mapper__.relationships.items():
                    try:
                        if rel.mapper.class_ == child_model and rel.direction is not MANYTOONE:
                            attr = name
                            break
                    except Exception:
                        continue
            except Exception:
                pass
        if not attr:
            cand = child_model.__name__.lower() if child_model is not None else ''
            if cand:
                if hasattr(parent, cand):
                    attr = cand
                elif hasattr(parent, cand + 's'):
                    attr = cand + 's'
            if not attr and fallback:
                attr = fallback

        # overrides de field exclusivamente via Schema: FK do pai deve ser
        # declarado como `pos_form: 0` na Entity (DK) ou no Schema da página.
        # Removido patch automático `f.pos_form=0` que mascarava falta de declaração.
        return attr, cols

    def _child_merged(self, child_ent):
        model = _resolve_model(child_ent)
        merged = resolve_entity_fields(self._schema_orig or {}, model, child_ent)
        return merged, model

    def _resolve_session_cols(self, child_merged, cols, child_ent):
        # Nome do model/entidade → expansão da Entity: pos_form/pos_list atuam
        # (`_pos_managed=True`). Lista explícita de campos → autoritativa.
        # Passa o schema no formato multi-entidade esperado por normalize_fieldspec
        full_schema = {child_ent: child_merged}
        principal = {child_ent: child_merged}
        if cols is None:
            return normalize_fieldspec(child_ent, full_schema, principal)
        if isinstance(cols, str):
            if cols == child_ent:
                return normalize_fieldspec(child_ent, full_schema, principal)
            cols = [cols]
        elif isinstance(cols, list):
            # Formato: ['Entity'] -> expansão de todos os campos da entidade
            if cols and isinstance(cols[0], str) and cols[0][0].isupper() and cols[0] == child_ent:
                if len(cols) == 1:
                    # Apenas o nome da entidade -> expande tudo (passa string para normalize_fieldspec)
                    return normalize_fieldspec(child_ent, full_schema, principal)
                else:
                    # ['Entity', 'field1', 'field2'] -> remove nome da entidade
                    cols = cols[1:]
        return normalize_fieldspec(cols, full_schema, principal)

    def _resolve_buttons(self):
        return resolve_buttons(self.buttons, self._bp_name)

    def resolve_query_sessions(self, instance=None):
        """Resolve sessões com `query` callable, no render (com o instance).

        A query callable recebe o instance e devolve o spec do query (dict) ou
        `None` (sessão sem tabela — só fields). Preenche no dict da sessão os
        mesmos campos que `_resolve_sessions` resolveria (columns/model/attr)
        para que macros/template funcionem igual à query estática."""
        for session in getattr(self, '_resolved_sessions', []) or []:
            q = session.get('query')
            if not callable(q):
                continue
            spec = q(instance) if instance is not None else None
            if not spec:
                session['query'] = None
                session['columns'] = []
                session['model'] = None
                session['attr'] = None
                continue
            if isinstance(spec, dict):
                q_cols = spec.get('columns')
            else:
                q_cols = getattr(spec, 'columns', None)
            child_ent = _extract_entity_from_cols(q_cols, session.get('name'))
            child_model = None
            cols = []
            if isinstance(child_ent, str):
                child_merged, child_model = self._child_merged(child_ent)
                cols = self._resolve_session_cols(child_merged, q_cols, child_ent)
            session['query'] = spec
            session['columns'] = cols
            session['model'] = child_model
            if isinstance(spec, dict) and spec.get('attr'):
                session['attr'] = spec['attr']
            else:
                attr, _ = self._resolve_parent_link(child_model, cols, fallback=(session.get('name') or '').lower())
                session['attr'] = attr
        return self


_FORM_KEYS = frozenset(f.name for f in dc_fields(Form))


def parse_form(spec, **overrides):
    """Normaliza a spec de formulário (dict | Form) para `Form` (idempotente).

    Mantém apps declarando dict; o motor molda pelo dataclass. `overrides`
    (ex. `fields`, label) são aplicados ao `Form` resultante.
    """
    if isinstance(spec, Form):
        form = spec
    else:
        cfg = {k: v for k, v in (spec or {}).items() if k in _FORM_KEYS}
        form = Form(**cfg)
    for k, v in overrides.items():
        setattr(form, k, v)
    return form
