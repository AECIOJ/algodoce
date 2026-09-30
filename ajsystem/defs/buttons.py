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

# ── Posições de botão ──
# São 8 nomes, e o MESMO nome se comporta de forma diferente conforme o
# contexto que vai renderizar o botão (ver `POSITION_CONTEXT`):
#
#   form  → as barras do form inteiro (topo e rodapé)
#   sessão com `fields`      → o bloco de fields (o `fields` decide, mesmo
#                              quando a sessão também tem `table`/`query`)
#   sessão só com `table/query` → a tabela/query (faixa acima e faixa de ação
#                              embaixo), não o rótulo da sessão
#
# `before`/`after` são os atalhos sem alinhamento de `top_left`/`bottom_left`;
# `left`/`right` só existem junto de `fields` (mesma linha do bloco).
POS_LEFT = 'left'
POS_RIGHT = 'right'
POS_BEFORE = 'before'
POS_AFTER = 'after'
POS_TOP_LEFT = 'top_left'
POS_TOP_RIGHT = 'top_right'
POS_BOTTOM_LEFT = 'bottom_left'
POS_BOTTOM_RIGHT = 'bottom_right'

POSITIONS = (POS_LEFT, POS_RIGHT, POS_BEFORE, POS_AFTER,
             POS_TOP_LEFT, POS_TOP_RIGHT, POS_BOTTOM_LEFT, POS_BOTTOM_RIGHT)

POSITION_CONTEXT = {
    # form: só as barras do form inteiro.
    'form': (POS_TOP_LEFT, POS_TOP_RIGHT, POS_BOTTOM_LEFT, POS_BOTTOM_RIGHT),
    # sessão só de fields: tudo — `left`/`right` na mesma linha, o resto
    # acima/abaixo do bloco.
    'fields': POSITIONS,
    # sessão com table/query e SEM fields: `left`/`right` não têm onde ficar,
    # porque não existe um bloco de fields para alinhar. Havendo `fields`, o
    # contexto é 'fields' e o botão vai para o head/tail desse bloco.
    'table': (POS_BEFORE, POS_AFTER, POS_TOP_LEFT, POS_TOP_RIGHT,
              POS_BOTTOM_LEFT, POS_BOTTOM_RIGHT),
}


def btn_style(color: str, variant: str = 'outline', size: str = 'sm') -> str:
    """Classe CSS do botão a partir da cor, do estilo e do tamanho.

    'ghost' não carrega cor: é o estilo da navegação de registro
    (⏮ ← → ⏭), que precisa sumir no fundo em vez de competir com as ações.
    """
    if variant == 'ghost':
        return f'btn-ghost btn-{size}'
    base = f'btn-{color} btn-{size}'
    return f'{base} btn-outline' if variant == 'outline' else base


# Estilos aceitos em `Button.variant`. `ghost` é o único que ignora `color`.
BUTTON_VARIANTS = ('solid', 'outline', 'ghost')


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
    # `variant` é o eixo de estilo: 'solid' (preenchido), 'outline' (contorno) ou
    # 'ghost' (sem fundo, sem cor — é o que a barra de navegação de registro usa).
    # `ghost` descarta `color`: o que ele emite é `btn-ghost btn-sm`, igual ao
    # markup que os templates escreviam à mão antes do catálogo.
    variant: str = 'outline'
    size: str = 'sm'
    cls: str = ''
    # Nome acessível. Vazio = cai no `label`; com `label=''` (botão só-ícone) é
    # o `title` que dá nome ao botão e o tooltip do mouse.
    title: str = ''
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

    # ── posicionamento (8 valores; o mesmo nome muda de sentido conforme o
    #    contexto — ver `POSITION_CONTEXT`) ──
    position: str = POS_TOP_RIGHT
    on_off: bool = False
    field: Optional[str] = None

    def btn_cls(self) -> str:
        return self.cls or btn_style(self.color, self.variant, self.size)

    def text(self) -> str:
        """Rótulo do botão. `label` JÁ é o texto do locale ativo (veja
        `ajsystem/locales/__init__.py`), então aqui não há o que traduzir.

        O método sobrevive como pass-through porque `label` é o contrato: um app
        pode escrever o texto dele direto (`label='Plular'`), e `text()` continua
        sendo a leitura correta sem que o template precise saber a diferença.
        """
        return self.label

    def title_or_label(self) -> str:
        """Nome acessível: `title` quando declarado, senão o `label`.

        Botão só-ícone (`label=''`) depende disto — sem `title`, os quatro botões
        de navegação de registro não teriam nome acessível nenhum.
        """
        return self.title or self.label

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


