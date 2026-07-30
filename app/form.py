"""
XXX_FORM — Configuração centralizada de formulários.

Cada rota sys_*.py declara:
  XXX_FORM = Form(model=Model, redirect='module.list', fields=FIELDSET)

A rota unificada:
  @bp.route("/<path>", defaults={"id": None}, methods=["GET", "POST"])
  @bp.route("/<path>/<int:id>", methods=["GET", "POST"])
  def form(id):
      return handle_form(XXX_FORM, id)
"""
import importlib, inspect
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Union
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.list import Field, MODEL_MAP, field_grid, build_field_config, _resolve_fieldset, _apply_transform, _infer_transform
from app.buttons import Button


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
    return ''


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
    items = delete_when if isinstance(delete_when, (list, tuple)) else [delete_when]
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


def _resolve_attr(parent_model, child_model):
    """Encontra o nome da relationship entre parent e child.
    Tenta SQLAlchemy mapper primeiro, fallback para convenção.
    """
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
    flash_ok: str = 'Salvo!'
    flash_update: str = 'Atualizado!'
    nav: bool = True
    readonly_when: Optional[dict] = None
    pre_save: Optional[Callable] = None
    post_save: Optional[Callable] = None
    tag: Optional[dict] = None
    buttons: Optional[list] = None
    delete_when: Union[set, dict, list, tuple] = field(default_factory=dict)

    defaults: Optional[dict] = None

    # template partials / config (auto-render pattern)
    entity_label: Optional[str] = None
    new_title: Optional[str] = None
    back_url: Optional[str] = None
    edit_endpoint: Optional[str] = None
    nav_right_extra: Optional[str] = None
    body_template: Optional[str] = None
    form_tail: Optional[str] = None
    footer_left: Optional[str] = None
    page_scripts: Optional[str] = None

    # backward compat aliases
    badge: Optional[dict] = None
    extra_buttons: Optional[list] = None
    children: Optional[list] = None

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
            for ent_name, ent_cfg in getattr(mod, 'Entidade', {}).items():
                ent_fields = set(ent_cfg.keys())
                if all(f in ent_fields for f in self.fields):
                    self.entity_name = ent_name
                    break

        if not self.model and self.entity_name and mod:
            self.model = getattr(mod, self.entity_name)
        if not self.model and isinstance(self.fields, dict) and 'model' in self.fields:
            self.model = self.fields['model']
        if not self.entity_name and self.model:
            self.entity_name = self.model.__name__

        if not self.redirect and mod:
            bp_name = None
            for name in dir(mod):
                obj = getattr(mod, name, None)
                if isinstance(obj, Blueprint):
                    bp_name = obj.name
                    break
            if bp_name:
                self.redirect = f"{bp_name}.list"

        if not self.entity_label and self.entity_name:
            self.entity_label = _ENTITY_LABELS.get(self.entity_name, self.entity_name)

        self._resolved_fields = self._resolve_fields()
        self._resolved_sessions = self._build_sessions()

    def _resolve_fields(self):
        if isinstance(self.fields, str):
            mod = importlib.import_module(self.module_name)
            entidade = getattr(mod, 'Entidade', {}).get(self.fields, {})
            overrides = self.field_overrides or {}
            return [Field(**build_field_config(n, {**c, **overrides.get(n, {})}))
                    for n, c in entidade.items()]
        if isinstance(self.fields, list):
            mod = importlib.import_module(self.module_name)
            entidade = getattr(mod, 'Entidade', {}).get(self.entity_name, {})
            overrides = self.field_overrides or {}
            result = []
            for name in self.fields:
                cfg = entidade.get(name, {})
                merged = {**cfg, **overrides.get(name, {})}
                result.append(Field(**build_field_config(name, merged)))
            return result
        if isinstance(self.fields, dict):
            if 'model' in self.fields and 'fields' in self.fields:
                return _resolve_fieldset(self.fields)
            mod = importlib.import_module(self.module_name)
            entidade = getattr(mod, 'Entidade', {})
            overrides = self.field_overrides or {}
            result = []
            for ent_name, field_names in self.fields.items():
                for name in field_names:
                    cfg = entidade.get(ent_name, {}).get(name, {})
                    merged = {**cfg, **overrides.get(name, {})}
                    result.append(Field(**build_field_config(name, merged)))
            return result
        if self.fields is None and self.entity_name and self.module_name:
            mod = importlib.import_module(self.module_name)
            entidade = getattr(mod, 'Entidade', {}).get(self.entity_name, {})
            overrides = self.field_overrides or {}
            return [Field(**build_field_config(n, {**c, **overrides.get(n, {})}))
                    for n, c in entidade.items()]
        return []

    SESSION_PREFIXES = ('*',)

    def _build_sessions(self):
        if not self.sessions:
            return []
        result = []
        for label, session_cfg in self.sessions.items():
            when = session_cfg.get('when') if isinstance(session_cfg, dict) else None

            if isinstance(session_cfg, dict) and session_cfg.get('type') == 'template':
                result.append({
                    'label': label,
                    'type': 'template',
                    'template': session_cfg.get('template'),
                    'when': when,
                })
                continue

            if isinstance(session_cfg, dict) and 'table' in session_cfg:
                mod = importlib.import_module(self.module_name)
                entidade = getattr(mod, 'Entidade', {})
                table_fields = session_cfg['table']
                if isinstance(table_fields, str):
                    entity_name = table_fields
                    entity_cfg = entidade.get(entity_name, {})
                    field_names = list(entity_cfg.keys())
                else:
                    first = table_fields[0] if table_fields else None
                    if first and first in entidade:
                        entity_name = first
                        entity_cfg = entidade[entity_name]
                        field_names = [f for f in entity_cfg if f not in ('id',)]
                    else:
                        entity_name = next((n for n, c in entidade.items()
                                            if all(f in c for f in table_fields)), None)
                        if not entity_name:
                            continue
                        entity_cfg = entidade[entity_name]
                        field_names = table_fields
                entity_cfg = entidade[entity_name]
                child_model = getattr(mod, entity_name)
                fields_list = [Field(**build_field_config(n, entity_cfg[n])) for n in field_names]
                attr = session_cfg.get('attr') or _resolve_attr(self.model, child_model)
                prefix = session_cfg.get('prefix') or (attr + '_' if attr else None)
                readonly = session_cfg.get('readonly', False)
                result.append({
                    'label': label, 'model': child_model, 'attr': attr,
                    'prefix': prefix, 'fields': fields_list,
                    'type': 'table' if readonly else 'editable_table',
                    'template': None, 'readonly': readonly,
                    'when': when, 'buttons': session_cfg.get('buttons'),
                })
                continue

            prefix_char = label[0] if label and label[0] in self.SESSION_PREFIXES else None

            if prefix_char:
                fields_list = [f for f in self._resolved_fields if f.edit == prefix_char]
                result.append({
                    'label': label.lstrip(prefix_char),
                    'model': None,
                    'attr': None,
                    'prefix': None,
                    'fields': fields_list,
                    'type': 'fields',
                    'template': None,
                    'readonly': False,
                    'when': when,
                    'buttons': session_cfg.get('buttons') if isinstance(session_cfg, dict) else None,
                })
                continue

            fs = session_cfg
            buttons = None
            child_model = None
            session_type = 'fields'
            session_attr = None
            session_template = None
            if isinstance(session_cfg, dict) and 'fields' in session_cfg:
                inner = session_cfg.get('fields')
                buttons = session_cfg.get('buttons')
                session_type = session_cfg.get('type', 'fields')
                session_attr = session_cfg.get('attr')
                session_template = session_cfg.get('template')
                if isinstance(inner, dict) and 'fields' in inner:
                    child_model = inner.get('model')
                    fs = inner
                else:
                    child_model = session_cfg.get('model')
                    fs = session_cfg
            elif not isinstance(session_cfg, dict):
                fs = {'fields': session_cfg}
            else:
                fs = session_cfg
            child_model = child_model or fs.get('model')
            attr = session_attr or (_resolve_attr(self.model, child_model) if child_model else None)
            fields_list = _resolve_fieldset(fs)
            prefix = session_cfg.get('prefix') if isinstance(session_cfg, dict) else None
            if not prefix:
                prefix = (attr + '_') if attr else None
            result.append({
                'label': label,
                'model': child_model,
                'attr': attr,
                'prefix': prefix,
                'fields': fields_list,
                'type': session_type,
                'template': session_template,
                'readonly': fs.get('readonly', False),
                'when': when,
                'buttons': buttons,
            })
        return result


