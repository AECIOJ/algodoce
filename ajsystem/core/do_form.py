"""Orquestrador `do_form` — request → response para formulários.

Reescrito do zero observando `core/old/do_form.py`. Consome o spec puro
`defs.form.Form` e delega persistência/coerção a `core/form.py` e validação/
transform a `defs.validators`/`defs.transformers`.
"""
import re

from flask import flash, redirect, render_template, request, url_for

from ajsystem.core.adapter import db
from ajsystem.core.form import (
    _empty_value, _coerce, _is_readonly, _flat_fields,
    _build_nav, _resolve_delete, _when_allows,
)
from ajsystem.core.do_upload import process_image_fields as _process_image_fields
from ajsystem.defs.data import fk_target_model, resolve_max_width
from ajsystem.defs.tags import parse_tag, resolve_tag
from ajsystem.defs.validators import resolve_validator
from ajsystem.defs.transformers import apply_field_transforms
from ajsystem.core.query import group_items, order_items


def _save_single_sessions(form, instance):
    """Persiste sessões criança 1:1 (formulário único, ex. Evento de um orçamento).

    Sessão só com `fields` (sem `query`/`table`) renderiza o child único como
    formulário. Os campos são enviados com o prefixo `child_<attr>_`. Se houver
    qualquer valor editável, cria/atualiza o child vinculado (`instance.<attr>`)
    e grava a FK do pai; caso contrário deixa o child como estava.
    """
    for session in getattr(form, '_resolved_sessions', []) or []:
        if session.get('query') or session.get('table') or not session.get('model'):
            continue
        model = session.get('model')
        attr = session.get('attr') or session.get('name', '').lower()
        if attr is None:
            continue
        fields = session.get('fields') or []
        editable = [f for f in fields
                    if getattr(f, '_pos_managed', True) is False
                    or getattr(f, 'pos_form', None) not in (0, 4)]
        if not editable:
            continue
        prefix = 'child_' + attr + '_'
        has_data = any(request.form.get(prefix + f.name) not in (None, '')
                       for f in editable)
        if not has_data:
            continue
        child = getattr(instance, attr, None)
        if child is None:
            child = model()
            setattr(instance, attr, child)   # vincula via relationship (seta FK do pai)
            db.session.add(child)
        for f in fields:
            raw = request.form.get(prefix + (f.input_name or f.name))
            if raw is None:
                continue
            setattr(child, f.name, _coerce(raw, f))
        apply_field_transforms(child, editable)


def _save_session_masters(form, instance, old_vals, is_new):
    """Persiste campos-master declarados em `session.fields` do pai.

    Cobre dois casos: sessões de TABELA (ex.: `sessions.Insumos.fields=
    ['qtd_receita']` do Produto) e sessões de campos do pai (só `fields`,
    sem child — ex.: `sessions.Financeiro.fields=['total','carteira_id']`).

    Lista explícita → autoritativa: o campo é renderizado/editado acima da
    tabela child (mesmo com `pos_form: 0` na Schema). Validação igual à do
    loop principal.
    """
    fields_ok = True
    for session in getattr(form, '_resolved_sessions', []) or []:
        if session.get('query'):
            continue  # sessões query são readonly
        if not session.get('table') and session.get('model') is not None:
            continue  # sessão 1:1 child já é gravada por `_save_single_sessions`
        for f in session.get('fields') or []:
            if getattr(f, 'calc', None):
                continue
            if f.input == 'image':
                continue
            if f.input == 'multi':
                raw = request.form.getlist(f.input_name or f.name)
            else:
                raw = request.form.get(f.input_name or f.name)
            if raw is None:
                continue
            val = _coerce(raw, f)
            if f.required and _empty_value(val):
                flash(f'{f.label or f.name} é obrigatório.', 'warning')
                fields_ok = False
                continue
            old_vals[f.name] = getattr(instance, f.name, None) if not is_new else None
            setattr(instance, f.name, val)
    return fields_ok


_CROW_RE = re.compile(r'^(n-?\d+|\d+)_(.+)$')