# ── Catálogo de tipos ────────────────────────────────────────────────────────
# O que antes eram 27 `Button(...)` avulsos e o dict `ACTIONS`. Cada entrada é a
# APARÊNCIA de um botão padrão: `label` vem de `ajsystem.locales` (já no idioma
# ativo) e `color`/`variant`/`size` alimentam `btn_cls()`. Nenhuma entrada fixa
# `cls` — se fixasse, `cls` sombrearia `btn_style()` e trocar só a `color` não
# mudaria nada no render.
#
# As chaves são o contrato público: é por elas que um app escreve
# `{'generate': {...}}` e `{'delete': {...}}` na spec, sem importar nada. Os
# `BTN_*` abaixo são o mesmo catálogo em forma de constante, derivados daqui —
# nenhum dos dois lados pode divergir do outro, porque todos nascem desta dict.
#
# Props de comportamento (`visible`, `enabled`, `carry`, `url`…) NÃO moram aqui:
# elas dependem do form e do registro, e ficam no ponto de uso.
BUTTON_TYPES = {
    # ── CRUD e persistência ──
    'save':        {'label': i18n.SAVE, 'icon': 'check', 'color': 'success', 'variant': 'solid'},
    'delete':      {'label': i18n.DELETE, 'icon': 'trash', 'color': 'danger', 'variant': 'solid',
                    'confirm_msg': i18n.CONFIRM_DELETE},
    'new':         {'label': i18n.NEW, 'color': 'success', 'variant': 'solid'},
    'edit':        {'label': i18n.EDIT, 'icon': 'pencil-square', 'color': 'primary'},
    'add':         {'label': i18n.ADD, 'color': 'success'},
    'add_item':    {'label': i18n.ADD_ITEM, 'color': 'success'},
    'remove':      {'label': i18n.REMOVE, 'icon': 'minus', 'color': 'danger',
                    'confirm_msg': i18n.REMOVE_ITEM},
    'details':     {'label': i18n.DETAILS, 'icon': 'eye', 'color': 'info'},
    'list':        {'label': i18n.LIST, 'icon': 'clipboard-document-list', 'color': 'secondary'},

    # ── Navegação e controle de fluxo ──
    # `back` tem texto; `first`/`previous`/`next`/`last` são os 4 da barra de
    # registro e são usados só-ícone (`label=''` na spec). Por isso trazem
    # `title` próprio: se dependessem do `label` do catálogo, a spec que esvazia
    # o texto levaria junto o nome acessível.
    'back':        {'label': i18n.BACK, 'icon': 'arrow-left', 'color': 'secondary'},
    'first':       {'label': i18n.FIRST, 'icon': 'chevron-bar-left', 'variant': 'ghost',
                    'title': i18n.FIRST},
    'previous':    {'label': i18n.PREVIOUS, 'icon': 'chevron-left', 'variant': 'ghost',
                    'title': i18n.PREVIOUS},
    'next':        {'label': i18n.NEXT, 'icon': 'chevron-right', 'variant': 'ghost',
                    'title': i18n.NEXT},
    'last':        {'label': i18n.LAST, 'icon': 'chevron-bar-right', 'variant': 'ghost',
                    'title': i18n.LAST},
    'cancel':      {'label': i18n.CANCEL, 'color': 'secondary'},
    'ok':          {'label': i18n.OK, 'color': 'success', 'variant': 'solid'},
    'close':       {'label': i18n.CLOSE, 'icon': 'xmark', 'variant': 'ghost'},
    'apply':       {'label': i18n.APPLY, 'icon': 'funnel', 'color': 'primary', 'variant': 'solid'},
    'clear':       {'label': i18n.CLEAR, 'icon': 'xmark', 'color': 'danger'},
    'exit':        {'label': i18n.EXIT, 'color': 'danger',
                    'confirm_msg': i18n.DISCARD_CHANGES},
    'yes':         {'label': i18n.YES, 'color': 'primary', 'variant': 'solid'},
    'no':          {'label': i18n.NO, 'color': 'secondary'},

    # ── Transição de estado e processos ──
    # "Aprovar/Validar" e "Faturar/Processar" da lista de padrões são uma entrada
    # cada: o rótulo do catálogo é o nome da ação, e quem quiser o sinônimo
    # sobrescreve `label` no ponto de uso.
    'approve':     {'label': i18n.APPROVE, 'icon': 'check', 'color': 'success', 'variant': 'solid'},
    'bill':        {'label': i18n.BILL, 'icon': 'document-text', 'color': 'primary',
                    'variant': 'solid'},
    'reverse':     {'label': i18n.REVERSE, 'icon': 'xmark', 'color': 'danger',
                    'variant': 'solid'},
    'finish':      {'label': i18n.FINISH, 'color': 'success', 'variant': 'solid'},
    'renew':       {'label': i18n.RENEW, 'color': 'info', 'variant': 'solid'},
    'confirm':     {'label': i18n.CONFIRM, 'color': 'success', 'variant': 'solid'},
    'convert':     {'label': i18n.CONVERT, 'icon': 'arrow-path', 'color': 'success',
                    'variant': 'solid'},
    'generate':    {'label': i18n.GENERATE, 'color': 'success', 'variant': 'solid'},
    # Genérico neutro para "executar uma ação do app" sem cor que carregue
    # significado (success/danger). Base de tipos específicos que não são CRUD,
    # fluxo nem estado — ex.: `precos_zerados` no Algodoce.
    'execute':     {'label': i18n.EXECUTE, 'color': 'secondary', 'variant': 'outline'},

    # ── Utilitários e ações secundárias ──
    'print':       {'label': i18n.PRINT, 'icon': 'printer', 'color': 'info'},
    # `chevron-bar-right` é o glifo mais próximo de "baixar" no sprite atual
    # (`arrow-down-tray` não existe). Ver `HEROICONS` no teste de ícones.
    'export':      {'label': i18n.EXPORT, 'icon': 'chevron-bar-right', 'color': 'info'},
    'search':      {'label': i18n.SEARCH, 'icon': 'magnifying-glass', 'color': 'info'},
    # Sem ícone: o sprite não tem `clipboard-document`/`document-duplicate`, e
    # "Copiar" já se explica sozinho pelo rótulo.
    'copy':        {'label': i18n.COPY, 'color': 'secondary'},
    'report':      {'label': i18n.REPORT, 'icon': 'document-text', 'color': 'info'},
    'refresh':     {'label': i18n.REFRESH, 'icon': 'arrow-path', 'color': 'warning'},
    'on_off':      {'label': i18n.ACTIVATE, 'icon': 'check', 'label_off': i18n.DEACTIVATE,
                    'icon_off': 'xmark', 'color': 'success', 'position': POS_TOP_RIGHT,
                    'on_off': True},

    # ── Específicos de auth e de domínio ──
    # Não são CRUD genérico, mas ficam no mesmo catálogo para não espalhar a
    # aparência do botão de login por três arquivos diferentes. Um app que
    # sobrescrever este catálogo pode removê-los sem tocar no framework.
    'login':       {'label': i18n.LOGIN, 'color': 'danger', 'variant': 'solid'},
    'access':      {'label': i18n.ACCESS, 'color': 'danger', 'variant': 'solid'},
    'edit_product': {'label': i18n.EDIT_PRODUCT, 'icon': 'pencil-square', 'color': 'primary'},
}

