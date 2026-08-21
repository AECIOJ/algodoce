"""Spec `Form` — configuração declarativa de formulários (camada de dados).

Agrupa a dataclass `Form` e a resolução declarativa de campos/sessões/botões.
Não depende de renderização (`core/form.py`), de request nem do motor
(`core/auto`, `core/menu`). Dependências: stdlib, `flask.Blueprint`
(inspeção de módulo), `sqlalchemy.orm.MANYTOONE` (introspect de relações)
e `app.ajsystem.core.utils` (helpers genéricos).
"""
import importlib
import inspect
import re
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Union

from flask import Blueprint
from sqlalchemy.orm import MANYTOONE

from app.ajsystem.defs.buttons import resolve_buttons
from app.ajsystem.defs.fields import Field, _auto_label
from app.ajsystem.defs.entities import (
    MODEL_MAP, build_field_config, _resolve_fieldset,
    _entidade_fields, _fk_query_for, _infer_field_from_model,
)
from app.ajsystem.core.utils import query_label


def _detect_module_name():
    for frame_info in inspect.stack():
        mod = inspect.getmodule(frame_info.frame)
        if mod and mod.__name__.startswith('app.routes'):
            return mod.__name__
        filename = frame_info.filename
        if '/app/routes/' in filename:
            name = filename.replace('/', '.').split('app.routes.')[1].replace('.py', '')
            return 'app.routes.' + name
    return ''


def _singular(label):
    """Singulariza um rótulo plural em pt-BR (ex.: "Operações" → "Operação")."""
    s = (label or '').strip()
    if not s:
        return s
    if s.endswith('ões'):
        return s[:-3] + 'ão'
    if s.endswith('ães'):
        return s[:-3] + 'ão'
    if s.endswith('s'):
        return s[:-1]
    return s


def _default_dk_masterkey(cfg, entidade):
    """Campos `DK` (ligação filho→pai) usam a 1ª tabela da `Entity` como
    `masterkey` padrão, quando não foi especificado `masterkey`/`query`."""
    if cfg.get('type') != 'DK':
        return {}
    if 'masterkey' in cfg or 'query' in cfg:
        return {}
    if not entidade:
        return {}
    first_key = next(iter(entidade))
    key = re.sub(r'(?<!^)(?=[A-Z])', '_', first_key).lower()
    if key in MODEL_MAP:
        return {'masterkey': key}
    return {}


def _resolve_label(mod, entity_name=None):
    """Rótulo singular de uma entidade.

    Ordem: `mod._label` (rótulo do menu) singularizado → nome da entidade.
    Usado para derivar `label`/`new_label` e as mensagens genéricas
    (`flash_ok`, `flash_update`, exclusão).
    """
    menu_label = getattr(mod, '_label', None) if mod else None
    singular = _singular(menu_label) if menu_label else None
    return singular or (entity_name or '')


def _entity_containing_all(entidade, names):
    """Retorna a entrada da Entity que contém todos os nomes (ou None)."""
    str_names = [n for n in names if isinstance(n, str)]
    if not str_names:
        return None
    for ent_cfg in entidade.values():
        if isinstance(ent_cfg, dict) and all(n in ent_cfg for n in str_names):
            return ent_cfg
    return None


def _entity_for_name(entidade, name):
    """Retorna a entrada da Entity que contém o campo (ou None)."""
    for ent_cfg in entidade.values():
        if isinstance(ent_cfg, dict) and name in ent_cfg:
            return ent_cfg
    return None


def _resolve_attr(parent_model, child_model):
    if child_model is None:
        return None
    try:
        for name, rel in parent_model.__mapper__.relationships.items():
            try:
                if rel.mapper.class_ == child_model:
                    return name
            except Exception:
                continue
    except Exception:
        pass
    name = child_model.__name__.lower()
    if hasattr(parent_model, name):
        return name
    plural = name + 's'
    if hasattr(parent_model, plural):
        return plural
    return None


