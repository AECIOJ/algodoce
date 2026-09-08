"""Wiring do framework: registra blueprint, templates, filtros/globals Jinja,
auth e módulos CRUD a partir do menu. Ponto único de inicialização."""
import os
import jinja2

from ajsystem import ajsystem, heroicon_filter
from ajsystem.core.adapter import APP, TEMAS, get_uploads_endpoint
from ajsystem.core.menu import modulo_atual
from ajsystem.core.do_auth import init_auth, bp as auth, bp_seguranca as seguranca
from ajsystem.core.auto import registrar_modulos
from ajsystem.core.form import _empty_value
from ajsystem.core.menu import url_do_item
from ajsystem.defs.data import fmt_mask, get_field, has_date_tokens
from ajsystem.core.list import fields_to_columns
from ajsystem.core.utils import (
    deep_attr, fmt_brl, fmt_money, fmt_id, fmt_zero, fmt_zero_int, fmt_date, fmt_datetime, fmt_percent, fmt_num, item_ref,
    field_value, calc_value,
)
from ajsystem.defs.tags import _resolve_tag_color


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

    # 3. auth (login manager, session timeout, unauthorized handler)
    init_auth(app)

    # 4. filtros/globals Jinja
    app.jinja_env.filters['deep_attr'] = deep_attr
    app.jinja_env.filters['is_empty'] = _empty_value
    app.jinja_env.filters['item_ref'] = item_ref
    app.jinja_env.filters['brl'] = fmt_brl
    app.jinja_env.filters['money'] = fmt_money
    app.jinja_env.filters['percent'] = fmt_percent
    app.jinja_env.filters['fmt_num'] = fmt_num
    app.jinja_env.filters['fmtid'] = fmt_id
    app.jinja_env.filters['fmtzero'] = fmt_zero
    app.jinja_env.filters['fmtzeroi'] = fmt_zero_int
    app.jinja_env.filters['fmtdate'] = fmt_date
    app.jinja_env.filters['fmtdatetime'] = fmt_datetime
    app.jinja_env.filters['mask'] = fmt_mask
    app.jinja_env.tests['datemask'] = has_date_tokens
    app.jinja_env.filters['fields_to_columns'] = fields_to_columns
    app.jinja_env.filters['tag_color'] = _resolve_tag_color
    app.jinja_env.filters['heroicon'] = heroicon_filter
    app.jinja_env.globals['get_field'] = get_field
    app.jinja_env.globals['menu_url'] = url_do_item
    app.jinja_env.globals['aj_uploads_endpoint'] = lambda: get_uploads_endpoint(app)
    app.jinja_env.globals['field_value'] = field_value
    app.jinja_env.globals['calc_value'] = calc_value

    # 5. registra módulos CRUD a partir dos menus do módulo 'system'
    system = APP.module('system')
    if system:
        registrar_modulos(app, system.menus)

    # 6. registra os módulos públicos (páginas do site) a partir do menu
    public = APP.module('public')
    if public:
        registrar_modulos(app, public.menus, modulo_ini='app.routes.site', login=False)

    # 7. globals/contexto padrão do framework (tema, app config, módulo atual).
    #    O host pode sobrescrever com seus próprios context_processor.
    def tema_atual():
        nome = APP.tema or next(iter(TEMAS))
        return nome if nome in TEMAS else next(iter(TEMAS))

    @app.context_processor
    def aj_framework_context():
        import json
        from ajsystem.core.menu import menus_para_json
        tema_nome = tema_atual()
        return {
            'APP': APP,
            'TEMA': TEMAS[tema_nome],
            'TEMAS': TEMAS,
            'TEMA_NOME': tema_nome,
            'modulo': modulo_atual(),
            'modulo_menus_json': json.dumps(menus_para_json()),
        }

    @app.context_processor
    def aj_framework_buttons():
        from ajsystem.defs.buttons import (
            Button, ConfirmModal, CONFIRM_EXCLUIR, CONFIRM_REMOVER_ITEM,
            BTN_SALVAR, BTN_ENVIAR, BTN_EXCLUIR, BTN_NOVO, BTN_VOLTAR,
            BTN_EDITAR, BTN_CANCELAR, BTN_CONVERTER, BTN_LISTA,
            BTN_IMPRIMIR, BTN_DETALHES, BTN_ADICIONAR, BTN_ADICIONAR_ITEM,
            BTN_FINALIZAR, BTN_ATUALIZAR, BTN_REMOVER, BTN_SIM, BTN_NAO,
            BTN_LIMPAR, BTN_APLICAR, BTN_OK, BTN_SAIR, BTN_RENOVAR,
            BTN_RELATORIO, BTN_GERAR, BTN_CONFIRMAR, BTN_EDITAR_PRODUTO,
            BTN_ENTRAR, BTN_ACESSAR,
        )
        return {
            'Button': Button, 'ConfirmModal': ConfirmModal,
            'CONFIRM_EXCLUIR': CONFIRM_EXCLUIR, 'CONFIRM_REMOVER_ITEM': CONFIRM_REMOVER_ITEM,
            'BTN_SALVAR': BTN_SALVAR, 'BTN_ENVIAR': BTN_ENVIAR, 'BTN_EXCLUIR': BTN_EXCLUIR,
            'BTN_NOVO': BTN_NOVO, 'BTN_VOLTAR': BTN_VOLTAR, 'BTN_EDITAR': BTN_EDITAR,
            'BTN_CANCELAR': BTN_CANCELAR, 'BTN_CONVERTER': BTN_CONVERTER,
            'BTN_LISTA': BTN_LISTA, 'BTN_IMPRIMIR': BTN_IMPRIMIR,
            'BTN_DETALHES': BTN_DETALHES, 'BTN_ADICIONAR': BTN_ADICIONAR,
            'BTN_ADICIONAR_ITEM': BTN_ADICIONAR_ITEM, 'BTN_FINALIZAR': BTN_FINALIZAR,
            'BTN_ATUALIZAR': BTN_ATUALIZAR, 'BTN_REMOVER': BTN_REMOVER,
            'BTN_SIM': BTN_SIM, 'BTN_NAO': BTN_NAO,
            'BTN_LIMPAR': BTN_LIMPAR, 'BTN_APLICAR': BTN_APLICAR,
            'BTN_OK': BTN_OK, 'BTN_SAIR': BTN_SAIR, 'BTN_RENOVAR': BTN_RENOVAR,
            'BTN_RELATORIO': BTN_RELATORIO, 'BTN_GERAR': BTN_GERAR,
            'BTN_CONFIRMAR': BTN_CONFIRMAR, 'BTN_EDITAR_PRODUTO': BTN_EDITAR_PRODUTO,
            'BTN_ENTRAR': BTN_ENTRAR, 'BTN_ACESSAR': BTN_ACESSAR,
        }
