import math
from datetime import datetime, date, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from sqlalchemy import func
from app.extensions import db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.ingredient import Ingredient
from app.models.product_ingredient import ProductIngredient
from app.models.producao import Producao
from app.models.producao_insumo import ProducaoInsumo
from app.models.producao_produto import ProducaoProduto

from app.constants import ORDER_STATUS, PRODUCAO_STATUS, PRODUCAO_ETAPAS
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter, apply_date_filter, MODE_NUMBER, MODE_TEXT, MODE_DATE, MODE_SELECT
from app.table import Field, build_field_context, Table


PRODUCAO_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='descricao', label='Descrição', width=50),
    Field(name='previsao_de', label='Previsão De', width=14, input='date'),
    Field(name='previsao_ate', label='Previsão Até', width=14, input='date'),
    Field(name='data_fim', label='Finalização', width=12, input='date'),
    Field(name='status', label='Status', width=14, options=PRODUCAO_STATUS, filter_options=PRODUCAO_STATUS),
]

PRODUCAO_TABLE = Table(fields=PRODUCAO_FIELDS, edit_endpoint='producao.detail')

PRODUCAO_FILTERS = {
    'id':           MODE_NUMBER,
    'descricao':    MODE_TEXT,
    'previsao_de':  MODE_DATE,
    'previsao_ate': MODE_DATE,
    'data_fim':     MODE_DATE,
    'status':       {**MODE_SELECT, 'options': PRODUCAO_STATUS},
}

bp = Blueprint("producao", __name__, url_prefix="/producao")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    active = resolve_filters(PRODUCAO_FILTERS, request.args)
    query = Producao.query
    producoes = query.order_by(Producao.previsao_de.desc().nullslast()).all()
    linhas = producoes[:]
    linhas = apply_select_filter(linhas, 'status', active.get('status'), PRODUCAO_STATUS)
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'descricao', active.get('descricao'))
    linhas = apply_date_filter(linhas, 'previsao_de', active.get('previsao_de'))
    linhas = apply_date_filter(linhas, 'previsao_ate', active.get('previsao_ate'))
    linhas = apply_date_filter(linhas, 'data_fim', active.get('data_fim'))
    producoes = linhas
    ctx = build_field_context(PRODUCAO_FIELDS)
    return render_template("sys_producao/list.html", producoes=producoes, PRODUCAO_TABLE=PRODUCAO_TABLE, ctx=ctx, active_filters=active, FILTERS=PRODUCAO_FILTERS)


def _calcular_qtd_produzir(produto, quantidade):
    qtd_min = produto.qtd_minima or 0
    if qtd_min > 0:
        return int(math.ceil(quantidade / qtd_min) * qtd_min)
    return quantidade


def _calcular_lotes(produto, quantidade):
    qtd_min = produto.qtd_minima or 0
    if qtd_min > 0:
        return int(math.ceil(quantidade / qtd_min))
    return 1


def _recalcular_insumos(producao):
    comprados = {
        pi.insumo_id: pi.comprado
        for pi in ProducaoInsumo.query.filter_by(producao_id=producao.id)
    }
    ProducaoInsumo.query.filter_by(producao_id=producao.id).delete()
    db.session.flush()
    insumos = {}
    for pp in producao.produtos:
        produto = pp.product
        lotes = _calcular_lotes(produto, pp.quantidade)
        pis = ProductIngredient.query.filter_by(product_id=pp.product_id).all()
        for pi in pis:
            key = pi.ingredient_id
            qtd = float(pi.quantidade) * lotes
            if key in insumos:
                insumos[key]["quantidade"] += qtd
            else:
                insumos[key] = {
                    "insumo_id": pi.ingredient_id,
                    "quantidade": qtd,
                    "unidade": pi.unidade,
                }
    for data in insumos.values():
        ing_id = data["insumo_id"]
        pi = ProducaoInsumo(
            producao_id=producao.id,
            insumo_id=ing_id,
            quantidade=data["quantidade"],
            unidade=data["unidade"],
            comprado=comprados.get(ing_id, 0),
        )
        db.session.add(pi)


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    if request.method == "POST":
        descricao = request.form["descricao"]
        previsao_de = request.form.get("previsao_de")
        previsao_ate = request.form.get("previsao_ate")
        if not previsao_de or not previsao_ate:
            flash("Informe o período de previsão", "warning")
            return redirect(url_for("producao.nova"))
        previsao_de = datetime.strptime(previsao_de, "%Y-%m-%d").date()
        previsao_ate = datetime.strptime(previsao_ate, "%Y-%m-%d").date()
        pedidos = Order.query.filter(
            Order.status == 0,
            Order.data_previsao_entrega.isnot(None),
            func.date(Order.data_previsao_entrega) >= previsao_de,
            func.date(Order.data_previsao_entrega) <= previsao_ate,
            Order.producao_id.is_(None),
        ).order_by(Order.data_previsao_entrega).all()
        if not pedidos:
            flash("Nenhum pedido pendente encontrado no período", "warning")
            return redirect(url_for("producao.nova"))
        producao = Producao(
            descricao=descricao,
            previsao_de=previsao_de,
            previsao_ate=previsao_ate,
        )
        db.session.add(producao)
        db.session.flush()
        for pedido in pedidos:
            for item in pedido.items:
                produto = Product.query.get(item.product_id)
                pp = ProducaoProduto(
                    producao_id=producao.id,
                    order_id=pedido.id,
                    product_id=item.product_id,
                    quantidade=_calcular_qtd_produzir(produto, item.quantidade),
                )
                db.session.add(pp)
            pedido.producao_id = producao.id
            pedido.status = 1
        _recalcular_insumos(producao)
        db.session.commit()
        flash(f"Produção {producao.id} criada com {len(pedidos)} pedido(s)!", "success")
        return redirect(url_for("producao.detail", id=producao.id))
    return render_template("sys_producao/form.html")


