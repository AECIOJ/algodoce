"""Orquestrador `do_auth` — wiring do login manager + rotas de autenticação
e painel de segurança.

Agrupa a inicialização (`init_auth`: user_loader, unauthorized_handler e
timeout de sessão) e os blueprints `auth` (login/logout/keepalive/chave
diária) e `seguranca` (painel de configurações do sistema).

Contratos consumidos pelo front-end (app/static/js/{auth,login,seguranca}.js):
  POST /api/login             {username, password}        -> {redirect} | 401 {error}
  POST /api/login-sistema     {username, password, chave} -> {redirect} | 401 {error}
  POST /api/login-admin       {username, password, chave} -> {redirect} | 401 {error}
  GET  /api/admin-config      -> {tem_usuario, tem_senha}
  POST /api/check-chave       -> {tem: bool}
  GET  /api/chave-diaria      -> {tem, chave, ordem, label}
  GET  /api/diaria-opcoes     -> {opcoes: [{valor, label}]}
  POST /api/keepalive         -> {ok: true}
  GET  /logout                -> redirect /
"""
import os
import time
from datetime import datetime
from flask import (
    Blueprint, request, jsonify, session, redirect, current_app,
    render_template, flash, url_for,
)
from flask import request as _req
from flask_login import (
    current_user, login_user, logout_user, login_required,
)
from app.ajsystem.core.adapter import db, User, Setting, APP, login_manager
from app.ajsystem.core.menu import pagina_home

bp = Blueprint("auth", __name__)
bp_seguranca = Blueprint("seguranca", __name__, url_prefix="/seguranca")

FAILED_ATTEMPTS = {}
WINDOW = 15 * 60
THRESHOLD = 3
MAX_DELAY = 60

PERMUTACOES = ["AMH", "AHM", "MAH", "MHA", "HAM", "HMA"]

_ROTULOS_CHAVE = {"A": "Ano", "M": "Mês", "H": "Hora"}


def init_auth(app):
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for('site.index'))

    @app.before_request
    def check_session_timeout():
        if current_app.config.get('SESSION_TIMEOUT', 0) <= 0:
            return
        if not current_user.is_authenticated:
            return
        if _req.endpoint in ('auth.keepalive',):
            return
        now = time.time()
        last = session.get('_last_activity')
        timeout = current_app.config['SESSION_TIMEOUT'] * 60
        if last and (now - last) > timeout:
            logout_user()
            session.clear()
            return redirect(url_for('site.index'))
        session['_last_activity'] = now


def _gerar_chave(ordem=None):
    if ordem is None:
        ordem = Setting.get("painel_chave")
    if ordem not in PERMUTACOES:
        return ""
    now = datetime.now()
    valores = {"A": str(now.year), "M": f"{now.month:02d}", "H": f"{now.hour:02d}"}
    return "".join(valores[c] for c in ordem)


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


# ─── Blueprint auth ────────────────────────────────────────────────────────

@bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    delay = _impose_delay()

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session.permanent = True
        login_user(user, remember=True)
        session['_last_activity'] = time.time()
        _clear_attempts()
        return jsonify(redirect=pagina_home(APP.module('system')))

    _record_failure()
    count, _ = FAILED_ATTEMPTS.get(_get_ip(), (0, 0))
    error = "Usuário ou senha inválidos"
    if delay > 0:
        error += f". Tentativa {count}, aguarde {delay}s."
    elif count == THRESHOLD + 1:
        error += ". Próximas tentativas terão atraso progressivo."
    return jsonify(error=error), 401


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
        return jsonify(error="Credenciais inválidas"), 401

    if expected_chave_code in PERMUTACOES:
        if c != _gerar_chave(expected_chave_code):
            return jsonify(error="Chave inválida"), 401

    user = User.query.filter_by(username=u).first()
    if not user:
        return jsonify(error="Usuário não encontrado"), 401
    session.permanent = True
    login_user(user, remember=True)
    _clear_attempts()
    return jsonify(redirect=pagina_home(APP.module('system')))


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
        return jsonify(error="Usuário obrigatório"), 401
    if u != expected_u:
        return jsonify(error="Credenciais inválidas"), 401
    if expected_p and p != expected_p:
        return jsonify(error="Credenciais inválidas"), 401
    if expected_chave_code not in PERMUTACOES:
        expected_chave_code = "HMA"
    if c != _gerar_chave(expected_chave_code):
        return jsonify(error="Chave inválida"), 401

    admin = User.query.first()
    if admin:
        login_user(admin, remember=True)
    session["seguranca_autenticado"] = True
    return jsonify(redirect=pagina_home(APP.module('admin')))


@bp.route("/api/admin-config")
def admin_config():
    return jsonify(
        tem_usuario=bool(os.getenv("ADMIN_USERNAME", "")),
        tem_senha=bool(os.getenv("ADMIN_PASSWORD", "")),
    )


@bp.route("/api/check-chave", methods=["POST"])
def check_chave():
    ordem = Setting.get("painel_chave")
    return jsonify(tem=ordem in PERMUTACOES)


@bp.route("/api/chave-diaria")
def chave_diaria():
    ordem = Setting.get("painel_chave")
    if ordem not in PERMUTACOES:
        return jsonify(tem=False)
    now = datetime.now()
    valores = {"A": str(now.year), "M": f"{now.month:02d}", "H": f"{now.hour:02d}"}
    chave = "".join(valores[c] for c in ordem)
    label = "Hoje: " + " ".join(_ROTULOS_CHAVE[c] for c in ordem)
    label += " → " + " ".join(valores[c] for c in ordem)
    return jsonify(tem=True, chave=chave, ordem=ordem, label=label)


@bp.route("/api/diaria-opcoes")
def diaria_opcoes():
    return jsonify(opcoes=[
        {"valor": p, "label": " ".join(_ROTULOS_CHAVE[c] for c in p)}
        for p in PERMUTACOES
    ])


@bp.route("/api/keepalive", methods=["POST"])
@login_required
def keepalive():
    session['_last_activity'] = time.time()
    return jsonify(ok=True)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    resp = redirect("/")
    for name in [current_app.config.get("SESSION_COOKIE_NAME", "session"), "remember_token"]:
        resp.set_cookie(name, "", max_age=0, path="/")
    return resp


# ─── Blueprint seguranca ───────────────────────────────────────────────────

@bp_seguranca.before_request
@login_required
def protect():
    pass


@bp_seguranca.route("/", methods=["GET", "POST"])
def painel():
    autenticado = bool(session.get("seguranca_autenticado"))
    if not autenticado:
        if request.method == "POST":
            u = request.form.get("username", "")
            p = request.form.get("password", "")
            expected_u = Setting.get("painel_usuario") or os.getenv("ADMIN_USERNAME", "doceira")
            expected_p = Setting.get("painel_senha") or os.getenv("ADMIN_PASSWORD", "doceira")
            if u == expected_u and p == expected_p:
                session["seguranca_autenticado"] = True
                flash("Acesso autorizado.", "success")
                return redirect(url_for("seguranca.painel"))
            flash("Credenciais inválidas.", "danger")
        return render_template("sys_auth/login.html")

    settings = Setting.query.order_by(Setting.key).all()
    return render_template(
        "sys_auth/settings.html",
        settings=settings,
        permutacoes=PERMUTACOES,
        codigo_atual=Setting.get("painel_chave"),
    )


@bp_seguranca.route("/salvar", methods=["POST"])
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


@bp_seguranca.route("/sair")
def sair():
    session.pop("seguranca_autenticado", None)
    flash("Sessão encerrada.", "info")
    return redirect(url_for("seguranca.painel"))
