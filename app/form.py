"""
XXX_FORM — Configuração centralizada de formulários.

Cada rota sys_*.py declara:
  XXX_FORM = Form(model=Model, redirect='module.list', fields=[...])

A rota unificada:
  @bp.route("/<path>", defaults={"id": None}, methods=["GET", "POST"])
  @bp.route("/<path>/<int:id>", methods=["GET", "POST"])
  def form(id):
      return handle_form(XXX_FORM, id)
"""
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from app.extensions import db
from app.table import Field, MODEL_MAP, field_grid
from app.buttons import Button


@dataclass
class Form:
    model: type
    redirect: str
    fields: list  # list of Field or dict (section group)
    children: Optional[list] = None  # list of dict
    template: Optional[str] = None
    flash_ok: str = 'Salvo!'
    flash_update: str = 'Atualizado!'
    nav: bool = True
    readonly_when: Optional[dict] = None  # ex: {'pedido_id': None} or {'status': [9]}
    pre_save: Optional[Callable] = None
    post_save: Optional[Callable] = None
    badge: Optional[dict] = None
    extra_buttons: Optional[list] = None
    delete_enabled: bool = False
    delete_check_usage: Optional[Callable] = None


def _is_readonly(form, instance):
    if not form.readonly_when or not instance:
        return False
    for field_name, value in form.readonly_when.items():
        actual = getattr(instance, field_name, None)
        if isinstance(value, (list, tuple)):
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


def _is_flat_field(item):
    return isinstance(item, Field)


def _is_section_group(item):
    return isinstance(item, dict) and 'fields' in item


def _flat_fields(form):
    for item in form.fields:
        if _is_flat_field(item):
            yield item
        elif _is_section_group(item):
            yield from item['fields']


def handle_form(form, id=None, extra_ctx=None):
    instance = form.model.query.get(id) if id is not None else None
    is_new = instance is None
    ro = _is_readonly(form, instance)

    if request.method == "POST":
        if is_new:
            instance = form.model()
            db.session.add(instance)

        old_vals = {}
        fields_ok = True
        for f in _flat_fields(form):
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
            form.pre_save(instance, request, is_new)

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

    template = form.template or f'sys_{form.model.__tablename__}/form.html'
    ctx = dict(
        instance=instance,
        form=form,
        nav=nav,
        ro=ro,
        is_new=is_new,
        _lookup=lookup,
    )
    if extra_ctx:
        ctx.update(extra_ctx)
    return render_template(template, **ctx)
