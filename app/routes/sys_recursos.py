from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.recurso import Recurso
from app.constants import TIPO_RECURSO
from app.table import Field, build_field_context, Table


RECURSOS_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='nome', label='Nome', width=20, pos=1),
    Field(name='tipo', label='Tipo', width=12, options=TIPO_RECURSO, filter_options=list(TIPO_RECURSO.values())),
    Field(name='saldo', label='Saldo Inicial', width=12, input='number', align='right', currency='brl'),
    Field(name='data', label='Balanço', width=12, input='date'),
]

RECURSOS_TABLE = Table(fields=RECURSOS_FIELDS, edit_endpoint='recursos.edit')

bp = Blueprint("recursos", __name__, url_prefix="/recursos")


@bp.route("/")
@login_required
def list():
    filtro_tipo = request.args.get("tipo", "todos")
    query = Recurso.query
    if filtro_tipo != "todos":
        query = query.filter(Recurso.tipo == int(filtro_tipo))
    recursos = query.order_by(Recurso.nome).all()
    ctx = build_field_context(RECURSOS_FIELDS)
    return render_template(
        "sys_recursos/list.html", recursos=recursos, RECURSOS_TABLE=RECURSOS_TABLE, ctx=ctx,
        TIPO_RECURSO=TIPO_RECURSO,
    )


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        tipo = int(request.form.get("tipo", 0))
        saldo = request.form.get("saldo", 0)
        data = request.form.get("data") or None
        recurso = Recurso(nome=nome, tipo=tipo, saldo=saldo, data=data)
        db.session.add(recurso)
        db.session.commit()
        flash("Recurso criado!", "success")
        return redirect(url_for("recursos.list"))
    return render_template("sys_recursos/form.html", TIPO_RECURSO=TIPO_RECURSO, recurso=None)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def edit(id):
    recurso = Recurso.query.get_or_404(id)
    if request.method == "POST":
        recurso.nome = request.form.get("nome", "").strip()
        recurso.tipo = int(request.form.get("tipo", 0))
        recurso.saldo = request.form.get("saldo", 0)
        recurso.data = request.form.get("data") or None
        db.session.commit()
        flash("Recurso atualizado!", "success")
        return redirect(url_for("recursos.list"))
    query = Recurso.query.with_entities(Recurso.id).order_by(Recurso.nome)
    ids = [r.id for r in query.all()]
    try:
        current_idx = ids.index(id)
        nav = {
            "first_id": ids[0],
            "last_id": ids[-1],
            "prev_id": ids[current_idx - 1] if current_idx > 0 else None,
            "next_id": ids[current_idx + 1] if current_idx < len(ids) - 1 else None,
        }
    except ValueError:
        nav = {"first_id": None, "last_id": None, "prev_id": None, "next_id": None}
    return render_template("sys_recursos/form.html", TIPO_RECURSO=TIPO_RECURSO, recurso=recurso, nav=nav)
