"""INPUTS — catálogo de tipos de input (camada de dados, padrão `Button`).

`Field.input` é o NOME de um tipo. O que o nome significa — tag HTML, classes,
largura padrão, alinhamento, se o valor volta booleano, máscara e validador, em
qual slot o controle é renderizado — mora num `Input`, e não em `if field.input
== ...` espalhado por template e `core/`.

Forma espelhada em `defs/buttons.py`: catálogo genérico (`INPUT_TYPES`), catálogo
do motor (`Inputs`), `INPUTS` semeia o merge, e um preset por tipo sai em loop
(`IN_TEXT`, `IN_TOGGLE`, …) para o Python importar por nome.

O que NÃO mora aqui: `options`, `rows`, `min`/`max`/`step`, `currency`,
`percent`, `on_set`, `calc`. São props do `Field` — dependem do campo, não do
tipo. `mask` e `validate` estão aqui por um motivo só: `cpf`/`cnpj` são inputs
do app que precisam carregar a máscara e o validador que os definem, e um
`Input` não aceita chave que não seja prop sua.

CAMADAS. A precedência é a dos botões:

    INPUTS  <  inputs do app  <  inputs da rota  <  input_props (spec do uso)

A camada do app é o DEFAULT DE PROCESSO (`definir_camadas_padrao`), porque
`Field` é construído em 6 lugares — expansão de entidade, listagem, filtro,
relatório, transformadores — e nem todos passam pelo `Form`. A da rota entra
por `build_field(..., inputs=...)` quando o módulo declara `Inputs`. É o mesmo
princípio do catálogo de locales (`locales/__init__.py`): um processo, um app,
resolvido no import e congelado.
"""
from dataclasses import dataclass
from typing import Optional, Union

from ajsystem import locales as i18n

# Slots onde o controle pode ser renderizado. `body` é o corpo do form; `bar` é
# a `app-bar-right` da página do form — o mesmo slot de `pos_form: 3`, que é o
# que o `Field` tem que declarar para um input de barra ser aceito.
INPUT_SLOTS = ('body', 'bar')

# Grupos de comandos de máscara liberados por tipo. `@B/@X` só em `number`;
# `@U/@L/@C/@T/@R` só em texto. `'*'` libera os dois (opt-in do host).
MASK_GROUPS = {
    'text':   frozenset('ULCTR'),
    'number': frozenset('BX'),
    '*':      frozenset('ULCTRBX'),
}

# Editor que a listagem usa para filtrar o campo. Antes isso era um `if` por
# nome de input em `core/list.py`; virar prop tira o `core` de conhecer os
# nomes do catálogo.
FILTER_KINDS = ('text', 'boolean', 'date', 'number', 'select')


# ── Dataclass Input ──────────────────────────────────────────────────────────
@dataclass
class Input:
    """Um tipo de input: como o controle se parece e como o valor volta."""

    # ── identidade ──
    label: str = 'Input'

    # ── tag e aparência ──
    html_type: str = 'text'      # atributo `type` do <input>; '' quando não é <input>
    inputmode: str = ''          # `decimal` etc. — hoje hardcoded no template
    cls: str = 'input input-bordered input-sm'
    size: Optional[int] = None   # largura padrão em ch; None = 18, o default do Field
    align: str = 'left'
    slot: str = 'body'           # 'body' | 'bar'

    # ── o valor, na ida e na volta ──
    boolean: bool = False        # True/False, e ausência no POST = False
    number: bool = False         # formatado por fmt_num/fmtid
    multi: bool = False          # lista de opções marcadas
    masked: bool = False         # o texto passa por `mask`/`mask_cmd`
    textual: bool = True         # texto livre, aceita transform @U/@L/@C/@T
    filter_kind: str = 'text'    # editor de filtro da listagem (ver FILTER_KINDS)
    upload: bool = False         # o valor é o nome de um arquivo enviado

    # ── máscara ──
    mask: Optional[str] = None
    validate: Optional[Union[str, list]] = None
    mask_group: str = 'text'

    # ── rota do motor em vez de submeter ──
    route: str = ''              # nome do endpoint; '' = o input grava no POST
    method: str = 'GET'
    # Endpoint resolvido: o `Form` junta o blueprint ao `route` no momento em
    # que sabe o slug (mesmo papel do `Button.url` derivado do `on_off` antigo).
    # Fica no `Input` do Field, que é uma instância só dele — nada é compartilhado.
    endpoint: str = ''
    label_on: Optional[str] = None
    label_off: Optional[str] = None
    badge_on: Optional[str] = None
    badge_off: Optional[str] = None

    def __post_init__(self):
        if self.slot not in INPUT_SLOTS:
            raise ValueError(
                f"INPUT '{self.label}': slot {self.slot!r} desconhecido — "
                f"use {', '.join(INPUT_SLOTS)}.")
        if self.mask_group not in MASK_GROUPS:
            raise ValueError(
                f"INPUT '{self.label}': mask_group {self.mask_group!r} "
                f"desconhecido — use {', '.join(MASK_GROUPS)}.")
        if self.filter_kind not in FILTER_KINDS:
            raise ValueError(
                f"INPUT '{self.label}': filter_kind {self.filter_kind!r} "
                f"desconhecido — use {', '.join(FILTER_KINDS)}.")
        if self.method not in ('GET', 'POST'):
            raise ValueError(
                f"INPUT '{self.label}': method {self.method!r} — só GET ou POST.")
        # `masked` não ganha validação própria: quem restringe os comandos `@X` é
        # `mask_group`, e `Field.__post_init__` cobra via `Input.aceita`. Um check
        # aqui repetiria a regra — e brigaria com `number`, que é `masked` com
        # `mask_group='number'`.

    @property
    def mask_cmds(self) -> frozenset:
        """Comandos `@X` que este tipo aceita."""
        return MASK_GROUPS[self.mask_group]

    def aceita(self, cmds) -> bool:
        """O conjunto de comandos de máscara `cmds` é válido para este tipo?"""
        return not (set(cmds) - self.mask_cmds)


