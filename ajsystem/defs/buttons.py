from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any, Callable, Dict, Optional, Union
import json
import re

from flask import url_for

from ajsystem import locales as i18n

# Tolerância numérica de `enabled`, espelhada em `itEnabledEval` (sys.html).
# "0,00" e Decimal('0.00') contam como vazio; 0.01 conta como preenchido.
NUM_EPS = 0.005

# Container exclusivo dos relatórios impressos, alternado com a página pelo
# script do fragmento; `closeReport` restaura sem recarregar. Declarado em
# `pages/sys.html` e usado como destino padrão de `Button.into`.
REPORT_ID = 'report-content'
REPORT_CONTENT = f'#{REPORT_ID}'

# Nomes de função JS globais aceitos em `action` (sem argumentos, sem statement).
_ACTION_RE = re.compile(r'^[A-Za-z_$][\w$]*$')

# Posições de botão dentro de uma sessão, por formato da sessão.
POS_FIELDS = ('fields_left', 'fields_right')
POS_TABLE = ('table_before', 'table_after')
POS_TABLE_NAVS = ('nav_left', 'nav_center', 'nav_right', 'nav_none',
                  'footer_left', 'footer_center', 'footer_right', 'footer_none')


def btn_style(color: str, outline: bool, size: str = 'sm') -> str:
    base = f'btn-{color} btn-{size}'
    return f'{base} btn-outline' if outline else base


def _get(obj, path, default=None):
    """Acesso a atributo por caminho pontilhado, tolerante a `None`/ausência."""
    cur = obj
    for part in str(path).split('.'):
        if cur is None:
            return default
        cur = getattr(cur, part, None)
    return default if cur is None else cur


def _as_num(v):
    """Valor numérico de `v`, ou None se não for número.

    Espelha o `parseNum` de `formats.js` (aceita '1.234,56' e '1.5'), para que
    Python e JS juliquem '0,00' do mesmo jeito. `bool` conta como 0/1.
    """
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float, Decimal)):
        return float(v)
    if isinstance(v, str):
        s = re.sub(r'[^0-9\-+,.]', '', v)
        if not s or s in ('-', '.', ','):
            return None
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _filled(v):
    """Preenchido: número ≠ 0 (|v| > NUM_EPS), string não-vazia, objeto truthy."""
    if v is None:
        return False
    n = _as_num(v)
    if n is not None:
        return abs(n) > NUM_EPS
    if isinstance(v, str):
        return v.strip() != ''
    return bool(v)


def _empty(v):
    """Vazio: None, número 0 (|v| <= NUM_EPS), string vazia, objeto falsy."""
    if v is None:
        return True
    n = _as_num(v)
    if n is not None:
        return abs(n) <= NUM_EPS
    if isinstance(v, str):
        return v.strip() == ''
    return not bool(v)


