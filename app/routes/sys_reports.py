from datetime import date, datetime
from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import func
from app.extensions import db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product_ingredient import ProductIngredient
from app.models.ingredient import Ingredient
from app.models.unit_conversion import UnitConversion

bp = Blueprint("reports", __name__)


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/relatorios/compras", methods=["GET", "POST"])
def compras():
    resultado = None
    data_inicio = request.args.get("data_inicio") or (
        request.form.get("data_inicio") if request.method == "POST" else ""
    )
    data_fim = request.args.get("data_fim") or (
        request.form.get("data_fim") if request.method == "POST" else ""
    )

    if data_inicio and data_fim:
        try:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        except ValueError:
            dt_inicio = None
            dt_fim = None

        if dt_inicio and dt_fim:
            resultado = (
                db.session.query(
                    Ingredient.nome,
                    Ingredient.unidade_medida,
                    func.sum(
                        ProductIngredient.quantidade * OrderItem.quantidade *
                        func.coalesce(UnitConversion.fator, 1)
                    ).label("total"),
                )
                .select_from(Order)
                .join(OrderItem, OrderItem.order_id == Order.id)
                .join(
                    ProductIngredient,
                    ProductIngredient.product_id == OrderItem.product_id,
                )
                .join(
                    Ingredient,
                    Ingredient.id == ProductIngredient.ingredient_id,
                )
                .outerjoin(
                    UnitConversion,
                    (UnitConversion.ingredient_id == ProductIngredient.ingredient_id) &
                    (UnitConversion.unidade == ProductIngredient.unidade)
                )
                .filter(Order.data_entrega.between(dt_inicio, dt_fim))
                .filter(Order.status != 3)
                .group_by(Ingredient.id, Ingredient.nome, Ingredient.unidade_medida)
                .order_by(Ingredient.nome)
                .all()
            )

    return render_template(
        "sys_reports/compras.html",
        resultado=resultado,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
