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
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Union
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from app.extensions import db
from app.list import Field, MODEL_MAP, field_grid, _resolve_fieldset, _apply_transform, _infer_transform
from app.buttons import Button


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


def _resolve_fields(fields_input):
    """Converte dict {nome: {cfg}} ou FieldSet {model, fields} ou lista em lista de Field."""
    if isinstance(fields_input, dict):
        if 'fields' in fields_input:
            return _resolve_fieldset(fields_input)
        return [Field(name=k, **v) for k, v in fields_input.items()]
    if isinstance(fields_input, list):
        result = []
        for item in fields_input:
            if isinstance(item, Field):
                result.append(item)
            elif isinstance(item, dict):
                name = item.get('name')
                if name:
                    rest = {k: v for k, v in item.items() if k != 'name'}
                    result.append(Field(name=name, **rest))
            else:
                result.append(item)
        return result
    return []


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
    model: type
    redirect: str
    fields: Union[dict, list]
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
        self._resolved_fields = _resolve_fields(self.fields)
        self._resolved_sessions = self._build_sessions()

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
            if f.input == 'checkbox':
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