@dataclass
class Button:
    """Botão de form/sessão/listagem.

    `visible` decide a renderização (servidor, uma vez). `enabled` decide o
    `disabled`, reavaliado no cliente a cada `input`/`change` a partir dos campos
    do próprio form — a mesma regra vale em Python (`enabled_ok`) e no JS
    (`itEnabledEval`), inclusive para números em pt-BR.

    O destino do clique é exatamente um entre:
      - `action`: nome de função JS global → `onclick="fn(this)"`;
      - `url`: nome de endpoint (str) → `url_for(...)`, ou callable que devolve URL;
      - `render`: callable que devolve HTML, injetado em `into`.
    """
    # ── apresentação ──
    label: str
    icon: Optional[str] = None
    color: str = 'secondary'
    outline: bool = True
    size: str = 'sm'
    cls: str = ''
    # `label_off`/`icon_off` não são renderizados por nenhum template ainda —
    # declarados para o toggle `on_off` completo. Se for conectá-los, declarar
    # com constante de `ajsystem.locales`, como os outros rótulos.
    label_off: Optional[str] = None
    icon_off: Optional[str] = None

    # ── visibilidade (servidor, 1× no render) ──
    visible: Union[bool, Callable, tuple, dict] = True

    # ── habilitação (cliente, a cada input/change) ──
    enabled: Union[bool, list, dict] = True
    enabled_fields: list = field(default_factory=list)
    enabled_mode: str = 'all_filled'

    # ── destino: exatamente UM entre action / url / render ──
    action: str = ''
    url: Union[str, Callable[[Any], str]] = ''
    render: Optional[Callable[[Any], str]] = None
    into: str = ''          # vazio = '#report-content' (ver `target_into`)
    url_params: Union[dict, Callable, None] = None
    method: str = 'GET'
    confirm_msg: Optional[str] = None
    carry: Optional[dict] = None
    serialize: bool = False

    # ── posicionamento ──
    position: str = 'nav_right'
    on_off: bool = False
    field: Optional[str] = None

    def btn_cls(self) -> str:
        return self.cls or btn_style(self.color, self.outline, self.size)

    def text(self) -> str:
        """Rótulo do botão. `label` JÁ é o texto do locale ativo (veja
        `ajsystem/locales/__init__.py`), então aqui não há o que traduzir.

        O método sobrevive como pass-through porque `label` é o contrato: um app
        pode escrever o texto dele direto (`label='Plular'`), e `text()` continua
        sendo a leitura correta sem que o template precise saber a diferença.
        """
        return self.label

    def confirm_text(self) -> str:
        """Texto da confirmação (vazio se o botão não confirma)."""
        return self.confirm_msg or ''

    def visible_ok(self, instance) -> bool:
        """Visibilidade. `True`/`False` literal, callable, ou declarativa
        `('attr', valor)` / `{'attr': valor}` (caminho pontilhado)."""
        v = self.visible
        if callable(v):
            return bool(v(instance))
        if isinstance(v, dict):
            for path, expected in v.items():
                if _get(instance, path) != expected:
                    return False
            return True
        if isinstance(v, (tuple, list)):
            if len(v) != 2:
                raise ValueError(
                    f"Botão '{self.label}': `visible` declarativo exige "
                    f"(attr, valor) — veio {v!r}."
                )
            return _get(instance, v[0]) == v[1]
        return bool(v)

    def enabled_spec(self):
        """`(fields, mode)` normalizado a partir de `enabled`.

        `resolve_buttons` pré-normaliza em `enabled_fields`/`enabled_mode`;
        a normalização também acontece aqui para que um `Button(...)`
        construído direto (constantes `BTN_*`) funcione igual.
        """
        if self.enabled_fields:
            return self.enabled_fields, self.enabled_mode
        spec = self.enabled
        if isinstance(spec, (list, tuple)):
            return [str(n) for n in spec], 'all_filled'
        if isinstance(spec, dict):
            mode = spec.get('mode', 'all_filled')
            names = spec.get('fields') or []
            if isinstance(names, str):
                names = [names]
            return [str(n) for n in names], mode
        return [], 'all_filled'

    def enabled_ok(self, instance) -> bool:
        """Habilitação inicial (servidor). Regra idêntica à do `itEnabledEval`."""
        if self.enabled is False:
            return False
        names, mode = self.enabled_spec()
        if not names:
            return True
        vals = [_get(instance, n) for n in names]
        if mode == 'all_zero':
            return all(_empty(v) for v in vals)
        return all(_filled(v) for v in vals)

    def url_ready(self, instance) -> bool:
        """False esconde o botão: `url` por endpoint sem registro para o `id`.

        `url` str é nome de endpoint e a chave de URL que ele recebe é o `id`
        (veja `target_url`/`url_params`), então sem instância salva o botão não
        tem para onde apontar — é o caso do `on_off` no form de criação. Já
        `url` callable e `render` não dependem do `id`.
        """
        if not self.url or callable(self.url) or self.render is not None:
            return True
        return _get(instance, 'id') is not None

    def target_url(self, instance=None) -> str:
        """URL de destino: callable, ou `url_for` do endpoint com `url_params`."""
        if callable(self.url):
            return self.url(instance)
        if not self.url:
            return ''
        if self.url_params is None:
            params = {'id': _get(instance, 'id')} if instance is not None else {}
        elif callable(self.url_params):
            params = dict(self.url_params(instance) or {})
        else:
            params = {'id': _get(instance, 'id')} if instance is not None else {}
            params.update(self.url_params)
        return url_for(self.url, **params)

    def target_html(self, instance=None) -> str:
        """HTML producedo por `render` (vazio se o botão não usa `render`)."""
        return self.render(instance) if self.render else ''

    def target_into(self) -> str:
        """Seletor de destino do HTML de `render`."""
        return self.into or REPORT_CONTENT


