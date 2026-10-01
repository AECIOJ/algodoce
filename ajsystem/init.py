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
    field_value, calc_value, fmt_mask_cmd, is_empty, is_zero_or_empty,
)
from ajsystem.defs.tags import _resolve_tag_color
# Filtros do predicado de `enabled`. `btn_empty` é a forma "zero ou vazio" (a
# que o botão usa) e `btn_filled` é a negação; os nomes antigos continuam porque
# `form_macros.html` os consome, e renomear exigiria tocar nos templates.
btn_empty = is_zero_or_empty
btn_filled = lambda v: not is_zero_or_empty(v)


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

    # 3.1 camada default do catálogo de inputs. Precisa vir ANTES de qualquer
    # construção de `Field`: `registrar_modulos` importa os models do app, e o
    # `Entity` já é expandido no import — um `type: 'CPF'` resolveria o input
    # antes de a camada do host existir. `App.inputs` é o default de processo
    # (ver `_CAMADAS_PADRAO`), e a camada da rota entra por cima na resolução.
    from ajsystem.defs import inputs as _inputs
    _inputs.definir_camadas_padrao((APP.inputs,))

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

    # Presets de input (`IN_TEXT`, `IN_TOGGLE`…) como globals Jinja, descobertos
    # por prefixo — mesma ideia dos BTN_: um tipo novo no catálogo chega nos
    # templates sem tocar em lista de importação. São o preset do FRAMEWORK, não
    # o do host: quem customiza escreve `input_props` no Field, que é a última
    # camada do merge e por isso não tem como ser enganado por um global.
    for _name in dir(_inputs):
        if not _name.startswith('IN_'):
            continue
        _value = getattr(_inputs, _name)
        if isinstance(_value, _inputs.Input):
            app.jinja_env.globals[_name] = _value

    # Contrato de DOM do container de relatório: a constante mora em
    # `defs/report.py` (o Python usa a forma de seletor, em `Button.into`), e
    # vem para cá porque `sys.html` e `print_overlay.html` precisam da forma
    # crua no `id=` e no `getElementById`. Um global só, sem literais nos
    # templates, para os três lados não poderem divergir em silêncio.
    from ajsystem.defs import report as _report
    app.jinja_env.globals['REPORT_ID'] = _report.REPORT_ID
    app.jinja_env.globals['REPORT_CONTENT'] = _report.REPORT_CONTENT

    # 4.1 catálogo de botões efetivo (framework < host). Vai para `extensions`
    # porque um endpoint HTTP não tem como receber isto por parâmetro — é o
    # único lugar do framework que precisa ler o catálogo fora do motor de forms.
    app.extensions['botoes'] = dict(APP.botoes or {})
    # 4.2 o mesmo para o catálogo de inputs, pelo mesmo motivo — a rota do
    # toggle (um endpoint HTTP) precisa resolver o input que o form renderizou.
    app.extensions['inputs'] = dict(APP.inputs or {})

    # 5. registra módulos CRUD a partir dos menus do módulo 'system'
    system = APP.module('system')
    if system:
        registrar_modulos(app, system.menus, botoes_tipos=APP.botoes,
                          inputs_tipos=APP.inputs)

    # 6. registra os módulos públicos (páginas do site) a partir do menu
    public = APP.module('public')
    if public:
        registrar_modulos(app, public.menus, modulo_ini='app.routes.site', login=False,
                          botoes_tipos=APP.botoes, inputs_tipos=APP.inputs)

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

