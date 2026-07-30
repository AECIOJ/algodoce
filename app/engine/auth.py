from flask import redirect, url_for, session, request as _req, current_app
from flask_login import current_user, logout_user
from app.extensions import login_manager
from app.models.user import User
import time as _time


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
        now = _time.time()
        last = session.get('_last_activity')
        timeout = current_app.config['SESSION_TIMEOUT'] * 60
        if last and (now - last) > timeout:
            logout_user()
            session.clear()
            return redirect(url_for('site.index'))
        session['_last_activity'] = now