@dataclass
class ConfirmModal:
    """Diálogo de confirmação. `title`/`message` são o texto do locale ativo; os
    `*_text()` são pass-through, pelo mesmo motivo de `Button.text()`."""
    title: str
    message: str
    confirm_label: str = i18n.CONFIRM
    confirm_color: str = 'danger'
    cancel_label: str = i18n.CANCEL
    icon: Optional[str] = 'trash'

    def text(self) -> str:
        return self.title

    def message_text(self) -> str:
        return self.message

    def confirm_button_text(self) -> str:
        return self.confirm_label

    def cancel_button_text(self) -> str:
        return self.cancel_label


CONFIRM_DELETE = ConfirmModal(
    title=i18n.CM_DELETE_TITLE,
    message=i18n.CM_DELETE_MSG,
)
CONFIRM_REMOVE_ITEM = ConfirmModal(
    title=i18n.CM_REMOVE_TITLE,
    message=i18n.CM_REMOVE_MSG,
    confirm_label=i18n.REMOVE,
)


# ── Presets de aparência ────────────────────────────────────────────────────
# Só aparência: `label` vem de `ajsystem.locales` (já no idioma ativo) e
# `color`/`outline`/`size` alimentam `btn_cls()`. Nenhum preset fixa `cls` — se
# fixasse, `cls` sombrearia
# `btn_style()` e trocar só a `color` não mudaria nada no render.
#
# Os dois botões de relatório (`BTN_PRINT`/`BTN_SEND`) não são presets: são
# factories, porque precisam do dict de relatório. Ver mais abaixo.
BTN_SAVE = Button(label=i18n.SAVE, icon='check', color='success', outline=False)
BTN_DELETE = Button(label=i18n.DELETE, icon='trash', color='danger', outline=False,
                    confirm_msg=i18n.CONFIRM_DELETE)
BTN_NEW = Button(label=i18n.NEW, color='success', outline=False)
BTN_BACK = Button(label=i18n.BACK, color='secondary', outline=True)
BTN_EDIT = Button(label=i18n.EDIT, icon='pencil-square', color='primary', outline=True)
BTN_CANCEL = Button(label=i18n.CANCEL, color='secondary', outline=True)
BTN_CONVERT = Button(label=i18n.CONVERT, icon='arrow-path', color='success', outline=False)
BTN_LIST = Button(label=i18n.LIST, icon='clipboard-document-list', color='secondary', outline=True)
BTN_DETAILS = Button(label=i18n.DETAILS, icon='eye', color='info', outline=True)
BTN_ADD = Button(label=i18n.ADD, color='success', outline=True)
BTN_ADD_ITEM = Button(label=i18n.ADD_ITEM, color='success', outline=True)
BTN_FINISH = Button(label=i18n.FINISH, color='success', outline=False)
BTN_REFRESH = Button(label=i18n.REFRESH, icon='arrow-path', color='warning', outline=True)
BTN_REMOVE = Button(label=i18n.REMOVE, icon='minus', color='danger', outline=True,
                    confirm_msg=i18n.REMOVE_ITEM)
BTN_YES = Button(label=i18n.YES, color='primary', outline=False)
BTN_NO = Button(label=i18n.NO, color='secondary', outline=True)
BTN_CLEAR = Button(label=i18n.CLEAR, color='danger', outline=True)
BTN_APPLY = Button(label=i18n.APPLY, color='primary', outline=False)
BTN_OK = Button(label=i18n.OK, color='danger', outline=False)
BTN_EXIT = Button(label=i18n.EXIT, color='danger', outline=True, confirm_msg=i18n.DISCARD_CHANGES)
BTN_RENEW = Button(label=i18n.RENEW, color='info', outline=False)
BTN_REPORT = Button(label=i18n.REPORT, icon='document-text', color='info', outline=True)
BTN_GENERATE = Button(label=i18n.GENERATE, color='success', outline=False)
BTN_CONFIRM = Button(label=i18n.CONFIRM, color='success', outline=False)
BTN_EDIT_PRODUCT = Button(label=i18n.EDIT_PRODUCT, icon='pencil-square', color='primary',
                          outline=True)