# ── Catálogo genérico ────────────────────────────────────────────────────────
# Um tipo existe aqui se ele faz sentido para QUALQUER entidade, e o app nunca
# precisa saber os nomes: `'type': 'BOOL'` na Entity já traz o editor.
INPUT_TYPES = {
    # ── texto ──
    'text':           {'html_type': 'text',     'masked': True},
    'textarea':       {'html_type': '', 'cls': 'textarea textarea-bordered',
                        'masked': True},
    'email':          {'html_type': 'email',    'masked': True},
    'tel':            {'html_type': 'tel',      'masked': True},
    'password':       {'html_type': 'password', 'masked': True},

    # ── número ──
    # `html_type: 'text'` de propósito: é o `text` com `inputmode` que deixa a
    # máscara e o `decimals` do motor formatarem no lugar certo. Um
    # `type="number"` do HTML não aceita máscara.
    'number':         {'html_type': 'text', 'inputmode': 'decimal',
                        'align': 'right', 'size': 12, 'mask_group': 'number',
                        'number': True, 'masked': True, 'textual': False,
                        'filter_kind': 'number'},

    # ── escolha ──
    'select':         {'html_type': '', 'cls': 'select select-bordered select-sm',
                        'filter_kind': 'select'},
    # Editor padrão do booleano — `type: 'BOOL'` na Entity aponta para cá. É o
    # `input[type=checkbox]` que o form já desenhava, agora com nome próprio.
    'checkbox':       {'html_type': '', 'cls': 'checkbox checkbox-sm',
                        'boolean': True, 'size': 6, 'textual': False,
                        'filter_kind': 'boolean'},
    'multi':          {'html_type': '', 'cls': '', 'multi': True},

    # ── data/hora ──
    'date':           {'html_type': 'date', 'size': 12, 'textual': False,
                        'filter_kind': 'date', 'mask': 'dd/mm/yyyy'},
    'datetime-local': {'html_type': 'datetime-local', 'size': 16, 'textual': False,
                        'filter_kind': 'date'},
    'time':           {'html_type': 'time', 'size': 10, 'textual': False},

    # ── arquivo ──
    'image':          {'html_type': '', 'size': 12, 'textual': False,
                        'upload': True},
}


# ── Catálogo do MOTOR ────────────────────────────────────────────────────────
# `INPUT_TYPES` acima é aparência pura. O que mora aqui é o contrário — input
# cujo comportamento é do motor, não da aparência: o motor procura pelo NOME
# porque o que ele faz é do motor.
#
# `toggle` é o caso: ele não submete o form, aciona uma rota de `core/auto` e
# mora na barra do form (`slot='bar'` ⇒ o Field declara `pos_form: 3`). Ele é o
# editor padrão do booleano com outra forma — daí o `type: 'checkbox'` e props
# novas, em vez de repetir o `cls` do checkbox. Se ficasse em `INPUT_TYPES`, um
# app que não usa toggle ainda carregaria a entrada; é a mesma razão que tirou
# `on_off` de `BUTTON_TYPES`.
Inputs = {
    'toggle':      {'type': 'checkbox', 'cls': 'toggle toggle-success',
                    'slot': 'bar', 'route': 'toggle', 'method': 'POST',
                    'label_on': i18n.ACTIVATE, 'label_off': i18n.DEACTIVATE,
                    'badge_on': i18n.ACTIVE, 'badge_off': i18n.INACTIVE},
}