def _rel_for_model(parent_model, child_model):
    """Relacionamento pai→filho (uselist) entre os models, ou None."""
    if parent_model is None or child_model is None:
        return None
    try:
        for name, rel in parent_model.__mapper__.relationships.items():
            try:
                if rel.mapper.class_ == child_model and rel.direction is not MANYTOONE:
                    return rel, name
            except Exception:
                continue
    except Exception:
        pass
    return None


@dataclass
class Form:
    model: Optional[type] = None
    redirect: Optional[str] = None
    fields: Union[str, list, dict, None] = None
    entity_name: Optional[str] = None
    module_name: Optional[str] = None
    field_overrides: Optional[dict] = None
    sessions: Optional[dict] = None
    template: Optional[str] = None
    flash_ok: Optional[str] = None
    flash_update: Optional[str] = None
    nav: bool = True
    readonly_when: Optional[dict] = None
    pre_save: Optional[Callable] = None
    post_save: Optional[Callable] = None
    tag: Optional[dict] = None
    buttons: Optional[list] = None
    delete_when: Union[set, dict, list, tuple] = field(default_factory=dict)
    defaults: Optional[dict] = None
    new_label: Optional[str] = None
    new_title: Optional[str] = None
    label: Optional[str] = None
    back_url: Optional[str] = None
    edit_endpoint: Optional[str] = None
    nav_right_extra: Optional[str] = None
    body_template: Optional[str] = None
    form_tail: Optional[str] = None
    footer_left: Optional[str] = None
    page_scripts: Optional[str] = None
    badge: Optional[dict] = None
    tags: Optional[list] = None
    extra_buttons: Optional[list] = None
    children: Optional[list] = None
    spacing: float = 2
    delete: Union[bool, dict] = False
    toggle: Optional[str] = None
    flash_deny: Optional[str] = None
    flash_excluido: Optional[str] = None
    flash_toggle: Optional[str] = None

    def __post_init__(self):
        if self.badge and not self.tag:
            self.tag = self.badge
        if self.extra_buttons and not self.buttons:
            self.buttons = self.extra_buttons
        if not self.module_name:
            self.module_name = _detect_module_name()
        mod = importlib.import_module(self.module_name) if self.module_name else None
        if isinstance(self.fields, str):
            self.entity_name = self.fields
        elif isinstance(self.fields, list) and not self.entity_name and mod:
            names = [f['name'] if isinstance(f, dict) else f for f in self.fields]
            for ent_name, ent_cfg in getattr(mod, 'Entity', {}).items():
                ent_fields = set(ent_cfg.keys())
                if names and all(n in ent_fields for n in names):
                    self.entity_name = ent_name
                    break
        if not self.model and self.entity_name and mod:
            self.model = self._resolve_entity_model(self.entity_name, mod)
        if not self.model and isinstance(self.fields, dict) and 'model' in self.fields:
            self.model = self.fields['model']
        if not self.entity_name and self.model:
            self.entity_name = self.model.__name__
        self._bp_name = None
        if mod:
            for name in dir(mod):
                obj = getattr(mod, name, None)
                if isinstance(obj, Blueprint):
                    self._bp_name = obj.name
                    break
        if not self.redirect and self._bp_name:
            self.redirect = f"{self._bp_name}.list"
        if not self.label:
            self.label = self.new_label or _resolve_label(mod, self.entity_name)
        if not self.new_label:
            self.new_label = self.label
        if not self.flash_ok:
            self.flash_ok = f'{self.label} incluído!'
        if not self.flash_update:
            self.flash_update = f'{self.label} atualizado!'
        self._resolved_fields = self._resolve_fields()
        self._derive_field_queries()
        self._resolved_sessions = self._build_sessions()
        self._resolved_buttons = self._resolve_buttons()

    def _derive_field_queries(self):
        """Deriva `query` de FKs do form principal sem `masterkey`/`query` (§5.4)."""
        if self.model is None:
            return
        for f in self._resolved_fields:
            if f.input == 'select' and f.query is None and f.options is None:
                query = _fk_query_for(self.model, f.name)
                if query:
                    f.query = query

    def _resolve_buttons(self):
        return resolve_buttons(self.buttons, self._bp_name)

    def _resolve_fields(self):
        if isinstance(self.fields, str):
            mod = importlib.import_module(self.module_name)
            entidade = getattr(mod, 'Entity', {}).get(self.fields, {})
            overrides = self.field_overrides or {}
            return [Field(**build_field_config(n, {**c, **overrides.get(n, {})}))
                    for n, c in _entidade_fields(entidade).items()]
        elif isinstance(self.fields, list):
            return self._resolve_fields_list(self.fields)
        elif isinstance(self.fields, dict):
            cfg = self.fields
            if 'fields' in cfg:
                return _resolve_fieldset(cfg, self.field_overrides)
            entity = cfg.get('entity') or self.entity_name
            mod = importlib.import_module(self.module_name)
            entidade = getattr(mod, 'Entity', {}).get(entity, {})
            allowed = cfg.get('only', [])
            overrides = cfg.get('overrides', {})
            result = []
            for n, c in _entidade_fields(entidade).items():
                if allowed and n not in allowed:
                    continue
                merged = {**c, **overrides.get(n, {})}
                result.append(Field(**build_field_config(n, merged)))
            return result
        return []

    def _resolve_fields_list(self, names):
        mod = importlib.import_module(self.module_name) if self.module_name else None
        entidade = getattr(mod, 'Entity', {}) if mod else {}
        overrides = self.field_overrides or {}
        if self.entity_name and self.entity_name in entidade:
            primary = entidade[self.entity_name]
        else:
            primary = _entity_containing_all(entidade, names)
        result = []
        for f in names:
            if isinstance(f, Field):
                result.append(f)
                continue
            name = f if isinstance(f, str) else f.get('name', '')
            ent_cfg = primary if primary else _entity_for_name(entidade, name)
            cfg = {}
            if isinstance(ent_cfg, dict):
                base = ent_cfg.get(name, {})
                if isinstance(base, dict):
                    cfg = dict(base)
            if isinstance(f, dict):
                merged = {**cfg, **{k: v for k, v in f.items() if k != 'name'}}
                inferred = _infer_field_from_model(self.model, name)
                merged = {**inferred, **cfg, **{k: v for k, v in f.items() if k != 'name'}}
                result.append(Field(**build_field_config(name, merged)))
            else:
                inferred = _infer_field_from_model(self.model, name)
                merged = {**inferred, **cfg, **overrides.get(name, {})}
                result.append(Field(**build_field_config(name, merged)))
        return result

    def _build_sessions(self):
        if self.sessions is None:
            return self._auto_sessions()
        if not self.sessions:
            return []
        result = []
        for key, cfg in self.sessions.items():
            if isinstance(cfg, str):
                result.append({'attr': key, 'template': cfg})
                continue
            model = cfg.get('model')
            child_model = model if isinstance(model, type) else None
            if not child_model and isinstance(model, str):
                mod = importlib.import_module(self.module_name) if self.module_name else None
                if mod:
                    child_model = getattr(mod, model, None)
            fields_raw = cfg.get('fields', [])
            query_raw = cfg.get('query')
            query_cfg = None
            if isinstance(query_raw, str):
                _mod = importlib.import_module(self.module_name) if self.module_name else None
                _queries = getattr(_mod, 'Query', {}) if _mod else {}
                query_cfg = _queries.get(query_raw)
                if query_cfg is None:
                    raise KeyError(
                        f"Query '{query_raw}' não definida em {self.module_name}. "
                        f"Disponíveis: {', '.join(_queries) or 'nenhuma'}"
                    )
            elif isinstance(query_raw, dict):
                query_cfg = query_raw
            fields = []
            if isinstance(fields_raw, dict):
                if 'fields' in fields_raw:
                    fields = _resolve_fieldset(fields_raw)
                else:
                    for n, c in fields_raw.items():
                        fields.append(Field(**build_field_config(n, c)))
            else:
                for f in fields_raw:
                    if isinstance(f, str):
                        fields.append(Field(**build_field_config(f, {})))
                    elif isinstance(f, dict):
                        fields.append(Field(**build_field_config(f.get('name', ''), f)))
            query_entities = None
            if query_cfg is not None:
                for f in (query_cfg.get('fields') or []):
                    if isinstance(f, str):
                        query_entities = (query_entities or []) + [f]
                    else:
                        fields.append(Field(**build_field_config(f.get('name', ''), f)))
            else:
                query_entities = cfg.get('query') if isinstance(cfg.get('query'), (list, tuple)) else None
            table_entities = query_entities if query_entities is not None else cfg.get('table', [])
            meta = {}
            if table_entities and (query_cfg is not None or not fields_raw):
                mod = importlib.import_module(self.module_name) if self.module_name else None
                entidade = getattr(mod, 'Entity', {}) if mod else {}
                for ent_name in table_entities:
                    ent_cfg = entidade.get(ent_name, {}) or {}
                    if child_model is None:
                        child_model = self._resolve_entity_model(ent_name, mod)
                    meta = ent_cfg.get('__meta__', {}) if isinstance(ent_cfg, dict) else {}
                    meta = meta if isinstance(meta, dict) else {}
                    managed = self._managed_field_names(child_model)
                    for n, c in _entidade_fields(ent_cfg).items():
                        cfg_extra = {'disabled': True} if (cfg.get('readonly') or query_entities is not None) else {}
                        dk = _default_dk_masterkey(c, entidade)
                        fld = Field(**build_field_config(n, {**c, **dk, **cfg_extra}))
                        if n in managed:
                            fld.in_form = 0
                        elif fld.query is None and fld.input == 'select' and not fld.options:
                            query = _fk_query_for(child_model, fld.name)
                            if query:
                                fld.query = query
                        if fld.on_set:
                            fld.on_set_ent = ent_name
                            fld.on_set_mod = self.module_name
                        fields.append(fld)
            rel = cfg.get('attr') or _resolve_attr(self.model, child_model) or key
            if cfg.get('attr') is None and child_model is not None:
                rel_pair = _rel_for_model(self.model, child_model)
                if rel_pair is not None:
                    rel = rel_pair[1]
            single = cfg.get('single')
            if single is None and child_model is not None:
                rel_pair = _rel_for_model(self.model, child_model)
                single = rel_pair is not None and not rel_pair[0].uselist
            is_report = query_entities is not None or query_cfg is not None
            group_by = None
            group_totals = None
            order_by = cfg.get('order_by')
            if is_report:
                if query_cfg is not None:
                    group_by = query_cfg.get('group_by')
                    group_totals = query_cfg.get('totals')
                    if query_cfg.get('order_by'):
                        order_by = query_cfg.get('order_by')
                else:
                    group_by = cfg.get('group_by')
                    group_totals = cfg.get('group_totals')
            if is_report and group_by:
                for f in fields:
                    if f.name == group_by:
                        f.in_form = 0
            result.append({
                'attr': rel,
                'label': query_label(query_cfg, key) if query_cfg is not None else cfg.get('label', key),
                'prefix': cfg.get('prefix', rel + '_'),
                'fields': fields,
                'order_by': order_by,
                'template': cfg.get('template'),
                'buttons': cfg.get('buttons'),
                'readonly': True if is_report else (cfg.get('readonly', False) or bool(meta.get('readonly', False))),
                'single': False if is_report else (bool(single) if single is not None else False),
                'model': child_model,
                'query': is_report,
                'group_by': group_by,
                'group_totals': group_totals,
            })
        return result

    def _auto_sessions(self):
        """Sessões derivadas dos relacionamentos do modelo + `Entity`.

        Roda quando `sessions` não é declarado. Cada relação filha (ONETOMANY/
        ONETOONE) cujo modelo alvo tenha uma entrada correspondente em
        `Entity` vira uma sessão. FK para o pai e PKs são marcados
        `edit=False`; FKs para outros modelos têm o `query` derivado da relação.
        """
        if not self.model:
            return []
        mod = importlib.import_module(self.module_name) if self.module_name else None
        entidade = getattr(mod, 'Entity', {}) if mod else {}
        mapper = getattr(self.model, '__mapper__', None)
        if mapper is None:
            return []
        sessions = []
        for name, rel in mapper.relationships.items():
            if rel.direction is MANYTOONE:
                continue
            if rel.secondary is not None:
                continue
            if getattr(rel, 'viewonly', False):
                continue
            child_model = rel.mapper.class_
            if child_model is self.model:
                continue
            ent_key = self._child_entity_key(child_model, entidade)
            if ent_key is None:
                continue
            ent_cfg = entidade.get(ent_key, {}) or {}
            meta = ent_cfg.get('__meta__', {}) if isinstance(ent_cfg, dict) else {}
            meta = meta if isinstance(meta, dict) else {}
            managed = {
                c.name for c in child_model.__table__.primary_key.columns
                if not any(c.foreign_keys)
            }
            managed |= self._parent_fk_names(child_model)
            fields = []
            for n, c in _entidade_fields(ent_cfg).items():
                dk = _default_dk_masterkey(c, entidade)
                fld = Field(**build_field_config(n, {**dict(c), **dk}))
                if n in managed:
                    fld.in_form = 0
                elif fld.query is None and fld.input == 'select' and not fld.options:
                    query = _fk_query_for(child_model, fld.name)
                    if query:
                        fld.query = query
                if fld.on_set:
                    fld.on_set_ent = ent_key
                    fld.on_set_mod = self.module_name
                fields.append(fld)
            sessions.append({
                'attr': name,
                'label': meta.get('label') or _auto_label(name),
                'prefix': name + '_',
                'fields': fields,
                'order_by': None,
                'template': None,
                'buttons': None,
                'readonly': bool(meta.get('readonly', False)),
                'single': not rel.uselist,
                'auto': True,
                'model': child_model,
            })
        return sessions

    def _child_entity_key(self, child_model, entidade):
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', child_model.__name__).lower()
        candidates = {child_model.__name__, child_model.__name__.lower(), snake}
        for key in entidade:
            if key in candidates:
                return key
        return None

    def _parent_fk_names(self, child_model):
        names = set()
        if self.model is None or child_model is None:
            return names
        parent_table = self.model.__table__
        for col in child_model.__table__.columns:
            for fk in col.foreign_keys:
                if fk.column.table is parent_table:
                    names.add(col.name)
        return names

    def _managed_field_names(self, child_model):
        if child_model is None:
            return set()
        managed = {
            c.name for c in child_model.__table__.primary_key.columns
            if not any(c.foreign_keys)
        }
        managed |= self._parent_fk_names(child_model)
        return managed

    def _resolve_entity_model(self, ent_name, mod=None):
        """Resolve uma Entity-key para o model (MODEL_MAP > attr do módulo > app.models)."""
        key = re.sub(r'(?<!^)(?=[A-Z])', '_', ent_name).lower()
        if key in MODEL_MAP:
            return MODEL_MAP[key]
        if mod is not None:
            m = getattr(mod, ent_name, None)
            if isinstance(m, type) and getattr(m, '__table__', None) is not None:
                return m
        try:
            mod2 = importlib.import_module(f'app.models.{key}')
            m = getattr(mod2, ent_name, None)
            if isinstance(m, type) and getattr(m, '__table__', None) is not None:
                return m
        except ImportError:
            pass
        return None