@bp.route("/<int:id>")
def detail(id):
    producao = Producao.query.get_or_404(id)
    pedidos_disponiveis = Order.query.filter(
        Order.status == 0,
        Order.producao_id.is_(None),
    ).order_by(Order.data_previsao_entrega).all()

    product_ids = [pp.product_id for pp in producao.produtos]
    seen = set()
    product_ids = [x for x in product_ids if not (x in seen or seen.add(x))]
    ing_etapas = db.session.query(
        ProductIngredient.product_id, ProductIngredient.etapa_id
    ).filter(
        ProductIngredient.product_id.in_(product_ids),
        ProductIngredient.etapa_id.isnot(None),
    ).distinct().all()
    product_etapas = {}
    for pid, eid in ing_etapas:
        product_etapas.setdefault(pid, set()).add(eid)

    query = Producao.query.with_entities(Producao.id).order_by(Producao.previsao_de.desc().nullslast())
    ids = [p.id for p in query.all()]
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

    return render_template(
        "sys_producao/detail.html",
        producao=producao,
        product_etapas=product_etapas,
        pedidos_disponiveis=pedidos_disponiveis,
        ORDER_STATUS=ORDER_STATUS,
        PRODUCAO_STATUS=PRODUCAO_STATUS,
        PRODUCAO_ETAPAS=PRODUCAO_ETAPAS,
        nav=nav,
    )


@bp.route("/<int:id>/add-pedido", methods=["POST"])
def add_pedido(id):
    producao = Producao.query.get_or_404(id)
    if producao.status == 9:
        flash("Produção já finalizada", "warning")
        return redirect(url_for("producao.detail", id=id))
    pedido_id = request.form.get("pedido_id", type=int)
    pedido = Order.query.get(pedido_id)
    if not pedido:
        flash("Pedido inexistente", "warning")
        return redirect(url_for("producao.detail", id=id))
    if pedido.producao_id:
        flash("Pedido já está em outra produção", "warning")
        return redirect(url_for("producao.detail", id=id))
    if pedido.status == 9:
        flash("Pedido já entregue", "warning")
        return redirect(url_for("producao.detail", id=id))
    for item in pedido.items:
        produto = Product.query.get(item.product_id)
        pp = ProducaoProduto(
            producao_id=producao.id,
            order_id=pedido.id,
            product_id=item.product_id,
            quantidade=_calcular_qtd_produzir(produto, item.quantidade),
        )
        db.session.add(pp)
    pedido.producao_id = producao.id
    pedido.status = 1
    _recalcular_insumos(producao)
    db.session.commit()
    flash("Pedido adicionado!", "success")
    return redirect(url_for("producao.detail", id=id))


@bp.route("/<int:id>/remove-pedido/<int:order_id>", methods=["POST"])
def remove_pedido(id, order_id):
    producao = Producao.query.get_or_404(id)
    if producao.status == 9:
        flash("Produção já finalizada", "warning")
        return redirect(url_for("producao.detail", id=id))
    pedido = Order.query.get_or_404(order_id)
    ProducaoProduto.query.filter_by(
        producao_id=id, order_id=order_id
    ).delete()
    pedido.producao_id = None
    pedido.status = 0
    _recalcular_insumos(producao)
    db.session.commit()
    flash("Pedido removido!", "success")
    return redirect(url_for("producao.detail", id=id))


