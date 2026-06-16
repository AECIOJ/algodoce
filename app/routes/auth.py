import os
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, session, redirect, current_app
from flask_login import login_user, logout_user, login_required
from app.extensions import db
from app.models.user import User
from app.models.setting import Setting

bp = Blueprint("auth", __name__)

FAILED_ATTEMPTS = {}
WINDOW = 15 * 60
THRESHOLD = 3
MAX_DELAY = 60

PERMUTACOES = ["AMH", "AHM", "MAH", "MHA", "HAM", "HMA"]


def _get_ip():
    return request.remote_addr or request.headers.get("X-Forwarded-For", "unknown")


def _cleanup():
    now = time.time()
    expired = [k for k, (_, t) in FAILED_ATTEMPTS.items() if now - t > WINDOW]
    for k in expired:
        del FAILED_ATTEMPTS[k]


def _impose_delay():
    _cleanup()
    ip = _get_ip()
    count, first = FAILED_ATTEMPTS.get(ip, (0, 0))
    if count >= THRESHOLD:
        delay = min(2 ** (count - THRESHOLD), MAX_DELAY)
        time.sleep(delay)
        return delay
    return 0


def _record_failure():
    ip = _get_ip()
    now = time.time()
    count, first = FAILED_ATTEMPTS.get(ip, (0, now))
    FAILED_ATTEMPTS[ip] = (count + 1, first if first else now)


def _clear_attempts():
    ip = _get_ip()
    FAILED_ATTEMPTS.pop(ip, None)


def _gerar_chave(ordem):
    if ordem not in PERMUTACOES:
        return ""
    now = datetime.now()
    valores = {"A": str(now.year), "M": f"{now.month:02d}", "H": f"{now.hour:02d}"}
    return "".join(valores[c] for c in ordem)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return redirect("/")

    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    delay = _impose_delay()

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session.permanent = True
        login_user(user, remember=True)
        _clear_attempts()
        return jsonify(success=True, redirect="/orcamentos")

    _record_failure()
    count, _ = FAILED_ATTEMPTS.get(_get_ip(), (0, 0))
    error = "Usuário ou senha inválidos"
    if delay > 0:
        error += f". Tentativa {count}, aguarde {delay}s."
    elif count == THRESHOLD + 1:
        error += ". Próximas tentativas terão atraso progressivo."
    return jsonify(success=False, error=error), 401


@bp.route("/api/login-sistema", methods=["POST"])
def login_sistema():
    data = request.get_json(silent=True) or {}
    u = data.get("username", "")
    p = data.get("password", "")
    c = data.get("chave", "")

    expected_u = Setting.get("painel_usuario") or os.getenv("ADMIN_USERNAME", "doceira")
    expected_p = Setting.get("painel_senha") or os.getenv("ADMIN_PASSWORD", "doceira")
    expected_chave_code = Setting.get("painel_chave")

    if u != expected_u or p != expected_p:
        return jsonify(success=False, error="Credenciais inválidas"), 401

    if expected_chave_code in PERMUTACOES:
        esperado = _gerar_chave(expected_chave_code)
        if c != esperado:
            return jsonify(success=False, error="Chave inválida"), 401

    user = User.query.filter_by(username=u).first()
    if not user:
        return jsonify(success=False, error="Usuário não encontrado"), 401
    session.permanent = True
    login_user(user, remember=True)
    _clear_attempts()
    return jsonify(success=True, redirect="/orcamentos")


@bp.route("/api/login-admin", methods=["POST"])
def login_admin():
    data = request.get_json(silent=True) or {}
    u = data.get("username", "")
    p = data.get("password", "")
    c = data.get("chave", "")

    expected_u = os.getenv("ADMIN_USERNAME", "admin")
    expected_p = os.getenv("ADMIN_PASSWORD", "")
    expected_chave_code = os.getenv("ADMIN_KEY", "HMA")

    if not u:
        return jsonify(success=False, error="Usuário obrigatório"), 401

    if u != expected_u:
        return jsonify(success=False, error="Credenciais inválidas"), 401

    if expected_p and p != expected_p:
        return jsonify(success=False, error="Credenciais inválidas"), 401

    if expected_chave_code not in PERMUTACOES:
        expected_chave_code = "HMA"

    esperado = _gerar_chave(expected_chave_code)
    if c != esperado:
        return jsonify(success=False, error="Chave inválida"), 401

    admin = User.query.first()
    if admin:
        login_user(admin, remember=True)
    session["seguranca_autenticado"] = True
    return jsonify(success=True, redirect="/seguranca/")


@bp.route("/api/admin-config", methods=["GET"])
def admin_config():
    return jsonify(
        tem_usuario=bool(os.getenv("ADMIN_USERNAME", "")),
        tem_senha=bool(os.getenv("ADMIN_PASSWORD", "")),
    )


@bp.route("/api/check-chave", methods=["GET"])
def check_chave():
    ordem = Setting.get("painel_chave")
    return jsonify(tem=ordem in PERMUTACOES)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    resp = redirect("/")
    for name in ["remember_token", current_app.config.get("SESSION_COOKIE_NAME", "session")]:
        resp.set_cookie(name, "", max_age=0, path="/")
    return resp
