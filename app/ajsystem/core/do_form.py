"""Orquestrador `do_form` — request → response para formulários.

Consome o spec puro `defs.form.Form` e delega a persistência/coerção para a
capacidade `core/form.py`. É o único ponto (além de `core.do_list`) que as
rotas/`core.auto` usam para montar a página de formulário e salvar.
"""
import re
from datetime import datetime

from flask import flash, redirect, render_template, request, url_for

from app.ajsystem.core.adapter import db
from app.ajsystem.defs.form import Form
from app.ajsystem.defs.fields import VALIDATORS
from app.ajsystem.defs.entities import (
    MODEL_MAP, _apply_transform, _infer_transform,
)
from app.ajsystem.core.form import (
    _is_readonly, _flat_fields, _process_image_fields, _save_session_children,
    _apply_aggregates, _aggregate_specs, _build_nav, _resolve_delete,
    _when_allows, _session_items, _empty_value,
)
from app.ajsystem.core.edits import editor_assets
from app.ajsystem.core.query import order_items, group_items, aggregate_rows


def do_form(form_spec, id=None, extra_ctx=None, instance=None):
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
            if not f.in_form:
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
            if not f.in_form or not hasattr(instance, f.name):
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
    for _s in form._resolved_sessions:
        if not _s.get('query'):
            continue
        if _s.get('group_by'):
            _items = order_items(
                _session_items(instance, _s.get('attr')),
                _s.get('order_by'),
                _s.get('fields'),
            )
            _gf = next((f for f in _s.get('fields', []) if f.name == _s['group_by']), None)
            _spec = _s.get('group_totals') or {}
            _s['groups'] = group_items(_items, _gf, _spec, _s.get('fields'))
            _s['totals'] = aggregate_rows(_items, _spec, _s.get('fields'))
        else:
            _s['groups'] = None
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