# Derivados: o mesmo catálogo como constantes, gerados em loop. A constante de
# um tipo é o preset EXATO desse tipo — o par de preset/tipo não pode divergir, porque a
# linha abaixo é a única que os dois constroem. `dir()` no módulo enxerga os
# nomes criados aqui, então `init.py` publica as globals Jinja sem lista.
#
# `print` vira `BTN_PRINT_STYLE` e não `BTN_PRINT`: o nome `BTN_PRINT` pertence à
# factory de relatório, que precisa do dict do relatório para funcionar.
for _nome, _spec in BUTTON_TYPES.items():
    _const = 'BTN_' + _nome.upper() + ('_STYLE' if _nome == 'print' else '')
    globals()[_const] = Button(**_spec)
del _nome, _spec, _const


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
    return replace(BTN_PRINT_STYLE, **opts)


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


# O antigo registro `ACTIONS` virou a entrada `'on_off'` de `BUTTON_TYPES`. O
# resolução por nome continua igual: um nome resolve para o tipo do catálogo, e
# endpoint/campo booleano são derivados por convenção (endpoint =
# '<blueprint>.toggle', campo default 'ativo'). Ver `resolve_buttons`.


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


def _check_position(btn, where, ctx, has_fields=None, has_table=None):
    """Valida `position` contra o contexto que vai renderizar o botão.

    `ctx` é `'form'` (barras do form inteiro) ou `'session'`. Na sessão o
    `fields` é o que decide: havendo `fields`, o botão é desenhado no bloco de
    campos — mesmo que a sessão também traga `table`/`query`, como em
    `Financeiro` (fields + query). Sem `fields`, o botão pertence à tabela.
    Valor fora do contexto levanta erro em vez de sumir em silêncio no render.
    """
    pos = btn.position
    if pos not in POSITIONS:
        raise _err(where, btn.label,
                   f"position '{pos}' não existe. Use: {', '.join(POSITIONS)}.")
    if ctx == 'form':
        key = 'form'
    elif has_table and not has_fields:
        key = 'table'
    elif has_fields:
        key = 'fields'
    else:
        raise _err(where, btn.label,
                   "position só faz sentido em sessão com `fields` e/ou "
                   "`table`/`query`; esta sessão não tem nenhum dos dois.")
    if pos not in POSITION_CONTEXT[key]:
        if key == 'table':
            dica = ("em sessão com `table`/`query` use before/after ou "
                    "top_*/bottom_*.")
        elif key == 'form':
            dica = "no form use top_left/top_right/bottom_left/bottom_right."
        else:
            dica = "em sessão use top_*/bottom_* ou before/after."
        raise _err(where, btn.label,
                   f"position '{pos}' não vale {dica}")


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