@bp.route("/<int:id>/update-comprado", methods=["POST"])
def update_comprado(id):
    producao = Producao.query.get_or_404(id)
    data = request.get_json()
    ing_id = data.get("insumo_id")
    value = data.get("value")
    pi = ProducaoInsumo.query.filter_by(
        producao_id=id, insumo_id=ing_id
    ).first()
    if not pi:
        return jsonify({"ok": False}), 404
    pi.comprado = value
    db.session.commit()
    return jsonify({"ok": True, "comprado": float(pi.comprado), "quantidade": float(pi.quantidade)})


@bp.route("/<int:id>/update-produto", methods=["POST"])
def update_produto(id):
    producao = Producao.query.get_or_404(id)
    data = request.get_json()
    pp_id = data.get("produto_id")
    field = data.get("field")
    value = data.get("value")
    pp = ProducaoProduto.query.get(pp_id)
    if not pp or pp.producao_id != id:
        return jsonify({"ok": False}), 404
    if field and field.startswith("producao_") and hasattr(pp, field):
        setattr(pp, field, value)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/<int:id>/finalizar", methods=["POST"])
def finalizar(id):
    producao = Producao.query.get_or_404(id)
    if producao.status == 9:
        flash("Já finalizada", "warning")
        return redirect(url_for("producao.detail", id=id))
    producao.status = 9
    producao.data_fim = datetime.now(timezone.utc)
    for pp in producao.produtos:
        for i in range(3):
            setattr(pp, f"producao_{i}", pp.quantidade)
    db.session.commit()
    flash("Produção finalizada!", "success")
    return redirect(url_for("producao.detail", id=id))


@bp.route("/<int:id>/reativar", methods=["POST"])
def reativar(id):
    producao = Producao.query.get_or_404(id)
    producao.status = 0
    producao.data_fim = None
    db.session.commit()
    flash("Produção reativada!", "success")
    return redirect(url_for("producao.detail", id=id))


@bp.route("/<int:id>/atualizar", methods=["POST"])
def atualizar(id):
    producao = Producao.query.get_or_404(id)
    if producao.status == 9:
        flash("Produção já finalizada", "warning")
        return redirect(url_for("producao.detail", id=id))
    order_ids = {pp.order_id for pp in producao.produtos}
    for oid in order_ids:
        pedido = Order.query.get(oid)
        if not pedido:
            continue
        existing = {
            (pp.product_id, pp.order_id): pp
            for pp in producao.produtos if pp.order_id == oid
        }
        seen_product_ids = set()
        for item in pedido.items:
            seen_product_ids.add(item.product_id)
            produto = Product.query.get(item.product_id)
            qtd = _calcular_qtd_produzir(produto, item.quantidade)
            key = (item.product_id, oid)
            if key in existing:
                pp = existing[key]
                if pp.quantidade != qtd:
                    pp.quantidade = qtd
            else:
                pp = ProducaoProduto(
                    producao_id=id,
                    order_id=oid,
                    product_id=item.product_id,
                    quantidade=qtd,
                )
                db.session.add(pp)
        for key, pp in existing.items():
            if key[1] == oid and key[0] not in seen_product_ids:
                db.session.delete(pp)
    _recalcular_insumos(producao)
    db.session.commit()
    flash("Produção atualizada com os dados mais recentes dos pedidos!", "success")
    return redirect(url_for("producao.detail", id=id))


@bp.route("/<int:id>/editar", methods=["POST"])
def editar(id):
    producao = Producao.query.get_or_404(id)
    descricao = request.form.get("descricao", "").strip()
    if not descricao:
        flash("Preencha a descrição", "warning")
        return redirect(url_for("producao.detail", id=id))
    producao.descricao = descricao
    previsao_de = request.form.get("previsao_de")
    previsao_ate = request.form.get("previsao_ate")
    if previsao_de and previsao_ate:
        producao.previsao_de = datetime.strptime(previsao_de, "%Y-%m-%d").date()
        producao.previsao_ate = datetime.strptime(previsao_ate, "%Y-%m-%d").date()
    data_fim = request.form.get("data_fim")
    if data_fim:
        producao.data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        producao.status = 9
    else:
        producao.data_fim = None
        producao.status = 0
    db.session.commit()
    flash("Produção atualizada!", "success")
    return redirect(url_for("producao.detail", id=id))


@bp.route("/<int:id>/relatorio")
def relatorio(id):
    producao = Producao.query.get_or_404(id)
    return render_template(
        "sys_producao/relatorio.html",
        producao=producao,
        PRODUCAO_ETAPAS=PRODUCAO_ETAPAS,
    )