def _save_table_sessions(form, instance):
    """Persiste sessões criança 1:N em tabela (ex. Itens do Pedido/Orçamento).

    Cada linha envia `child_<rel>_<crow>_<campo>`, onde `<crow>` é o id da
    linha existente ou `n-1`, `n-2`... (linhas novas criadas no JS; o template
    `__IDX__` chega com valores vazios e é ignorado). Linhas do banco ausentes
    no POST são excluídas. Sessão sem nenhuma chave no POST (não renderizada)
    é ignorada. Retorna False se a validação (`required`) falhar.
    """
    parent_table = getattr(getattr(form, '_model', None), '__tablename__', None)
    for session in getattr(form, '_resolved_sessions', []) or []:
        if not session.get('table') or not session.get('model'):
            continue
        if session.get('query'):
            continue
        model = session.get('model')
        rel = session.get('attr') or session.get('name', '')
        if not rel:
            continue
        prefix = 'child_' + rel + '_'
        rows = {}
        rendered = False
        for key in request.form.keys():
            if not key.startswith(prefix):
                continue
            rendered = True
            m = _CROW_RE.match(key[len(prefix):])
            if not m:
                continue
            crow, fname = m.group(1), m.group(2)
            rows.setdefault(crow, {})[fname] = key
        if not rendered:
            continue  # sessão não renderizada: não toca nos filhos
        pk_names = {c.name for c in model.__table__.primary_key.columns}
        pk_attr = next(iter(pk_names), 'id')
        dk_name = None
        if parent_table is not None:
            for col in model.__table__.columns:
                for fk in col.foreign_keys:
                    try:
                        if fk.column.table.name == parent_table:
                            dk_name = col.name
                            break
                    except Exception:
                        continue
                if dk_name:
                    break
        columns = session.get('columns') or []
        savable = [f for f in columns
                   if not getattr(f, 'calc', None)
                   and f.input != 'image'
                   and f.name not in pk_names
                   and f.name != dk_name]
        by_input = {(f.input_name or f.name): f for f in savable}
        posted_ids = set()
        posted_crows = set()
        new_children = []
        is_composite = len(pk_names) > 1
        for crow, fmap in rows.items():
            if crow.startswith('n'):
                child = model()
                if dk_name:
                    setattr(child, dk_name, instance.id)
                is_new_row = True
            elif is_composite:
                # PK composta: sem endereço confiável p/ update — preserva a
                # linha (não atualiza nem exclui); novas (n-*) inserem normal.
                try:
                    int(crow)
                except (TypeError, ValueError):
                    continue
                posted_crows.add(str(crow))
                continue
            else:
                try:
                    cid = int(crow)
                except (TypeError, ValueError):
                    continue
                try:
                    child = model.query.get(cid)
                except Exception:
                    child = None
                if child is None:
                    continue
                if dk_name and getattr(child, dk_name, None) != instance.id:
                    continue  # não pertence a este pai
                posted_ids.add(cid)
                posted_crows.add(str(crow))
                is_new_row = False
            vals = {}
            for fname, key in fmap.items():
                f = by_input.get(fname)
                if f is None:
                    continue
                if f.input == 'multi':
                    raw = request.form.getlist(key)
                else:
                    raw = request.form.get(key)
                vals[f.name] = _coerce(raw, f)
            for f in savable:
                if f.name not in vals and f.input in ('checkbox', 'boolean'):
                    vals[f.name] = False
            if is_new_row and all(_empty_value(v) for v in vals.values()):
                continue  # linha adicionada mas não preenchida
            for f in savable:
                if f.name in vals and f.required and _empty_value(vals[f.name]):
                    flash(f'{f.label or f.name} é obrigatório.', 'warning')
                    return False
            touched = False
            for f in savable:
                if f.name in vals:
                    setattr(child, f.name, vals[f.name])
                    touched = True
            if not touched:
                continue
            if is_new_row:
                db.session.add(child)
                new_children.append(child)
            apply_field_transforms(child, savable)
        if new_children:
            db.session.flush()
            for child in new_children:
                posted_ids.add(getattr(child, pk_attr, None))
        if dk_name is not None:
            existing = model.query.filter(
                getattr(model, dk_name) == instance.id).all()
        else:
            existing = list(getattr(instance, rel, []) or [])
        if is_composite:
            from ajsystem.core.utils import item_ref
            for child in existing:
                try:
                    ref = item_ref(child, existing)
                except Exception:
                    ref = None
                if ref is not None and str(ref) not in posted_crows:
                    db.session.delete(child)
        else:
            for child in existing:
                if getattr(child, pk_attr, None) not in posted_ids:
                    db.session.delete(child)
    return True