def build_catalogo(types=None) -> dict:
    """Junta o catálogo do framework com o do host e devolve o efetivo.

    É a MESMA função para `resolve_buttons` e para o `_toggle_field` do motor
    (que precisa ler `on_off` sem passar por um `Button`), porque dois merges
    divergem no dia seguinte em que um deles ganha uma regra.

    Quatro camadas, na ordem:

        BUTTON_TYPES[tipo-base]  <  entrada do host (sem 'type')  <  spec

    - **A chave é o nome do tipo**, e a entrada do host é um override *parcial*
      da entrada de base. Sem isso, `{'delete': {'color': 'warning'}}` trocaria a
      entrada inteira e perderia o `label`/`icon`/`confirm_msg` dela.
    - **`type` diz de qual tipo genérico o tipo do host diverge.** Sem ele a base
      é o tipo de *mesmo nome* (o caso de sobrescrever `delete`). Com ele, o app
      nomeia um tipo novo que declara só o que muda:
      `{'type': 'generate', 'icon': 'currency-dollar'}`.
    - `type` aponta para tipo que não existe é erro aqui, com o nome — senão o
      `Button(**...)` lá embaixo reclama de `label` faltando e não diz que o
      problema é o tipo base declarado.
    - Nenhuma camada muta `BUTTON_TYPES`: o merge é sempre por dict nova.
    """
    catalogo = dict(BUTTON_TYPES)
    for chave, entrada in (types or {}).items():
        if not isinstance(entrada, dict):
            raise TypeError(f"entrada de botoes[{chave!r}] não é dict: "
                            f"{type(entrada).__name__}.")
        base = entrada.get('type', chave)
        if base not in BUTTON_TYPES:
            # Duas causas bem diferentes com a mesma consequência (a entrada
            # ficaria sem `label` e o `Button(**...)` reclamaria depois), então a
            # mensagem diz qual das duas é — senão `type='gerate'` (digitação) e
            # "esqueci de declarar a base" viram o mesmo erro.
            if 'type' in entrada:
                raise KeyError(
                    f"botoes[{chave!r}] declara type={base!r}, que não existe em "
                    f"ajsystem.defs.buttons.BUTTON_TYPES. Disponíveis: "
                    f"{', '.join(BUTTON_TYPES)}"
                )
            raise KeyError(
                f"botoes[{chave!r}] não existe em BUTTON_TYPES e não declara "
                f"'type'. Todo tipo do app diverge de um genérico: ponha "
                f"'type': '<genérico>' em botoes[{chave!r}], ou sobrescreva um "
                f"tipo que já tenha o nome. Genéricos: {', '.join(BUTTON_TYPES)}"
            )
        # `type` sai do merge: é metadado de qual base usar, não prop de Button.
        catalogo[chave] = {**BUTTON_TYPES[base],
                           **{k: v for k, v in entrada.items() if k != 'type'}}
    return catalogo


