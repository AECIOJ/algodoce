from flask import Blueprint, render_template, redirect, url_for, abort
from flask_login import current_user
from app.utils import render_pagina

bp = Blueprint("site", __name__)


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect("/orcamentos")
    return render_template("site/index.html")


@bp.route("/sobre")
def sobre():
    content = render_pagina("sobre")
    if content is None:
        abort(404)
    return render_template("site/sobre.html", content=content)


@bp.route("/contato")
def contato():
    return render_template("site/contato.html")