# Catálogo efetivo: o que o merge semeia, antes de qualquer camada do host. É
# a soma dos dois catálogos, com o `type` do catálogo do motor já resolvido
# contra o genérico — `INPUTS` é o que um `Input(**…)` consegue instanciar, e
# o merge e os presets leem daqui para nenhum dos dois enxergar um tipo que o
# outro não vê.
def _resolver(catalogo, chave, entrada):
    """Funde uma entrada de catálogo sobre a base que ela declara."""
    base = entrada.get('type', chave)
    if base not in catalogo:
        # Duas causas muito diferentes com a mesma consequência (a entrada
        # ficaria sem `html_type` e o `Input(**…)` reclamaria depois), então a
        # mensagem diz qual das duas é.
        if 'type' in entrada:
            raise KeyError(
                f"inputs[{chave!r}] declara type={base!r}, que não existe no "
                f"catálogo. Disponíveis: {', '.join(catalogo)}")
        raise KeyError(
            f"inputs[{chave!r}] não existe no catálogo e não declara 'type'. "
            f"Todo tipo do app diverge de um genérico: ponha "
            f"'type': '<genérico>' em inputs[{chave!r}], ou sobrescreva um tipo "
            f"que já tenha o nome. Genéricos: {', '.join(INPUT_TYPES)}")
    # `type` sai do merge: é metadado de qual base usar, não prop de Input.
    return {**catalogo[base],
            **{k: v for k, v in entrada.items() if k != 'type'}}


INPUTS = dict(INPUT_TYPES)
for _chave, _entrada in Inputs.items():
    INPUTS[_chave] = _resolver(INPUTS, _chave, _entrada)
del _chave, _entrada


# ── Camada default do host ───────────────────────────────────────────────────
# `Field` é construído em 6 lugares (expansão de entidade, listagem, filtro,
# relatório, transformadores) e nem todos passam pelo `Form`, então o catálogo
# do app não pode chegar só por parâmetro. Fica num holder de processo, mudado
# uma vez no `init.py` — antes de `registrar_modulos`, porque o `Entity` já é
# expandido no import do model.
_CAMADAS_PADRAO = ()


def definir_camadas_padrao(camadas) -> None:
    """Fixa a camada default do host (o `App.inputs`). Chamado no `init.py`."""
    global _CAMADAS_PADRAO
    _CAMADAS_PADRAO = tuple(c for c in (camadas or ()) if c)


# ── Merge ────────────────────────────────────────────────────────────────────
def build_catalogo_inputs(*camadas) -> dict:
    """Junta os catálogos, do genérico para o do host, e devolve o efetivo.

    Mesma regra e mesma mensagem de `buttons.build_catalogo`: a entrada do host
    é override PARCIAL da base, e `type` (metadado de qual base) sai do merge.

        INPUTS  <  inputs do app  <  inputs da rota

    Nenhuma camada muta `INPUTS`; `None`/`{}` são ignorados. Sem nenhuma
    camada, semeia só `INPUTS`.
    """
    catalogo = dict(INPUTS)
    for camada in camadas:
        for chave, entrada in (camada or {}).items():
            if not isinstance(entrada, dict):
                raise TypeError(f"entrada de inputs[{chave!r}] não é dict: "
                                f"{type(entrada).__name__}.")
            catalogo[chave] = _resolver(catalogo, chave, entrada)
    return catalogo


def module_inputs(mod) -> dict:
    """Lê o `Inputs` de um módulo de rota ({} se ausente/inválido).

    Gêmeo de `buttons.module_buttons`, com o mesmo papel que `Schema` tem sobre
    os campos: o catálogo genérico do motor resolve a chave, o `app.extends.inputs.Inputs`
    descreve o que o app diverge, e o `Inputs` do módulo descreve o que só
    aquela página precisa. Por isso a entrada pode ser só um override parcial:

        Inputs = {'money': {'mask': '@R 999.999,99'}}
    """
    i = getattr(mod, 'Inputs', None)
    return i if isinstance(i, dict) else {}


def resolve_input(nome, overrides=None, *camadas) -> Input:
    """Instancia o `Input` de `nome`, com `overrides` do ponto de uso por cima.

    `overrides` entra depois das camadas porque é o ponto de uso — mesmo lugar
    onde, nos botões, a spec do uso é a última camada do merge. Sem camadas,
    semeia a default do host (`definir_camadas_padrao`).
    """
    cats = [c for c in camadas if c] or list(_CAMADAS_PADRAO)
    catalogo = build_catalogo_inputs(*cats)
    if nome not in catalogo:
        raise KeyError(
            f"input {nome!r} não existe no catálogo. Disponíveis: "
            f"{', '.join(catalogo)}")
    spec = catalogo[nome]
    if overrides:
        desconhecidas = set(overrides) - set(Input.__dataclass_fields__)
        if desconhecidas:
            raise KeyError(
                f"input_props de {nome!r} com chave(s) desconhecida(s): "
                f"{', '.join(sorted(desconhecidas))}.")
        spec = {**spec, **overrides}
    return Input(**spec)


# Derivados: o mesmo catálogo como constantes, geradas em loop. A constante de um
# tipo é o preset EXATO desse tipo — par de preset/tipo não pode divergir, porque
# os dois leem o mesmo `INPUTS`. `dir()` no módulo enxerga os nomes criados
# aqui, então `init.py` publica as globals Jinja sem lista.
for _nome, _spec in INPUTS.items():
    globals()['IN_' + _nome.replace('-', '_').upper()] = Input(**_spec)
del _nome, _spec