from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from markupsafe import Markup
from flask_login import login_required
from app.extensions import db
from app.models.trf import Trf
from app.models.movto import Movto
from app.models.recurso import Recurso
from app.models.client import Conta
from app.constants import TIPO_RECURSO
from app.table import Field, build_field_context
from decimal import Decimal

bp = Blueprint("transferencias", __name__, url_prefix="/transferencias")

def _trf_status(trf):
    count = trf.movtos.count()
    if count == 0:
        return Markup('<span class="badge bg-dark">Editando</span>')
    if float(trf.total or 0) != 0:
        return Markup('<span class="badge bg-warning text-dark">Pendente</span>')
    return Markup('<span class="badge bg-success">Fechada</span>')


TRF_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='data', label='Data', width=10, input='date'),
    Field(name='historico', label='Histórico', width=30),
    Field(name='status', label='Status', width=12, function=_trf_status),
]


@bp.before_request
@login_required
def protect():
    pass


def _list():
    trfs = Trf.query.order_by(Trf.data.desc(), Trf.id.desc()).all()
    ctx = build_field_context(TRF_FIELDS)
    return render_template(
        "sys_transferencias/list.html",
        trfs=trfs, fields=TRF_FIELDS, ctx=ctx,
    )


def _load_form_data():
    recursos = Recurso.query.order_by(Recurso.nome).all()
    contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    return recursos, contas


def _new():
    recursos, contas = _load_form_data()
    return render_template(
        "sys_transferencias/form.html",
        trf=None, recursos=recursos, contas=contas,
        TIPO_RECURSO=TIPO_RECURSO,
    )


def _edit(id):
    trf = Trf.query.get(id)
    if not trf:
        flash("Registro inexistente", "warning")
        return None
    return trf


@bp.route("/")
def trf_list():
    return _list()


@bp.route("/novo", methods=["GET", "POST"])
def trf_new():
    if request.method == "POST":
        return _save(None)
    return _new()


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def trf_edit(id):
    trf = _edit(id)
    if trf is None:
        return redirect(url_for("transferencias.trf_list"))

    if request.method == "POST":
        return _save(trf)

    recursos, contas = _load_form_data()

    query = Trf.query.with_entities(Trf.id).order_by(Trf.data.desc(), Trf.id.desc())
    ids = [t.id for t in query.all()]
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

    movimentos = Movto.query.filter_by(trf_id=id).order_by(Movto.id).all()

    return render_template(
        "sys_transferencias/form.html",
        trf=trf, movimentos=movimentos,
        recursos=recursos, contas=contas, nav=nav,
        TIPO_RECURSO=TIPO_RECURSO,
    )


def _save(trf):
    data = request.form.get("data")
    historico = request.form.get("historico") or None

    tipos = request.form.getlist("trf_tipo[]")
    recursos_ids = request.form.getlist("trf_recurso_id[]")
    contas_ids = request.form.getlist("trf_conta_id[]")
    documentos = request.form.getlist("trf_documento[]")
    valores = request.form.getlist("trf_valor[]")
    historicos = request.form.getlist("trf_historico[]")
    remover = request.form.getlist("trf_remover[]")

    if not data:
        flash("Preencha a data", "danger")
        return redirect(url_for("transferencias.trf_new") if trf is None else url_for("transferencias.trf_edit", id=trf.id))

    movtos_existentes = {}
    if trf and trf.id:
        for m in Movto.query.filter_by(trf_id=trf.id).all():
            movtos_existentes[m.id] = m

    ids_recebidos = request.form.getlist("trf_movto_id[]")

    movtos_salvar = []
    for i in range(len(tipos)):
        if i < len(remover) and remover[i] == "1":
            continue
        tipo = tipos[i] if i < len(tipos) else None
        recurso_id = recursos_ids[i] if i < len(recursos_ids) else None
        conta_id = contas_ids[i] if i < len(contas_ids) else None
        documento = documentos[i] if i < len(documentos) else None
        valor = valores[i] if i < len(valores) else None
        historico_mov = historicos[i] if i < len(historicos) else None
        movto_id = ids_recebidos[i] if i < len(ids_recebidos) else None

        if not tipo or not recurso_id or not valor:
            continue

        valor_float = float(valor)
        if valor_float <= 0:
            continue

        movtos_salvar.append({
            "id": movto_id,
            "tipo": tipo,
            "recurso_id": int(recurso_id),
            "conta_id": int(conta_id) if conta_id else None,
            "documento": documento or None,
            "valor": valor_float,
            "historico": historico_mov or None,
        })

    if not movtos_salvar:
        flash("Adicione pelo menos uma linha de movimentação", "danger")
        return redirect(url_for("transferencias.trf_new") if trf is None else url_for("transferencias.trf_edit", id=trf.id))

    total = sum(
        m["valor"] if m["tipo"] == "E" else -m["valor"]
        for m in movtos_salvar
    )

    if abs(total) > 0.005:
        flash(f"Transferência não fecha em zero (total: {total:+,.2f}). Ajuste os valores.", "danger")
        return redirect(url_for("transferencias.trf_new") if trf is None else url_for("transferencias.trf_edit", id=trf.id))

    if trf is None:
        trf = Trf(data=data, historico=historico, total=0)
        db.session.add(trf)
        db.session.flush()
    else:
        trf.data = data
        trf.historico = historico

    ids_manter = set()
    for m in movtos_salvar:
        movto_id = m["id"]
        sinal = 1 if m["tipo"] == "E" else -1
        valor_final = m["valor"] * sinal

        if movto_id and movto_id.isdigit() and int(movto_id) in movtos_existentes:
            movto = movtos_existentes[int(movto_id)]
            movto.data = data
            movto.recurso_id = m["recurso_id"]
            movto.tipo = m["tipo"]
            movto.conta_id = m["conta_id"]
            movto.documento = m["documento"]
            movto.valor = m["valor"]
            movto.variacao = 0
            movto.sincronizar = True
            movto.historico = m["historico"]
            movto.trf_id = trf.id
            ids_manter.add(int(movto_id))
        else:
            movto = Movto(
                data=data,
                recurso_id=m["recurso_id"],
                tipo=m["tipo"],
                conta_id=m["conta_id"],
                documento=m["documento"],
                valor=m["valor"],
                variacao=0,
                sincronizar=True,
                historico=m["historico"],
                trf_id=trf.id,
            )
            db.session.add(movto)

    for movto_id, movto in movtos_existentes.items():
        if movto_id not in ids_manter:
            movto.trf_id = None
            db.session.delete(movto)

    trf.total = Decimal(str(total))
    db.session.commit()
    flash("Transferência salva!", "success")
    return redirect(url_for("transferencias.trf_edit", id=trf.id))


@bp.route("/<int:id>/excluir", methods=["POST"])
def trf_excluir(id):
    trf = Trf.query.get(id)
    if not trf:
        flash("Registro inexistente", "warning")
        return redirect(url_for("transferencias.trf_list"))

    Movto.query.filter_by(trf_id=trf.id).delete()
    db.session.delete(trf)
    db.session.commit()
    flash("Transferência excluída!", "success")
    return redirect(url_for("transferencias.trf_list"))
