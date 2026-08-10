from datetime import date, time, datetime
from decimal import Decimal
import importlib
from flask import Blueprint, request, jsonify, session
from flask_login import login_required
from app.extensions import db
from app.utils import _title_case
from app.ajsystem.defs.entities import MODEL_MAP as AJSYSTEM_MODEL_MAP
from app.ajsystem.defs.entities import Field, build_field_config, _entidade_fields
from app.models.category import Category
from app.models.product import Product
from app.models.ingredient import Ingredient
from app.models.client import Conta
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
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


def _consulta_model(campo):
    """Resolve o model pelo nome informado (classe, slug do ajsystem ou label)."""
    if not campo:
        return None
    key = str(campo).strip()
    model = MODEL_MAP.get(key)
    if model is None:
        model = AJSYSTEM_MODEL_MAP.get(key)
    if model is None:
        model = AJSYSTEM_MODEL_MAP.get(key.lower())
    if model is None:
        for k, m in MODEL_MAP.items():
            if k.lower() == key.lower():
                model = m
                break
    return model


def _jsonable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, time, datetime)):
        return value.isoformat()
    return str(value)


@bp.route("/consulta")
@login_required
def consulta():
    """Consulta genérica de um registro e retorno de campo(s).

    `consulta(campo, valor, retorno[, por])`: pesquisa na tabela `campo` um
    registro cujo campo `por` (default: chave primária) seja `valor` e retorna
    o valor de `retorno` (aceita vários campos separados por vírgula, caso em
    que retorna um dict `valores`). Ex.: product/5/preco -> 25.00.

    Uso no cliente: `consulta('product', 5, 'preco,qtd_minima', cb)`.
    """
    campo = request.args.get("campo", "")
    valor = request.args.get("valor", "").strip()
    retorno = request.args.get("retorno", "").strip()
    por = request.args.get("por", "").strip() or None

    model_class = _consulta_model(campo)
    if model_class is None:
        return jsonify({"ok": False, "error": "Modelo inválido"}), 400

    colunas = set()
    pk = None
    try:
        colunas = set(model_class.__table__.columns.keys())
        pks = list(model_class.__table__.primary_key.columns)
        pk = pks[0].name if pks else None
    except Exception:
        pass
    por = por or pk or 'id'
    if por not in colunas:
        return jsonify({"ok": False, "error": "Campo de filtro inválido"}), 400

    campos_retorno = [c.strip() for c in retorno.split(",") if c.strip()]
    if not campos_retorno or any(c not in colunas for c in campos_retorno):
        return jsonify({"ok": False, "error": "Campo(s) de retorno inválido(s)"}), 400

    try:
        record = model_class.query.filter(getattr(model_class, por) == valor).first()
    except Exception:
        return jsonify({"ok": False, "error": "Consulta inválida"}), 400
    if record is None:
        return jsonify({"ok": False, "error": "Não encontrado"}), 404

    if len(campos_retorno) == 1:
        return jsonify({"ok": True, "valor": _jsonable(getattr(record, campos_retorno[0], None))})
    return jsonify({
        "ok": True,
        "valores": {c: _jsonable(getattr(record, c, None)) for c in campos_retorno},
    })


@bp.route("/on_set")
@login_required
def on_set():
    """Executa o `on_set` declarado na FK (intervenção do operador).

    O `on_set` é um callable anotado na FK da Entity (ex.:
    `'product_id': {'on_set': preco_on_set}`). Recebe um dict `row` com a FK
    setada, preenche os alvos via `pesquise` e devolve os valores preenchidos
    para o browser gravar nos inputs. Nunca roda no save.
    """
    ent = request.args.get("ent", "").strip()
    fk = request.args.get("fk", "").strip()
    valor = request.args.get("valor", "").strip()
    mod = request.args.get("mod", "").strip()
    if not ent or not fk or not valor or not mod:
        return jsonify({"ok": False, "error": "Parâmetros inválidos"}), 400

    try:
        module = importlib.import_module(mod)
    except Exception:
        return jsonify({"ok": False, "error": "Módulo inválido"}), 400
    entidade = getattr(module, "Entity", {}) or {}
    ent_cfg = entidade.get(ent, {})
    if not isinstance(ent_cfg, dict):
        return jsonify({"ok": False, "error": "Entity inválida"}), 400

    fld = None
    for n, c in _entidade_fields(ent_cfg).items():
        if n == fk:
            fld = Field(**build_field_config(n, dict(c))) if isinstance(c, dict) else Field(name=n)
            break
    fn = getattr(fld, "on_set", None) if fld is not None else None
    if not callable(fn):
        return jsonify({"ok": False, "error": "Campo sem on_set"}), 400

    row = {fk: valor}
    try:
        fn(row)
    except Exception:
        return jsonify({"ok": False, "error": "Falha no on_set"}), 400
    return jsonify({
        "ok": True,
        "valores": {k: _jsonable(v) for k, v in row.items() if k != fk and v is not None},
    })


@bp.route("/tunnel-url")
def tunnel_url():
    from app import get_tunnel_url

    url = get_tunnel_url(force=True)
    if not url:
        url = request.host_url.rstrip("/")
    return jsonify({"url": url})
