import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.setting import Setting

bp = Blueprint("seguranca", __name__, url_prefix="/seguranca")

PERMUTACOES = ["AMH", "AHM", "MAH", "MHA", "HAM", "HMA"]


def _creds():
    return (
        Setting.get("painel_usuario") or os.getenv("ADMIN_USERNAME", "doceira"),
        Setting.get("painel_senha") or os.getenv("ADMIN_PASSWORD", "doceira"),
    )


def _gerar_chave():
    ordem = Setting.get("painel_chave")
    if ordem not in PERMUTACOES:
        return ""
    now = datetime.now()
    valores = {"A": str(now.year), "M": f"{now.month:02d}", "H": f"{now.hour:02d}"}
    return "".join(valores[c] for c in ordem)


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/", methods=["GET", "POST"])
def painel():
    if not session.get("seguranca_autenticado"):
        if request.method == "POST":
            u = request.form.get("username", "")
            p = request.form.get("password", "")
            expected_u, expected_p = _creds()
            if u == expected_u and p == expected_p:
                session["seguranca_autenticado"] = True
                flash("Acesso autorizado.", "success")
                return redirect(url_for("seguranca.painel"))
            flash("Credenciais inválidas.", "danger")
        return render_template("seguranca/login.html")

    settings = Setting.query.order_by(Setting.key).all()
    return render_template(
        "seguranca/settings.html",
        settings=settings,
        permutacoes=PERMUTACOES,
        codigo_atual=Setting.get("painel_chave"),
        chave_hoje=_gerar_chave(),
    )


@bp.route("/salvar", methods=["POST"])
def salvar():
    if not session.get("seguranca_autenticado"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("seguranca.painel"))

    for key in Setting.KEYS:
        val = request.form.get(key, "")
        Setting.set(key, val)
    db.session.commit()
    flash("Configurações salvas com sucesso.", "success")
    return redirect(url_for("seguranca.painel"))


@bp.route("/sair")
def sair():
    session.pop("seguranca_autenticado", None)
    flash("Sessão encerrada.", "info")
    return redirect(url_for("seguranca.painel"))


@bp.route("/api/chave", methods=["POST"])
def verificar_chave():
    data = request.get_json(silent=True) or {}
    chave = data.get("chave", "")
    if chave and chave == _gerar_chave():
        return jsonify(ok=True)
    return jsonify(ok=False), 401