def _build_session_groups(session, instance):
    """Calcula `groups` para sessões query agrupadas (readonly).

    Sessão `query` com `groups` renderiza como tabela readonly agrupada: os
    itens do relacionamento (`attr`) são agrupados pelo campo, na ordem das
    options da Entity. Preenche `session['groups']` para o macro
    `item_table_grouped`. Totais (`totals`/`group_totals`) ficam para quando
    o contrato for alinhado."""
    if instance is None or not isinstance(session, dict):
        return
    q = session.get('query')
    if not isinstance(q, dict) or not q.get('groups'):
        return
    columns = session.get('columns') or []
    g_name = q.get('groups')
    if isinstance(g_name, list):
        g_name = g_name[0] if g_name else None
    g_field = next((f for f in columns if getattr(f, 'name', None) == g_name), None)
    items = list(getattr(instance, session.get('attr') or session.get('name', '').lower(), None) or [])
    if q.get('order'):
        items = order_items(items, q.get('order'), columns)
    groups = group_items(items, g_field, None, columns)
    if groups:
        session['groups'] = groups





def _build_lookup(form, extra_lookup=None, instance=None):
    """Popula `_lookup` (legado) para FKs — `{campo: [instâncias alvo]}`.

    Para cada campo `select` sem `options`, resolve o model alvo do FK e
    carrega as instâncias (usadas pelo template para montar os `<option>` e
    exibir o nome em vez do id). `extra_lookup` tem prioridade.
    O `when` do lookup filtra SÓ a escolha: se a instância tem valor fora do
    filtro, ele é unido às opções (exibe certo e o save preserva).
    """
    lookup = dict(extra_lookup or {})

    def fill(f, src_model, _union=True):
        if f.input != 'select' or f.options is not None:
            return
        if f.name in lookup:
            return
        tgt = fk_target_model(src_model, f.name)
        if tgt is None or getattr(tgt, '__table__', None) is None:
            return
        opts = tgt.query
        resolved = getattr(f, 'lookup', None)
        has_when = isinstance(resolved, dict) and resolved.get('when')
        if isinstance(resolved, dict) and resolved.get('query'):
            lookup[f.name] = []  # busca em modal: sem options, widget próprio
            return
        if has_when:
            from ajsystem.defs.data import apply_lookup_when
            opts = apply_lookup_when(opts, tgt, resolved['when'])
        items = list(opts.all())
        if _union and has_when and instance is not None:
            cur = getattr(instance, f.name, None)
            if cur is not None:
                vkey = resolved.get('value', 'id')
                if all(getattr(o, vkey, None) != cur for o in items):
                    try:
                        if vkey == 'id':
                            cur_obj = tgt.query.get(cur)
                        else:
                            cur_obj = tgt.query.filter(
                                getattr(tgt, vkey) == cur).first()
                    except Exception:
                        cur_obj = None
                    if cur_obj is not None:
                        items.append(cur_obj)
        lookup[f.name] = items

    for f in _flat_fields(form):
        fill(f, form._model)
    for session in form._resolved_sessions:
        child_model = session.get('model')
        for f in (session.get('columns') or []) or []:
            fill(f, child_model, _union=False)
        if child_model is None:
            # sessão de campos do pai: lookup resolvido contra o model do pai
            for f in (session.get('fields') or []):
                fill(f, form._model, _union=False)
    return lookup


