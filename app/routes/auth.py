import os
import time
from flask import Blueprint, request, jsonify, session, redirect, current_app
from flask_login import login_user, logout_user, login_required
from app.extensions import db
from app.models.user import User

bp = Blueprint("auth", __name__)

FAILED_ATTEMPTS = {}
WINDOW = 15 * 60
THRESHOLD = 3
MAX_DELAY = 60


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


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    delay = _impose_delay()

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user, remember=True)
        _clear_attempts()
        return jsonify(success=True, redirect="/sistema/")

    _record_failure()
    count, _ = FAILED_ATTEMPTS.get(_get_ip(), (0, 0))
    error = "Usuário ou senha inválidos"
    if delay > 0:
        error += f". Tentativa {count}, aguarde {delay}s."
    elif count == THRESHOLD + 1:
        error += ". Próximas tentativas terão atraso progressivo."
    return jsonify(success=False, error=error), 401


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    resp = redirect("/")
    for name in ["remember_token", current_app.config.get("SESSION_COOKIE_NAME", "session")]:
        resp.set_cookie(name, "", max_age=0, path="/")
    return resp
