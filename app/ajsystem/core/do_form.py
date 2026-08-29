"""Orquestrador `do_form` — request → response para formulários.

Reescrito do zero observando `core/old/do_form.py`. Consome o spec puro
`defs.form.Form` e delega persistência/coerção a `core/form.py` e validação/
transform a `defs.validators`/`defs.transformers`.
"""
import re

from flask import flash, redirect, render_template, request, url_for

from app.ajsystem.core.adapter import db
from app.ajsystem.core.form import (
    _empty_value, _coerce, _is_readonly, _flat_fields, _process_image_fields,
    _build_nav, _resolve_delete, _when_allows,
)
from app.ajsystem.defs.data import fk_target_model
from app.ajsystem.defs.validators import resolve_validator
from app.ajsystem.defs.transformers import apply_field_transforms


def _resolve_tag_color(value, options=None, colors=None):
    if colors and value in colors:
        return colors[value]
    if options and value in options:
        label = str(options[value]).lower()
    else:
        label = str(value).lower() if value is not None else ''
    if any(w in label for w in ('aprovado', 'renovado', 'ativo', 'pago', 'entregue')):
        return 'success'
    if any(w in label for w in ('reprovado', 'rejeitado', 'expirado', 'cancelado', 'inativo', 'atrasado')):
        return 'error'
    if any(w in label for w in ('negociação', 'negociacao', 'pendente', 'aguardando', 'enviado')):
        return 'warning'
    if any(w in label for w in ('rocessando', 'andamento', 'faturado')):
        return 'info'
    if isinstance(value, (int, float)):
        if value <= 2:
            return 'warning'
        if value <= 6:
            return 'info'
        return 'error'
    return 'ghost'


def _build_lookup(form, extra_lookup=None):
    """Popula `_lookup` (legado) para FKs — `{campo: [instâncias alvo]}`.

    Para cada campo `select` sem `options`, resolve o model alvo do FK e
    carrega as instâncias (usadas pelo template para montar os `<option>` e
    exibir o nome em vez do id). `extra_lookup` tem prioridade.
    """
    lookup = dict(extra_lookup or {})

    def fill(f, src_model):
        if f.input != 'select' or f.options is not None:
            return
        if f.name in lookup:
            return
        tgt = None
        q = f.query
        if q is not None:
            mk = q if isinstance(q, str) else (q.get('model') if isinstance(q, dict) else getattr(q, 'model', None))
            if mk:
                from app.ajsystem.core.list import _resolve_model
                try:
                    tgt = _resolve_model(mk)
                except Exception:
                    tgt = None
        if tgt is None:
            tgt = fk_target_model(src_model, f.name)
        if tgt is None or getattr(tgt, '__table__', None) is None:
            return
        lookup[f.name] = list(tgt.query.all())

    for f in _flat_fields(form):
        fill(f, form._model)
    for session in form._resolved_sessions:
        child_model = session.get('model')
        for f in (session.get('columns') or []) or []:
            fill(f, child_model)
    return lookup


def do_form(form, id=None, extra_ctx=None, instance=None):
    """GET: renderiza o form (novo/editar). POST: valida, salva e redireciona."""
    instance = instance or (form._model.query.get(id) if id is not None else None)
    is_new = instance is None
    ro = _is_readonly(form, instance)

    if request.method == "POST":
        if is_new:
            instance = form._model()
            for f in _flat_fields(form):
                if f.default is not None:
                    setattr(instance, f.name, f.default() if callable(f.default) else f.default)
            db.session.add(instance)

        old_vals = {}
        fields_ok = True
        for f in _flat_fields(form):
            if f.in_form != 1:
                continue
            if f.calc:
                continue
            if f.input == 'image':
                continue
            if f.input == 'multi':
                raw = request.form.getlist(f.name)
            else:
                raw = request.form.get(f.name)
            val = _coerce(raw, f)
            if f.required and _empty_value(val):
                flash(f'{f.label or f.name} é obrigatório.', 'warning')
                fields_ok = False
                continue
            if val and f.validate:
                validator = resolve_validator(f.validate)
                if callable(validator) and not validator(val):
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
            return redirect(url_for(form._redirect))

        if is_new:
            db.session.flush()

        image_changed = _process_image_fields(form, instance)

        if form.pre_save:
            result = form.pre_save(instance, request, is_new)
            if result is False:
                db.session.rollback()
                return redirect(url_for(form._redirect))

        apply_field_transforms(instance, form._resolved_fields)

        db.session.flush()
        db.session.commit()

        changed = {n for n, old in old_vals.items()
                   if getattr(instance, n, None) != old}
        changed |= image_changed
        if form.post_save:
            form.post_save(instance, changed, old_vals)
        flash(form.flash_ok if is_new else form.flash_update, 'success')
        return redirect(url_for(form._redirect))

    nav = _build_nav(form._model, id) if id is not None else None
    _delete_cfg = _resolve_delete(form.delete, label=form._label)
    _can_delete = (instance is None) or (
        _delete_cfg is not None and _when_allows(_delete_cfg['when'], instance))

    template = form.template or 'pages/form.html'

    _resolved_tags = []
    if form.tags and instance:
        for tag_spec in form.tags:
            if isinstance(tag_spec, str):
                fname, colors = tag_spec, None
            else:
                fname = tag_spec.get('field', tag_spec.get('name'))
                colors = tag_spec.get('colors')
            f_obj = next((f for f in _flat_fields(form) if f.name == fname), None)
            val = getattr(instance, fname, None)
            options = f_obj.options if f_obj else None
            label = str(options.get(val, val)) if (options and val in options) else (str(val) if val is not None else '')
            _resolved_tags.append({'text': label, 'color': _resolve_tag_color(val, options, colors)})
    form._resolved_tags = _resolved_tags

    ctx = dict(
        instance=instance,
        form=form,
        nav=nav,
        ro=ro,
        is_new=is_new,
        _lookup=_build_lookup(form, extra_ctx.get('_lookup') if extra_ctx else None),
        can_delete=_can_delete,
        _session_totals={},
    )
    if extra_ctx:
        for k, v in extra_ctx.items():
            if k == '_lookup' and isinstance(v, dict):
                ctx.setdefault('_lookup', {}).update(v)
            else:
                ctx[k] = v
    return render_template(template, **ctx)
