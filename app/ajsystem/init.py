"""Wiring do framework: registra blueprint, templates, filtros/globals Jinja,
auth e módulos CRUD a partir do menu. Ponto único de inicialização."""
import os
import jinja2

from app.ajsystem import ajsystem, heroicon_filter
from app.ajsystem.core.adapter import APP, get_uploads_endpoint
from app.ajsystem.core.do_auth import init_auth, bp as auth, bp_seguranca as seguranca
from app.ajsystem.core.auto import registrar_modulos
from app.ajsystem.core.menu import url_do_item
from app.ajsystem.defs.fields import fmt_mask
from app.ajsystem.defs.entities import get_field
from app.ajsystem.core.list import fields_to_columns, field_filter_options, field_grid
from app.ajsystem.core.utils import (
    deep_attr, fmt_brl, fmt_id, fmt_zero, fmt_zero_int, fmt_date, fmt_datetime, fmt_percent, item_ref,
    field_value,
)


def init_app(app):
    # 1. loader de templates do framework (anexado ao loader da app)
    aj_templates = os.path.join(app.root_path, 'ajsystem', 'templates')
    app.jinja_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader(aj_templates),
    ])

    # 2. blueprints do framework
    app.register_blueprint(ajsystem)
    app.register_blueprint(auth)
    app.register_blueprint(seguranca)

    from app.ajsystem.core.do_api import api
    app.register_blueprint(api)

    # 3. auth (login manager, session timeout, unauthorized handler)
    init_auth(app)

    # 4. filtros/globals Jinja
    app.jinja_env.filters['deep_attr'] = deep_attr
    app.jinja_env.filters['item_ref'] = item_ref
    app.jinja_env.filters['brl'] = fmt_brl
    app.jinja_env.filters['percent'] = fmt_percent
    app.jinja_env.filters['fmtid'] = fmt_id
    app.jinja_env.filters['fmtzero'] = fmt_zero
    app.jinja_env.filters['fmtzeroi'] = fmt_zero_int
    app.jinja_env.filters['fmtdate'] = fmt_date
    app.jinja_env.filters['fmtdatetime'] = fmt_datetime
    app.jinja_env.filters['mask'] = fmt_mask
    app.jinja_env.filters['fields_to_columns'] = fields_to_columns
    app.jinja_env.filters['field_filter_options'] = field_filter_options
    app.jinja_env.filters['field_grid'] = field_grid
    app.jinja_env.filters['heroicon'] = heroicon_filter
    app.jinja_env.globals['get_field'] = get_field
    app.jinja_env.globals['menu_url'] = url_do_item
    app.jinja_env.globals['aj_uploads_endpoint'] = lambda: get_uploads_endpoint(app)
    app.jinja_env.globals['field_value'] = field_value

    # 5. registra módulos CRUD a partir dos menus do módulo 'system'
    system = APP.module('system')
    if system:
        registrar_modulos(app, system.menus)
