import os
from flask import Blueprint, send_from_directory, current_app

bp = Blueprint("uploads", __name__)


@bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    upload_dir = os.path.join(current_app.root_path, "..", "dados", "uploads")
    return send_from_directory(upload_dir, filename)
