from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

bp = Blueprint("site", __name__)


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("sistema.dashboard"))
    return render_template("site/index.html")


@bp.route("/sobre")
def sobre():
    return render_template("site/sobre.html")


@bp.route("/contato")
def contato():
    return render_template("site/contato.html")