def _is_readonly(form, instance):
    if not form.readonly_when or not instance:
        return False
    for field_name, value in form.readonly_when.items():
        actual = getattr(instance, field_name, None)
        if callable(value):
            if value(actual):
                return True
        elif isinstance(value, (list, tuple)):
            if actual in value:
                return True
        else:
            if actual == value:
                return True
    return False


def _build_nav(model, id):
    query = model.query.with_entities(model.id).order_by(model.id)
    ids = [r.id for r in query.all()]
    try:
        current_idx = ids.index(id)
        return {
            "first_id": ids[0],
            "last_id": ids[-1],
            "prev_id": ids[current_idx - 1] if current_idx > 0 else None,
            "next_id": ids[current_idx + 1] if current_idx < len(ids) - 1 else None,
        }
    except ValueError:
        return {"first_id": None, "last_id": None, "prev_id": None, "next_id": None}


def _flat_fields(form):
    for f in form._resolved_fields:
        yield f


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
                    setattr(instance, f.name, f.default)
            db.session.add(instance)

        old_vals = {}
        fields_ok = True
        for f in _flat_fields(form):
            if not f.edit:
                continue
            if f.input in ('checkbox', 'boolean'):
                raw = request.form.get(f.name)
                val = raw in ('on', '1', 1, True)
            elif f.input == 'number':
                raw = request.form.get(f.name, '').strip()
                try:
                    val = int(raw) if raw else None
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
            else:
                val = request.form.get(f.name, '').strip() or None
            if f.required and not val:
                flash(f'{f.label or f.name} é obrigatório.', 'warning')
                fields_ok = False
                continue
            old_vals[f.name] = getattr(instance, f.name, None) if not is_new else None
            setattr(instance, f.name, val)

        if not fields_ok:
            db.session.rollback()
            return redirect(url_for(form.redirect))

        if is_new:
            db.session.flush()

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

        changed = {n for n, old in old_vals.items()
                    if getattr(instance, n, None) != old}

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
    _can_delete = can_delete(instance, form.delete_when) if instance else True

    template = form.template or 'components/form_default.html'
    ctx = dict(
        instance=instance,
        form=form,
        nav=nav,
        ro=ro,
        is_new=is_new,
        _lookup=lookup,
        can_delete=_can_delete,
    )
    if extra_ctx:
        for k, v in extra_ctx.items():
            if k == '_lookup' and isinstance(v, dict):
                ctx.setdefault('_lookup', {}).update(v)
            else:
                ctx[k] = v
    return render_template(template, **ctx)