BTN_LOGIN = Button(label=i18n.LOGIN, color='danger', outline=False)
BTN_ACCESS = Button(label=i18n.ACCESS, color='danger', outline=False)


# ── Botões de relatório (factories: precisam do dict do relatório) ─────────
def _has_items(instance) -> bool:
    """Regra padrão de `BTN_PRINT`/`BTN_SEND`: documento sem itens não imprime.

    `getattr` (e não `.items` direto) para o botão apenas esconder quando a
    entidade não tem esse relationship, em vez de estourar `AttributeError` no
    clique.
    """
    return instance is not None and bool(getattr(instance, 'items', None))


def _render_relatorio(report, guard):
    from ajsystem.core.do_report import print_report

    def render(instance):
        if not guard(instance):
            return ''            # botão não aparece (o `render` pode devolver '')
        return print_report(report, instance)
    return render


def _render_relatorio_filtro(report, field):
    from ajsystem.core.do_report import print_report, filter_select

    def render(_instance=None):
        return print_report(report, filter_select(field))
    return render


def BTN_PRINT(report, *, filter_field='', guard=None, **overrides) -> Button:
    """Botão que imprime um relatório declarativo, no overlay padrão.

    Sem `filter_field`, imprime `report` para a instância (shape documento); com
    `filter_field='tipo'`, imprime o relatório da seleção de filtro corrente
    (shape listagem) e o `guard` não se aplica.

    No spec:
        'buttons': [BTN_PRINT(PEDIDO)]
        'buttons': [BTN_PRINT(PLANO, filter_field='tipo', label='Plano')]

    `print_report` entra por import tardio dentro da closure para este módulo não
    depender de `core/` — é o que mantém `defs/buttons.py` importável isolado.
    """
    render = (_render_relatorio_filtro(report, filter_field) if filter_field
              else _render_relatorio(report, guard=guard or _has_items))
    opts = {'render': render, 'into': REPORT_CONTENT}
    opts.update(overrides)
    return replace(Button(label=i18n.PRINT, icon='printer', color='info',
                          outline=True), **opts)


def BTN_SEND(report, *, filter_field='', guard=None, **overrides) -> Button:
    """`BTN_PRINT` com o visual de envio (papagaio/verde). Muda ícone e cor; o
    `replace` recria `cls` a partir da nova `color` via `btn_style()`.

    No spec:
        'buttons': [BTN_SEND(PEDIDO)]
        'buttons': [BTN_SEND(COMPRA), BTN_SEND(ORCAMENTO, guard=lambda c: c.finalizado)]
    """
    opts = {'label': i18n.SEND, 'icon': 'paper-airplane', 'color': 'success'}
    opts.update(overrides)
    return replace(BTN_PRINT(report, filter_field=filter_field, guard=guard), **opts)


# ── Registro nomeado de ações (Form.buttons / List) ──
# Resolução em ajsystem.core.form: um nome resolve para o default abaixo.
# Endpoint e campo booleano são derivados por convenção
# (endpoint = '<blueprint>.toggle', campo default 'ativo').
ACTIONS = {
    'on_off': Button(
        label=i18n.ACTIVATE, icon='check',
        label_off=i18n.DEACTIVATE, icon_off='xmark',
        color='success', outline=True, position='nav_right', on_off=True,
    ),
}


def _err(where, label, msg):
    prefix = f"{where}: botão '{label}'" if where else f"Botão '{label}'"
    return ValueError(f'{prefix} — {msg}')


