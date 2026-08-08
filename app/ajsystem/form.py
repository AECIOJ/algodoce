import importlib, inspect, os, re
from dataclasses import dataclass, field, replace
from typing import Any, Optional, Callable, Union
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy import text
from sqlalchemy.orm import MANYTOONE
from app.ajsystem.app_config import db
from app.ajsystem.list import (
    Field, MODEL_MAP, field_grid, build_field_config, _resolve_fieldset,
    _apply_transform, _infer_transform, _entidade_fields, _fk_query_for, _auto_label,
    _infer_field_from_model,
)
from app.ajsystem.buttons import Button, ACTIONS
from app.ajsystem.edits import editor_assets
from app.ajsystem.fields import VALIDATORS
from app.ajsystem.utils import item_ref


_ENTITY_LABELS = {
    'Category': 'Categoria',
    'Ingredient': 'Insumo',
    'Product': 'Produto',
    'Conta': 'Conta',
    'Carteira': 'Carteira',
    'Operacao': 'Operação',
}


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

    Ordem: `mod._label` (rótulo do menu) singularizado → `_ENTITY_LABELS` →
    nome da entidade. Usado para derivar `label`/`new_label` e as mensagens
    genéricas (`flash_ok`, `flash_update`, exclusão).
    """
    menu_label = getattr(mod, '_label', None) if mod else None
    singular = _singular(menu_label) if menu_label else None
    return singular or _ENTITY_LABELS.get(entity_name or '', entity_name or '')


def _to_pair(cond):
    if not cond:
        return None
    if isinstance(cond, dict):
        return next(iter(cond.items()))
    return tuple(cond)


def _has_references(instance, child_model):
    parent_table = instance.__class__.__tablename__
    for col in child_model.__table__.columns:
        if col.foreign_keys:
            for fk in col.foreign_keys:
                if fk.column.table.name == parent_table:
                    q = child_model.query.filter(getattr(child_model, col.name) == instance.id)
                    if db.session.query(q.exists()).scalar():
                        return True
    return False


def can_delete(instance, delete_when):
    if not delete_when:
        return True
    items = delete_when if isinstance(delete_when, (list, tuple, set)) else [delete_when]
    for item in items:
        if isinstance(item, type) and issubclass(item, db.Model):
            if _has_references(instance, item):
                return False
        elif isinstance(item, dict):
            for field_name, empty_val in item.items():
                actual = getattr(instance, field_name, None)
                if actual is not None and actual != empty_val:
                    return False
    return True


def em_uso(instance, models):
    """True se o registro é referenciado por algum dos modelos (FKs)."""
    models = models if isinstance(models, (list, tuple)) else [models]
    return any(_has_references(instance, m) for m in models)


def _pesquise_model(campo):
    """Resolve o model de `campo` (classe, entidade, slug ou nome de tabela)."""
    if isinstance(campo, type):
        return campo if getattr(campo, '__table__', None) is not None else None
    key = str(campo).strip()
    if key in MODEL_MAP:
        return MODEL_MAP[key]
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
    if snake in MODEL_MAP:
        return MODEL_MAP[snake]
    low = key.lower()
    if low in MODEL_MAP:
        return MODEL_MAP[low]
    for m in MODEL_MAP.values():
        if getattr(m, '__tablename__', None) == low:
            return m
        if getattr(m, '__name__', '').lower() == low:
            return m
    return None


def pesquise(campo, valor, retorno, destino=None, por=None):
    """Pesquisa genérica (utilitário reutilizável em qualquer módulo).

    `pesquise(Campo a pesquisar, Valor pesquisado, Campo a ser retornado,
    variavel a ser modificada)` -> True/False.

    Ex.: ok = pesquise('product', 5, 'preco', item)   # item.preco = preço
         preco = pesquise('product', 5, 'preco')      # devolve o valor
         ok = pesquise(Product, 'Limão', 'id', item, 'nome')  # por outro campo

    `campo` aceita o model, o nome da entidade ('Product'/'product') ou a
    tabela ('products'). `por` é o campo de busca (default: chave primária).
    Com `destino` (objeto com atributo `retorno` ou dict), grava e retorna
    True quando encontra, False caso contrário. Sem `destino`, devolve o valor
    encontrado (ou None).
    """
    model = _pesquise_model(campo)
    if model is None:
        return False if destino is not None else None
    table = getattr(model, '__table__', None)
    if table is None:
        return False if destino is not None else None
    cols = set(table.columns.keys())
    pk = next((c.name for c in table.primary_key.columns), 'id')
    por = por or pk
    if por not in cols or retorno not in cols:
        return False if destino is not None else None
    record = model.query.filter(getattr(model, por) == valor).first()
    if record is None:
        return False if destino is not None else None
    value = getattr(record, retorno, None)
    if destino is None:
        return value
    if isinstance(destino, dict):
        destino[retorno] = value
    elif hasattr(destino, retorno):
        setattr(destino, retorno, value)
    return True


_DEFAULT_MSG_OK = 'Excluído!'
_DEFAULT_MSG_NO = 'Não é possível excluir — está em uso.'


def _resolve_delete(delete, delete_when=None, flash_deny=None, flash_excluido=None, label=None):
    """Normaliza a config de exclusão em {'when', 'msg_ok', 'msg_no'} ou None.

    `delete` aceita: False/None (desabilita), True (habilita) ou dict com as
    chaves `when` (False desabilita; set/list de modelos para checagem FK via
    `can_delete`; callable `(instance) -> bool`; True/ausente = sempre permite),
    `msg_ok` (sucesso) e `msg_no` (bloqueado). Mantém fallback legado para
    `delete_when`, `flash_deny` e `flash_excluido` quando o dict não os define.
    """
    if delete is None or delete is False:
        return None
    if isinstance(delete, dict):
        when = delete.get('when', delete_when or True)
        if when is False:
            return None
        msg_ok = delete.get('msg_ok') or flash_excluido
        msg_no = delete.get('msg_no') or flash_deny
    else:
        when = delete_when or True
        msg_ok = flash_excluido
        msg_no = flash_deny
    return {
        'when': when,
        'msg_ok': msg_ok or (f'{label} excluído!' if label else _DEFAULT_MSG_OK),
        'msg_no': msg_no or _DEFAULT_MSG_NO,
    }


def _when_allows(when, instance):
    """True se a condição `when` do delete permite excluir `instance`."""
    if when is None or when is False:
        return False
    if when is True:
        return True
    if callable(when):
        return bool(when(instance))
    return can_delete(instance, when)


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
        if not self.buttons:
            return []
        resolved = []
        for spec in self.buttons:
            name = None
            if isinstance(spec, str):
                name = spec
                base = ACTIONS.get(name)
                if base is None:
                    raise KeyError(
                        f"Botão padrão '{name}' não existe em app.ajsystem.buttons.ACTIONS. "
                        f"Disponíveis: {', '.join(ACTIONS)}"
                    )
                btn = replace(base)
                field_name = None
            elif isinstance(spec, dict) and 'label' not in spec and len(spec) == 1:
                name, overrides = next(iter(spec.items()))
                base = ACTIONS.get(name)
                if base is None:
                    raise KeyError(
                        f"Botão padrão '{name}' não existe em app.ajsystem.buttons.ACTIONS. "
                        f"Disponíveis: {', '.join(ACTIONS)}"
                    )
                overrides = dict(overrides or {})
                field_name = overrides.pop('field', None)
                btn = replace(base, **overrides)
            else:
                cfg = dict(spec)
                btn = Button(**{
                    k: v for k, v in cfg.items()
                    if k in Button.__dataclass_fields__
                })
                field_name = cfg.get('field')
            if btn.endpoint is None and self._bp_name:
                btn.endpoint = f"{self._bp_name}.toggle"
            if btn.on_off:
                btn.field = field_name or 'ativo'
            btn.show_if = _to_pair(btn.show_if)
            btn.hide_if = _to_pair(btn.hide_if)
            resolved.append(btn)
        return resolved

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
            table_entities = cfg.get('table', [])
            meta = {}
            if table_entities and not fields_raw:
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
                        cfg_extra = {'disabled': True} if cfg.get('readonly') else {}
                        dk = _default_dk_masterkey(c, entidade)
                        fld = Field(**build_field_config(n, {**c, **dk, **cfg_extra}))
                        if n in managed:
                            fld.edit = False
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
            result.append({
                'attr': rel,
                'label': cfg.get('label', key),
                'prefix': cfg.get('prefix', rel + '_'),
                'fields': fields,
                'order_by': cfg.get('order_by'),
                'template': cfg.get('template'),
                'buttons': cfg.get('buttons'),
                'readonly': cfg.get('readonly', False) or bool(meta.get('readonly', False)),
                'single': bool(single) if single is not None else False,
                'model': child_model,
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
                    fld.edit = False
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




def _flat_fields(form):
    return form._resolved_fields


def _upload_root():
    return os.path.join(current_app.root_path, '..', 'dados', 'uploads')


def _delete_uploaded(filename):
    if not filename:
        return
    root = _upload_root()
    rel = os.path.normpath(filename)
    if rel.startswith('..') or os.path.isabs(rel):
        return
    path = os.path.join(root, rel)
    try:
        inside = os.path.commonpath([os.path.abspath(root), os.path.abspath(path)]) == os.path.abspath(root)
    except ValueError:
        inside = False
    if inside and os.path.exists(path) and os.path.isfile(path):
        os.remove(path)


def _process_image_fields(form, instance):
    """Aplica uploads temporarios e exclusoes de campos image (somente no salvar)."""
    changed = set()
    for f in form._resolved_fields:
        if f.input != 'image' or not f.edit:
            continue
        name = f.name
        old = getattr(instance, name, None)
        temp = request.form.get(f'temp_imagem_{name}', '').strip()
        remover = request.form.get(f'remover_imagem_{name}', '').strip() in ('1', 'on')
        if temp.startswith('temp_'):
            root = _upload_root()
            temp_path = os.path.join(root, os.path.basename(temp))
            if os.path.exists(temp_path):
                rel = (f.upload_path or '').strip('/')
                final_dir = os.path.join(root, rel) if rel else root
                os.makedirs(final_dir, exist_ok=True)
                ext = temp.rsplit('.', 1)[-1].lower()
                final = f'{instance.__class__.__tablename__}_{instance.id}_{name}.{ext}'
                final_name = f'{rel}/{final}' if rel else final
                if old:
                    _delete_uploaded(old)
                os.rename(temp_path, os.path.join(final_dir, final))
                setattr(instance, name, final_name)
        elif remover and old:
            _delete_uploaded(old)
            setattr(instance, name, None)
        if getattr(instance, name, None) != old:
            changed.add(name)
    return changed


def _is_readonly(form, instance):
    if not form.readonly_when or not instance:
        return False
    for k, v in form.readonly_when.items():
        actual = getattr(instance, k, None)
        if callable(v):
            if not v(actual):
                return False
        elif isinstance(v, (list, tuple, set)):
            if actual not in v:
                return False
        else:
            if actual != v:
                return False
    return True


def _build_nav(model, current_id):
    rows = db.session.execute(
        text(f'SELECT id FROM {model.__tablename__} ORDER BY id')
    ).fetchall()
    ids = [r[0] for r in rows]
    idx = ids.index(current_id) if current_id in ids else -1
    return {
        'first_id': ids[0] if ids else None,
        'last_id': ids[-1] if ids else None,
        'prev_id': ids[idx - 1] if idx > 0 else None,
        'next_id': ids[idx + 1] if 0 <= idx < len(ids) - 1 else None,
    }


def _field_raw(form_data, prefix, f):
    """Valor bruto de um campo; para `multi`, concatena os checkboxes marcados."""
    if f.input == 'multi':
        return ''.join(sorted(form_data.getlist(prefix + f.name)))
    return form_data.get(prefix + f.name)


def _coerce_field_value(f, raw):
    """Converte o valor bruto de um input para o tipo do campo (linhas filhas).

    Espelha a conversão do formulário principal; para `select` com options em
    dict, normaliza o valor para o tipo da chave correspondente (int/str).
    """
    if raw is None:
        return None
    if f.input in ('checkbox', 'boolean'):
        return raw in ('on', '1', 1, True)
    if f.input == 'number':
        s = str(raw).strip()
        if not s:
            return None
        try:
            if f.decimals is not None and f.decimals > 0:
                return float(s)
            return int(s)
        except (ValueError, TypeError):
            return None
    if f.input == 'date':
        s = str(raw).strip()
        return datetime.strptime(s, '%Y-%m-%d').date() if s else None
    if f.input == 'time':
        s = str(raw).strip()
        return datetime.strptime(s, '%H:%M').time() if s else None
    if f.input == 'datetime-local':
        s = str(raw).strip()
        return datetime.fromisoformat(s) if s else None
    val = str(raw).strip() or None
    if val and f.digits_only:
        val = re.sub(r'\D', '', val) or None
    if f.input == 'select' and isinstance(f.options, dict):
        for key in f.options:
            if str(key) == val:
                return key
    return val


def _set_parent_child(child_model, parent_model, child, instance):
    """Liga um filho ao pai (FK) via relação quando possível."""
    if parent_model is None or child_model is None:
        return
    mapper = getattr(child_model, '__mapper__', None)
    if mapper is not None:
        for name, rel in mapper.relationships.items():
            if rel.mapper.class_ is parent_model:
                setattr(child, name, instance)
                return
    for col in child_model.__table__.columns:
        for fk in col.foreign_keys:
            if fk.column.table is parent_model.__table__:
                setattr(child, col.name, instance.id)
                return


def _empty_value(val):
    if val is None:
        return True
    if isinstance(val, str):
        return val == ''
    if isinstance(val, (list, tuple, dict, set)):
        return len(val) == 0
    return False


def _save_session_children(form, instance, form_data):
    """Persistência genérica das sessions auto-derivadas.

    Parseia os inputs `child_<rel>_<rid>_<campo>` do renderizador padrão.
    Regras:
    - linha ignorada quando todos os campos editáveis estão vazios ou falta
      algum campo `required`;
    - rid numérico = registro existente (upsert); rid `n*` = novo;
    - FK para o pai preenchida automaticamente;
    - registros existentes não submetidos são excluídos.
    """
    if not form._resolved_sessions:
        return
    for session in form._resolved_sessions:
        if session.get('template'):
            continue
        if session.get('readonly'):
            continue
        rel_name = session['attr']
        child_model = session.get('model')
        if child_model is None:
            continue
        fields = [f for f in session.get('fields', []) if f.edit]
        if not fields:
            continue
        prefix = 'child_' + rel_name + '_'
        raw = getattr(instance, rel_name, None)
        if session.get('single'):
            existing = [raw] if raw is not None else []
        elif raw is None:
            existing = []
        else:
            existing = raw.all() if hasattr(raw, 'all') and callable(raw.all) else list(raw)
        if session.get('single'):
            row = {}
            has_val = False
            missing_required = False
            for f in fields:
                val = _coerce_field_value(f, _field_raw(form_data, prefix, f))
                row[f.name] = val
                if val not in (None, '', False):
                    has_val = True
                if f.required and _empty_value(val):
                    missing_required = True
            if not has_val or missing_required:
                continue
            child = existing[0] if existing else child_model()
            if not existing:
                _set_parent_child(child_model, form.model, child, instance)
                db.session.add(child)
            for fname, val in row.items():
                if hasattr(child, fname):
                    setattr(child, fname, val)
            continue
        by_ref = {}
        for i in existing:
            ref = item_ref(i, existing)
            if ref is not None:
                by_ref[str(ref)] = i
        rids = []
        seen = set()
        for k in form_data:
            if not k.startswith(prefix):
                continue
            rest = k[len(prefix):]
            if '_' not in rest:
                continue
            rid = rest.split('_', 1)[0]
            if rid not in seen:
                seen.add(rid)
                rids.append(rid)
        kept = set()
        for rid in rids:
            row = {}
            has_val = False
            missing_required = False
            for f in fields:
                val = _coerce_field_value(f, _field_raw(form_data, f'{prefix}{rid}_', f))
                row[f.name] = val
                if val not in (None, '', False):
                    has_val = True
                if f.required and _empty_value(val):
                    missing_required = True
            if not has_val or missing_required:
                continue
            child = by_ref.get(rid)
            if child is None:
                child = child_model()
                _set_parent_child(child_model, form.model, child, instance)
                db.session.add(child)
            for fname, val in row.items():
                if hasattr(child, fname):
                    setattr(child, fname, val)
            kept.add(rid)
        if session.get('single'):
            continue
        for i in existing:
            ref = item_ref(i, existing)
            if ref is None or str(ref) not in kept:
                db.session.delete(i)


def _expr_names(expr):
    return set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', expr or ''))


def _aggregate_specs(form):
    """Campos do pai com `aggregate` dict (dos campos do form e da Entity)."""
    specs = []
    seen = set()
    for f in form._resolved_fields:
        if isinstance(f.aggregate, dict) and f.aggregate.get('table') and f.aggregate.get('sum'):
            specs.append((f.name, f.aggregate))
            seen.add(f.name)
    if form.module_name:
        try:
            mod = importlib.import_module(form.module_name)
        except ImportError:
            mod = None
        if mod:
            entidade = getattr(mod, 'Entity', {}) or {}
            key = form._child_entity_key(form.model, entidade) if form.model else None
            ent_cfg = entidade.get(key, {}) if key else {}
            if isinstance(ent_cfg, dict):
                for name, cfg in _entidade_fields(ent_cfg).items():
                    if name in seen or not isinstance(cfg, dict):
                        continue
                    agg = cfg.get('aggregate')
                    if isinstance(agg, dict) and agg.get('table') and agg.get('sum'):
                        specs.append((name, agg))
                        seen.add(name)
    return specs


def _apply_aggregates(form, instance):
    """Recomputa campos do pai com `aggregate` dict após salvar os filhos.

    Ex.: `'total': {'aggregate': {'table': 'items', 'sum': 'preco_unitario * quantidade'}}`.
    A expressão é avaliada por filho com namespace restrito aos atributos.
    """
    for name, agg in _aggregate_specs(form):
        if not hasattr(instance, name):
            continue
        table = agg.get('table')
        expr = agg.get('sum')
        rel = getattr(instance, table, None)
        if rel is None:
            total = 0
        else:
            children = rel.all() if hasattr(rel, 'all') and callable(rel.all) else list(rel)
            names = _expr_names(expr)
            total = 0
            for child in children:
                ns = {n: (getattr(child, n, None) or 0) for n in names}
                try:
                    total += float(eval(expr, {'__builtins__': {}}, ns))
                except Exception:
                    continue
        setattr(instance, name, round(total, 2))


def handle_form(form_spec, id=None, extra_ctx=None, instance=None):
    form = form_spec if isinstance(form_spec, Form) else Form(**form_spec)
    instance = instance or (form.model.query.get(id) if id is not None else None)
    is_new = instance is None
    ro = _is_readonly(form, instance)

    if request.method == "POST":
        if is_new:
            instance = form.model()
            if form.defaults:
                for k, v in form.defaults.items():
                    setattr(instance, k, v)
            for f in _flat_fields(form):
                if f.default is not None:
                    setattr(instance, f.name, f.default() if callable(f.default) else f.default)
            db.session.add(instance)

        old_vals = {}
        fields_ok = True
        for f in _flat_fields(form):
            if not f.edit:
                continue
            if f.input == 'image':
                continue
            if f.input in ('checkbox', 'boolean'):
                raw = request.form.get(f.name)
                val = raw in ('on', '1', 1, True)
            elif f.input == 'number':
                raw = request.form.get(f.name, '').strip()
                if not raw:
                    val = None
                elif f.decimals is not None and f.decimals > 0:
                    try:
                        val = float(raw)
                    except (ValueError, TypeError):
                        val = None
                else:
                    try:
                        val = int(raw)
                    except (ValueError, TypeError):
                        val = None
            elif f.input in ('date',):
                raw = request.form.get(f.name, '').strip()
                val = datetime.strptime(raw, '%Y-%m-%d').date() if raw else None
            elif f.input in ('time',):
                raw = request.form.get(f.name, '').strip()
                val = datetime.strptime(raw, '%H:%M').time() if raw else None
            elif f.input in ('datetime-local',):
                raw = request.form.get(f.name, '').strip()
                val = datetime.fromisoformat(raw) if raw else None
            elif f.input == 'multi':
                val = ''.join(sorted(request.form.getlist(f.name))) or None
            else:
                val = request.form.get(f.name, '').strip() or None
                if val and f.digits_only:
                    val = re.sub(r'\D', '', val) or None
            if f.required and _empty_value(val):
                flash(f'{f.label or f.name} é obrigatório.', 'warning')
                fields_ok = False
                continue
            if val and f.validate:
                fn = VALIDATORS.get(f.validate) if isinstance(f.validate, str) else f.validate
                if callable(fn) and not fn(val):
                    flash(f'{f.label or f.name} inválido.', 'warning')
                    fields_ok = False
                    continue
            if val is not None and (f.min is not None or f.max is not None):
                try:
                    if f.min is not None and val < f.min:
                        flash(f'{f.label or f.name} deve ser maior ou igual a {f.min}.', 'warning')
                        fields_ok = False
                        continue
                    if f.max is not None and val > f.max:
                        flash(f'{f.label or f.name} deve ser menor ou igual a {f.max}.', 'warning')
                        fields_ok = False
                        continue
                except TypeError:
                    pass
            old_vals[f.name] = getattr(instance, f.name, None) if not is_new else None
            setattr(instance, f.name, val)

        if not fields_ok:
            db.session.rollback()
            return redirect(url_for(form.redirect))

        if is_new:
            db.session.flush()

        image_changed = _process_image_fields(form, instance)

        if form.pre_save:
            result = form.pre_save(instance, request, is_new)
            if result is False:
                db.session.rollback()
                return redirect(url_for(form.redirect))

        for f in form._resolved_fields:
            if not f.edit or not hasattr(instance, f.name):
                continue
            val = getattr(instance, f.name, None)
            if val is None or not isinstance(val, str):
                continue
            tr = _infer_transform(f)
            if tr == 'none':
                continue
            setattr(instance, f.name, _apply_transform(val, tr, f))

        _save_session_children(form, instance, request.form)
        db.session.flush()
        _apply_aggregates(form, instance)

        changed = {n for n, old in old_vals.items()
                    if getattr(instance, n, None) != old}
        changed |= image_changed

        db.session.commit()
        if form.post_save:
            form.post_save(instance, changed, old_vals)
        flash(form.flash_ok if is_new else form.flash_update, 'success')
        return redirect(url_for(form.redirect))

    lookup = {}
    for f in _flat_fields(form):
        if f.query and f.query in MODEL_MAP:
            model_cls = MODEL_MAP[f.query]
            q = model_cls.query
            if f.query_filter:
                for k, v in f.query_filter.items():
                    if isinstance(v, (list, tuple)):
                        q = q.filter(getattr(model_cls, k).in_(v))
                    else:
                        q = q.filter(getattr(model_cls, k) == v)
            lookup[f.name] = q.order_by(model_cls.nome).all()
    for session in form._resolved_sessions:
        for f in session.get('fields', []):
            if f.query and f.query in MODEL_MAP and f.name not in lookup:
                model_cls = MODEL_MAP[f.query]
                lookup[f.name] = model_cls.query.order_by(model_cls.nome).all()

    nav = _build_nav(form.model, id) if form.nav and id is not None else None
    _delete_cfg = _resolve_delete(form.delete, form.delete_when, form.flash_deny, form.flash_excluido, form.label)
    _can_delete = (instance is None) or (_delete_cfg is not None and _when_allows(_delete_cfg['when'], instance))

    template = form.template or 'pages/form.html'
    session_totals = {}
    for _sname, _sagg in _aggregate_specs(form):
        session_totals[_sagg['table']] = {
            'expr': _sagg['sum'],
            'currency': _sagg.get('currency'),
        }
    ctx = dict(
        instance=instance,
        form=form,
        nav=nav,
        ro=ro,
        is_new=is_new,
        _lookup=lookup,
        can_delete=_can_delete,
        _session_totals=session_totals,
    )
    _editor_inputs = {f.input for f in _flat_fields(form)}
    for _s in form._resolved_sessions:
        for _f in _s.get('fields', []):
            _editor_inputs.add(_f.input)
    _editor_js, _editor_css = editor_assets(_editor_inputs)
    ctx['_editor_js'] = [url_for('ajsystem.static', filename=_f) + '?v=1' for _f in _editor_js]
    ctx['_editor_css'] = [url_for('ajsystem.static', filename=_f) + '?v=1' for _f in _editor_css]
    if extra_ctx:
        for k, v in extra_ctx.items():
            if k == '_lookup' and isinstance(v, dict):
                ctx.setdefault('_lookup', {}).update(v)
            else:
                ctx[k] = v
    return render_template(template, **ctx)