def resolve_buttons(specs, bp_name=None, *, where=None, valid_fields=None,
                    sess=None, ctx='form', types=None):
    """Resolve specs de botão para `Button` (Form.buttons / List.buttons).

    Cada spec aceita: instância `Button` pronta (os `BTN_*` e as factories
    `BTN_PRINT`/`BTN_SEND`), nome de tipo do catálogo (ex.: `'on_off'`,
    `'delete'`), `{tipo: {overrides}}` ou dict custom. Toda chave é validada —
    chave desconhecida, destino ambíguo ou campo inexistente em `enabled` levanta
    erro em vez de ser descartado em silêncio.

    Parâmetros de validação: `where` (rótulo do contexto, p/ mensagens),
    `valid_fields` (nomes de campo válidos para `enabled`), `sess` (dict com
    `has_fields`/`has_table`, para `position` de sessão) e `ctx` (`'form'` ou
    `'list'`).

    `types` é o catálogo do host (`app.botoes.Buttons`), mesclado sobre
    `BUTTON_TYPES` — o mesmo papel que o `Schema` do módulo tem sobre a entity
    em `resolve_entity_fields`. O merge é o de `build_catalogo`: o app declara
    de qual tipo genérico diverge (`type`) e só o que muda, e a spec declara
    sobre o app. Nenhuma camada muta `BUTTON_TYPES`.
    """
    if not specs:
        return []
    catalogo = build_catalogo(types)
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
            base = catalogo.get(name)
            if base is None:
                raise KeyError(
                    f"Botão padrão '{name}' não existe em ajsystem.defs.buttons.BUTTON_TYPES. "
                    f"Disponíveis: {', '.join(catalogo)}"
                )
            btn = replace(Button(**base))
        elif (isinstance(spec, dict) and 'label' not in spec and len(spec) == 1
                and next(iter(spec)) in catalogo):
            # `{'tipo': {overrides}}` — merge raso: catálogo base < catálogo do
            # host < spec. O gate `next(iter(spec)) in catalogo` é o que separa
            # este ramo do dict custom: `{'enabled': {...}}` tem uma chave só e
            # um dict como valor, mas 'enabled' não é tipo, então cai no `else`
            # e vira `Button` normal.
            name, overrides = next(iter(spec.items()))
            base = {**catalogo[name], **(overrides or {})}
            field_name = base.pop('field', None)
            unknown = set(base) - set(Button.__dataclass_fields__)
            if unknown:
                raise _err(where, f"{name}", f"chave(s) desconhecida(s): {', '.join(sorted(unknown))}.")
            btn = replace(Button(**base))
        else:
            cfg = dict(spec)
            if 'label' not in cfg and len(cfg) == 1:
                # Chegou aqui por ter uma chave só e nenhuma chave de tipo. A
                # mensagem precisa dizer isso, senão o `Button(**cfg)` reclama
                # de `label` faltando e não diz que o problema é o nome do tipo.
                raise KeyError(
                    f"Botão padrão '{next(iter(cfg))}' não existe em "
                    f"ajsystem.defs.buttons.BUTTON_TYPES. "
                    f"Disponíveis: {', '.join(catalogo)}"
                )
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
        elif sess is not None:
            _check_position(btn, where, 'session', sess.get('has_fields'),
                            sess.get('has_table'))
        else:
            _check_position(btn, where, 'form')
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