def _check_destination(btn, where):
    """Exatamente um destino, e props de navegação que só fazem sentido com
    `url`. Sem isso, `action`+`endpoint` juntos venciam em ordem invertida
    conforme o renderizador, sem aviso."""
    label = btn.label
    if not (btn.action or btn.url or btn.render) and not btn.on_off:
        raise _err(where, label,
                   'sem destino — declare `action`, `url` ou `render` (o toggle '
                   '`on_off` é a única exceção, com url derivada).')
    if sum(bool(x) for x in (btn.action, btn.url, btn.render)) > 1:
        raise _err(where, label,
                   '`action`, `url` e `render` são mutuamente exclusivos '
                   f'(recebeu {", ".join(k for k, v in (("action", btn.action), ("url", btn.url), ("render", btn.render)) if v)}).')
    if btn.action and not _ACTION_RE.match(btn.action):
        raise _err(where, label,
                   f'`action` deve ser o NOME de uma função JS global, sem '
                   f'argumentos nem ";" — veio {btn.action!r}.')
    if btn.url_params is not None and not btn.url:
        raise _err(where, label, '`url_params` só existe com `url`.')
    if btn.url and callable(btn.url) and btn.url_params is not None:
        raise _err(where, label,
                   '`url` callable já devolve a URL pronta — `url_params` é '
                   'para `url` str (endpoint).')
    if btn.url and isinstance(btn.url, str) and btn.url.startswith('/'):
        raise _err(where, label,
                   f'`url` str é NOME de endpoint, não caminho — veio '
                   f'{btn.url!r}. Para uma URL calculada use `url` como callable.')
    for key in ('confirm_msg', 'carry', 'serialize'):
        if getattr(btn, key) and not btn.url:
            raise _err(where, label, f'`{key}` só existe com `url`.')
    if btn.method != 'GET' and not btn.url:
        raise _err(where, label, f"`method='{btn.method}'` só existe com `url`.")
    if btn.into and not btn.render:
        raise _err(where, label, '`into` só existe com `render`.')


def _check_enabled(btn, where, valid_fields):
    """Normaliza `enabled` para `enabled_fields`/`enabled_mode` e valida nomes."""
    spec = btn.enabled
    if spec is None:
        btn.enabled = True
        spec = True
    if isinstance(spec, bool):
        btn.enabled_fields, btn.enabled_mode = [], 'all_filled'
        return
    mode = 'all_filled'
    if isinstance(spec, (list, tuple)):
        names = list(spec)
    elif isinstance(spec, dict):
        mode = spec.get('mode', 'all_filled')
        if mode not in ('all_filled', 'all_zero'):
            raise _err(where, btn.label,
                       f"`mode` deve ser 'all_filled' ou 'all_zero' — veio {mode!r}.")
        names = spec.get('fields') or []
        if isinstance(names, str):
            names = [names]
    else:
        raise _err(where, btn.label,
                   f'`enabled` deve ser bool, lista de campos ou '
                   f'{{"fields": [...], "mode": ...}} — veio {type(spec).__name__}.')
    btn.enabled_fields = [str(n) for n in names]
    btn.enabled_mode = mode
    if not btn.enabled_fields:
        btn.enabled = True
        return
    if valid_fields is not None:
        unknown = [n for n in btn.enabled_fields if n not in valid_fields]
        if unknown:
            raise _err(where, btn.label,
                       f'`enabled` cita campo(s) inexistente(s) no form: '
                       f'{", ".join(unknown)}.')


def _check_position(btn, where, has_fields, has_table):
    """`fields_*` exige fields na sessão; `nav_*`/`footer_*` exigem table/query."""
    pos = btn.position
    if pos in POS_FIELDS:
        if not has_fields:
            raise _err(where, btn.label,
                       f"position '{pos}' exige uma sessão com `fields`.")
    elif pos.startswith('nav_') or pos.startswith('footer_'):
        if not has_table:
            raise _err(where, btn.label,
                       f"position '{pos}' exige uma sessão com `table`/`query`; "
                       f"em sessão só de fields use fields_left/fields_right.")


def _check_list(btn, where):
    """Listagem não tem `instance` nem form: só visibilidade literal."""
    if callable(btn.visible) or isinstance(btn.visible, (tuple, list, dict)):
        raise _err(where, btn.label,
                   'em listagem `visible` deve ser bool — listagem não tem '
                   'instância para avaliar.')
    if btn.enabled is not True:
        raise _err(where, btn.label,
                   '`enabled` não existe em listagem (não há form para reavaliar).')
    if btn.url and not callable(btn.url) and not callable(btn.url_params):
        raise _err(where, btn.label,
                   'em listagem `url` precisa ser callable (ou ter `url_params` '
                   'callable): o endpoint receberia o `id`, que a listagem não tem.')


