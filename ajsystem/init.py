"""Wiring do framework: registra blueprint, templates, filtros/globals Jinja,
auth e módulos CRUD a partir do menu. Ponto único de inicialização."""
import os
import jinja2

from ajsystem import ajsystem, heroicon_filter
from ajsystem import locales
from ajsystem.core.adapter import APP, TEMAS, get_uploads_endpoint
from ajsystem.core.menu import modulo_atual
from ajsystem.core.do_auth import init_auth, bp as auth, bp_seguranca as seguranca
from ajsystem.core.auto import registrar_modulos
from ajsystem.core.menu import url_do_item
from ajsystem.defs.buttons import Button, ConfirmModal
from ajsystem.defs.data import fmt_mask, get_field, has_date_tokens, internal_scripts
from ajsystem.core.list import fields_to_columns
from ajsystem.core.utils import (
    deep_attr, fmt_brl, fmt_money, fmt_id, fmt_zero, fmt_zero_int, fmt_date, fmt_datetime, fmt_percent, fmt_num, item_ref,
    field_value, calc_value, fmt_mask_cmd, is_empty,
)
from ajsystem.defs.tags import _resolve_tag_color
from ajsystem.defs.buttons import _empty as btn_empty, _filled as btn_filled


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
    app.jinja_env.filters['is_empty'] = is_empty
    # Predicados de `Button.enabled` (numéricos, espelham itEnabledEval).
    app.jinja_env.filters['btn_filled'] = btn_filled
    app.jinja_env.filters['btn_empty'] = btn_empty
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
    app.jinja_env.filters['mask_cmd'] = fmt_mask_cmd
    app.jinja_env.tests['datemask'] = has_date_tokens
    # Um único global `i18n` (o catálogo do locale ativo), em vez de ~100 nomes
    # soltos: não polui o namespace do template nem sombreia variável de
    # contexto. Acesso nos templates: `{{ i18n.SAVE }}`.
    app.jinja_env.globals.update(locales.para_jinja())
    def _is_field_body(f):
        if not getattr(f, '_pos_managed', True):
            return True
        if getattr(f, '_pos_form_when', None) is not None:
            # visibilidade condicional via `when` (ex.: POS_0_NOT_EMPTY);
            # o `when` decide (is_visible_by_pos), independente do pos_form da expansão
            return True
        return (getattr(f, 'pos_form', 1) or 0) not in (3, 5) and bool(getattr(f, 'pos_form', 1))
    _jinja_field_body = _is_field_body
    _jinja_field_row = (lambda f: bool(getattr(f, 'pos_form', 1))
                        if getattr(f, '_pos_managed', True) else True)
    app.jinja_env.tests['field_body'] = _jinja_field_body
    app.jinja_env.tests['field_row'] = _jinja_field_row
    app.jinja_env.filters['fields_to_columns'] = fields_to_columns
    app.jinja_env.filters['tag_color'] = _resolve_tag_color
    app.jinja_env.filters['heroicon'] = heroicon_filter
    app.jinja_env.globals['get_field'] = get_field
    app.jinja_env.globals['menu_url'] = url_do_item
    app.jinja_env.globals['aj_uploads_endpoint'] = lambda: get_uploads_endpoint(app)
    app.jinja_env.globals['field_value'] = field_value
    app.jinja_env.globals['calc_value'] = calc_value
    # Manifesto de scripts internos do framework (ver defs/data.INTERNAL_JS):
    # sai do template, que só itera o resultado.
    app.jinja_env.globals['internal_scripts'] = internal_scripts

    # Presets de botão como globals Jinja, descobertos por prefixo — assim um
    # preset novo em defs/buttons.py chega nos templates sem tocar em lista de
    # importação. As factories BTN_PRINT/BTN_SEND ficam de fora de propósito:
    # precisam do dict do relatório, então são chamadas em Python, não em Jinja.
    from ajsystem.defs import buttons as _buttons
    for _name in dir(_buttons):
        if not _name.startswith(('BTN_', 'CONFIRM_')):
            continue
        _value = getattr(_buttons, _name)
        if isinstance(_value, (Button, ConfirmModal)):
            app.jinja_env.globals[_name] = _value

    # 4.1 catálogo de botões efetivo (framework < host). Vai para `extensions`
    # porque um endpoint HTTP não tem como receber isto por parâmetro — é o
    # único lugar do framework que precisa ler o catálogo fora do motor de forms.
    app.extensions['botoes'] = dict(APP.botoes or {})

    # 5. registra módulos CRUD a partir dos menus do módulo 'system'
    system = APP.module('system')
    if system:
        registrar_modulos(app, system.menus, botoes_tipos=APP.botoes)

    # 6. registra os módulos públicos (páginas do site) a partir do menu
    public = APP.module('public')
    if public:
        registrar_modulos(app, public.menus, modulo_ini='app.routes.site', login=False,
                          botoes_tipos=APP.botoes)

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