def do_form(form, id=None, extra_ctx=None, instance=None, list_max_width=None):
    """GET: renderiza o form (novo/editar). POST: valida, salva e redireciona.

    `list_max_width`: largura da listagem do mesmo módulo (consumida quando
    `form.max_width` não é declarado), passada por `core.auto._form`."""
    instance = instance or (form._model.query.get(id) if id is not None else None)
    is_new = instance is None
    ro = _is_readonly(form, instance)

    from ajsystem.core.filters import fixed_filters as _fixed_filters
    _fixed = _fixed_filters(form._resolved_fields, form._model)
    if instance is not None and _fixed:
        for _mf, _v in _fixed:
            _attr = getattr(_mf, 'key', None) or getattr(_mf, 'name', None)
            if _attr and getattr(instance, _attr, None) != _v:
                flash('Registro fora do escopo da página.', 'warning')
                _back = request.referrer
                if _back and _back.split('?')[0].rstrip('/') != request.url.rstrip('/'):
                    return redirect(_back)
                return redirect(url_for(form._redirect))

    from ajsystem.defs.data import resolve_lookup
    for f in _flat_fields(form):
        resolved = resolve_lookup(f, form._model)
        if resolved is not None:
            f.lookup = resolved
    for session in getattr(form, '_resolved_sessions', []) or []:
        child_model = session.get('model')
        if child_model is not None:
            for f in (session.get('columns') or []) or []:
                resolved = resolve_lookup(f, child_model)
                if resolved is not None:
                    f.lookup = resolved
        else:
            for f in (session.get('fields') or []):
                resolved = resolve_lookup(f, form._model)
                if resolved is not None:
                    f.lookup = resolved

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
            if getattr(f, '_pos_managed', True) and f.pos_form != 1:
                continue
            if f.calc:
                continue
            if f.input == 'image':
                continue
            if f.input == 'multi':
                raw = request.form.getlist(f.input_name or f.name)
            else:
                raw = request.form.get(f.input_name or f.name)
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

        if not _save_session_masters(form, instance, old_vals, is_new):
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

        _save_single_sessions(form, instance)
        if _save_table_sessions(form, instance) is False:
            db.session.rollback()
            return redirect(url_for(form._redirect))

        db.session.flush()
        db.session.commit()

        changed = {n for n, old in old_vals.items()
                   if getattr(instance, n, None) != old}
        changed |= image_changed
        if form.post_save:
            form.post_save(instance, changed, old_vals)
        flash(form.flash_ok if is_new else form.flash_update, 'success')
        return redirect(url_for(form._redirect))

    nav = _build_nav(form._model, id, _fixed) if id is not None else None
    _delete_cfg = _resolve_delete(form.delete, label=form._label)
    _can_delete = (instance is None) or (
        _delete_cfg is not None and _when_allows(_delete_cfg['when'], instance))

    for session in getattr(form, '_resolved_sessions', []) or []:
        _build_session_groups(session, instance)

    template = form.template or 'pages/form.html'

    _resolved_tags = []
    if instance:
        for f in _flat_fields(form):
            if not getattr(f, 'tag', None) or f.pos_form != 4:
                continue
            _val = getattr(instance, f.name, None)
            if _val is None:
                continue
            r = resolve_tag(f.tag, _val, f.options)
            if r is not None:
                _resolved_tags.append({'label': f.display_label, 'text': r['text'],
                                       'color': r['color'],
                                       'link': r.get('link'), 'id': _val})
    form._resolved_tags = _resolved_tags

    ctx = dict(
        instance=instance,
        form=form,
        nav=nav,
        ro=ro,
        is_new=is_new,
        _lookup=_build_lookup(form, extra_ctx.get('_lookup') if extra_ctx else None,
                            instance),
        can_delete=_can_delete,
        _session_totals={},
        max_width=resolve_max_width(form.max_width) or list_max_width or '160ch',
    )
    if extra_ctx:
        for k, v in extra_ctx.items():
            if k == '_lookup' and isinstance(v, dict):
                ctx.setdefault('_lookup', {}).update(v)
            else:
                ctx[k] = v
    return render_template(template, **ctx)
