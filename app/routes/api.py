from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.extensions import db
from app.utils import _title_case
from app.models.category import Category
from app.models.product import Product
from app.models.ingredient import Ingredient
from app.models.client import Conta
from app.models.quote import Quote
from app.models.recurso import Recurso
from app.models.producao import Producao
from app.models.movto import Movto
from app.models.previsao import Previsao
from app.models.compra import Compra

bp = Blueprint("api", __name__, url_prefix="/api")

MODEL_MAP = {
    "Category": Category,
    "Product": Product,
    "Ingredient": Ingredient,
    "Conta": Conta,
    "Quote": Quote,
    "Recurso": Recurso,
    "Producao": Producao,
    "Movto": Movto,
    "Previsao": Previsao,
    "Compra": Compra,
}


@bp.route("/transformar-texto", methods=["POST"])
@login_required
def transformar_texto():
    data = request.get_json(force=True)
    model_name = data.get("model")
    field_name = data.get("field")
    mode = data.get("mode")

    erro = None
    if model_name not in MODEL_MAP:
        erro = f"Modelo inválido: {model_name}"
    elif mode not in ("lower", "upper", "title"):
        erro = f"Modo inválido: {mode}"
    if erro:
        return jsonify({"success": False, "error": erro}), 400

    model_class = MODEL_MAP[model_name]
    field = getattr(model_class, field_name, None)
    if field is None:
        return jsonify({"success": False, "error": f"Campo inválido: {field_name}"}), 400

    records = model_class.query.all()
    count = 0
    for record in records:
        value = getattr(record, field_name)
        if not value or not isinstance(value, str) or not value.strip():
            continue
        if mode == "lower":
            new_value = value.lower()
        elif mode == "upper":
            new_value = value.upper()
        elif mode == "title":
            new_value = _title_case(value)
        if new_value != value:
            setattr(record, field_name, new_value)
            count += 1

    db.session.commit()
    return jsonify({"success": True, "count": count})
