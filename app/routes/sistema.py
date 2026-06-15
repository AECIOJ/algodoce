from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("sistema", __name__, url_prefix="/sistema")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def dashboard():
    return render_template("sistema/dashboard.html")