def resolve_buttons(specs, bp_name=None, *, where=None, valid_fields=None,
                    sess=None, ctx='form'):
    """Resolve specs de botão para `Button` (Form.buttons / List.buttons).

    Cada spec aceita: instância `Button` pronta (presets e `BTN_PRINT`/
    `BTN_SEND`), nome de preset em `ACTIONS` (ex.: `'on_off'`),
    `{nome: {overrides}}` (preset com ajustes) ou dict custom. Toda chave é
    validada — chave desconhecida, destino ambíguo ou campo inexistente em
    `enabled` levanta erro em vez de ser descartado em silêncio.

    Parâmetros de validação: `where` (rótulo do contexto, p/ mensagens),
    `valid_fields` (nomes de campo válidos para `enabled`), `sess` (dict com
    `has_fields`/`has_table`, para `position` de sessão) e `ctx` (`'form'` ou
    `'list'`).
    """
    if not specs:
        return []
    resolved = []
    for spec in specs:
        name = None
        field_name = None
        if isinstance(spec, Button):
            # Instância pronta: as factories `BTN_PRINT`/`BTN_SEND` e os presets
            # já são Buttons. Copia porque a validação normaliza `enabled`/
            # `field`/`url` in-place — sem a cópia, o preset compartilhado seria
            # contaminado pelo primeiro registro que o usasse.
            btn = replace(spec)
        elif isinstance(spec, str):
            name = spec
            base = ACTIONS.get(name)
            if base is None:
                raise KeyError(
                    f"Botão padrão '{name}' não existe em ajsystem.defs.buttons.ACTIONS. "
                    f"Disponíveis: {', '.join(ACTIONS)}"
                )
            btn = replace(base)
        elif isinstance(spec, dict) and 'label' not in spec and len(spec) == 1:
            name, overrides = next(iter(spec.items()))
            base = ACTIONS.get(name)
            if base is None:
                raise KeyError(
                    f"Botão padrão '{name}' não existe em ajsystem.defs.buttons.ACTIONS. "
                    f"Disponíveis: {', '.join(ACTIONS)}"
                )
            overrides = dict(overrides or {})
            field_name = overrides.pop('field', None)
            unknown = set(overrides) - set(Button.__dataclass_fields__)
            if unknown:
                raise _err(where, f"{name}", f"chave(s) desconhecida(s): {', '.join(sorted(unknown))}.")
            btn = replace(base, **overrides)
        else:
            cfg = dict(spec)
            field_name = cfg.get('field')
            unknown = set(cfg) - set(Button.__dataclass_fields__)
            if unknown:
                raise _err(where, cfg.get('label') or '?', f"chave(s) desconhecida(s): {', '.join(sorted(unknown))}.")
            btn = Button(**cfg)
        if btn.on_off and bp_name and not btn.url:
            btn.url = f'{bp_name}.toggle'
        if btn.on_off:
            btn.field = field_name or btn.field or 'ativo'
        _check_destination(btn, where)
        _check_enabled(btn, where, valid_fields)
        if ctx == 'list':
            _check_list(btn, where)
        if sess is not None:
            _check_position(btn, where, sess.get('has_fields'),
                            sess.get('has_table'))
        resolved.append(btn)
    return resolved


def modal_script(title=None, lines=None, *, buttons=None, icon=None,
                 wide=False, html=None):
    """Monta `<script>ajModal(...)</script>` com escape seguro, para uso como
    retorno do `render` de um botão (ex.: `print_report(...)`).

    Espelha 1:1 as opts do `ajModal` (ver `sys.html`): `title`, `lines` (str
    ou lista — texto seguro), `buttons` ([{label, cls, value, icon}]),
    `icon` (heroicon), `wide` (bool), `html` (confiável, já sanitizado pelo
    chamador — NUNCA passe dado cru do banco aqui; prefira `lines`).

    Limites: modal informativo (sem callbacks — confirmação com ação segue
    via `confirm_msg`/JS); `instance` pode ser `None` (trate no chamador).
    """
    if isinstance(lines, str):
        lines = [lines]
    opts: Dict[str, Any] = {}
    if title is not None:
        opts['title'] = title
    if lines:
        opts['lines'] = [str(t) for t in lines]
    if buttons is not None:
        opts['buttons'] = [dict(b) for b in buttons]
    if icon is not None:
        opts['icon'] = icon
    if wide:
        opts['wide'] = True
    if html is not None:
        opts['html'] = html
    payload = json.dumps(opts, ensure_ascii=False).replace('</', '<\\/')
    return f'<script>ajModal({payload});</script>'

