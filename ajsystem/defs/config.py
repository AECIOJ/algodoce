"""Estrutura declarativa do config do app (APP, Temas).

O host declara os dicts em `app/config.py`; este módulo tipa a estrutura e
coage os dicts em dataclasses (`build_*`). Consumidores do framework
(`core/menu`, `core/do_auth`, `core/auto`, `app/__init__`) acessam por
atributo. Não depende de request nem do motor.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Valor especial para `LayoutTitle.text`: resolve para `APP.title` no render.
TEXTO_APP = 'app_title'


@dataclass
class Tema:
    """Tema de cores do app (design tokens)."""
    base: str = ''
    rotulo: str = ''
    marca: dict = field(default_factory=dict)
    neutras: dict = field(default_factory=dict)
    feedback: dict = field(default_factory=dict)
    apoio: dict = field(default_factory=dict)
    barras: dict = field(default_factory=dict)
    modal: dict = field(default_factory=dict)


@dataclass
class LayoutLogo:
    """Configuração do logo no header."""
    rows: float = 5
    align: str = 'center'


@dataclass
class LayoutTitle:
    """Configuração do título no header."""
    text: Optional[str] = None
    align: str = 'center'
    font: Optional[str] = None
    color: Optional[str] = None


@dataclass
class LayoutHeader:
    """Configuração do header (container com logo + título)."""
    logo: LayoutLogo = field(default_factory=LayoutLogo)
    title: LayoutTitle = field(default_factory=LayoutTitle)


@dataclass
class LayoutFooter:
    """Configuração do footer."""
    font: Optional[str] = None
    color: Optional[str] = None
    user: bool = True


@dataclass
class Layout:
    """Layout visual do módulo (header + footer)."""
    header: LayoutHeader = field(default_factory=LayoutHeader)
    footer: LayoutFooter = field(default_factory=LayoutFooter)


@dataclass
class MenuItem:
    """Item de menu.

    - `page`: arquivo do módulo quando o rótulo do menu ≠ nome do arquivo
      (ex.: menu 'Contas a Receber', 'page': 'receber' → app.routes.sys.receber).
      É a forma padrão de ligar um item ao seu módulo.
    - `url`: rota registrada (nome de endpoint, ex.: 'orcamentos.list') ou
      caminho literal ('/pagina', 'https://...'). É escape de navegação — não
      monta módulo.
    - Se nem `page` nem `url` → módulo derivado do rótulo.
    """
    page: Optional[str] = None
    url: Optional[str] = None
    icon: str = ''
    submenus: Optional[Dict[str, 'MenuItem']] = None


@dataclass(frozen=True)
class Version:
    """Versão do app em partes, exibida como `1.26.10-010`.

    - `cycle`: major fixo do esquema de versionamento (hoje `1`).
    - `year`: ano com 2 dígitos (`26`).
    - `month`: mês 1–12 (`10`).
    - `number`: sequencial do período (`10` → `010`).

    `frozen` porque versão não muda em runtime: só o script de bump
    o script de bump do host a reescreve no config. `text()` compõe a forma
    de leitura — padding em um lugar só, para o rodapé nunca divergir do dict.
    """
    cycle: int
    year: int
    month: int
    number: int

    def __post_init__(self):
        for chave in ('cycle', 'year', 'month', 'number'):
            valor = getattr(self, chave)
            if not isinstance(valor, int) or isinstance(valor, bool):
                raise ValueError(
                    f"APP['version']['{chave}'] deve ser int, veio "
                    f"{valor!r}. Edite APP['version'] em app/config.py.")
        if not 1 <= self.month <= 12:
            raise ValueError(
                f"APP['version']['month'] deve ser 1–12, veio {self.month}.")

    def text(self) -> str:
        """Forma direta de leitura: `1.aa.mm-build` (ex.: `'1.26.10-010'`)."""
        return (f"{self.cycle}.{self.year:02d}.{self.month:02d}-"
                f"{self.number:03d}")


@dataclass
class Module:
    """Módulo (área do app): tipo + página padrão + árvore de menus.

    - `type`: identificador do módulo ('public', 'system', 'admin' ou outro).
      Padrão: 'public'. Devem ser únicos no app.
    - `default_path`: destino padrão do módulo (endpoint nomeado, caminho literal
      ou caminho de menu 'secao/item' — veja §3.3 do README).
    - `triggers`: dict de triggers de UI (ex.: click no logo → popup de login).
      Chave = evento ('click', 'click_dbl'), valor = dict com 'target' e 'action'.
    """
    type: str = 'public'
    default_path: Optional[str] = None
    menus: Dict[str, MenuItem] = field(default_factory=dict)
    triggers: Optional[Dict] = None
    layout: Optional[Layout] = None


@dataclass
class App:
    """Config geral do app (APP): metadados + lista de módulos.

    - `name`: nome do app exibido no cabeçalho/títulos.
    - `version`: versão exibida no rodapé (`Version`: `cycle`/`year`/`month`/
      `number`, ex. `{'cycle': 1, 'year': 26, 'month': 10, 'number': 10}` → lê-se
      `'1.26.10-010'`). É sub-dict do próprio `APP['version']`, em `app/config.py`
      — sem arquivo separado; o script de bump do host incrementa o `number`. Ausente (`None`) = rodapé sem versão. O motor valida as partes
      e exibe `Version.text()` — não interpreta além disso.
    - `upload`: política global de upload (`Page.upload` sobrescreve).
      Ausente (`None`) = `DEFAULT_UPLOAD` abaixo.
    - `botoes`: catálogo de botões do host (`app.extends.buttons.Buttons`), mesclado
      sobre `BUTTON_TYPES` na resolução. Mesmo papel do `Schema` de um módulo
      sobre os campos. Ausente (`None`) = só o catálogo do framework.
    - `inputs`: catálogo de inputs do host (`app.extends.inputs.Inputs`), mesclado sobre
      `INPUTS` na resolução do `Field`. Gêmeo de `botoes`: é aqui que `cpf`,
      `cnpj` e a máscara do telefone ganham forma, e é o que `FIELD_TYPES`
      referencia. Ausente (`None`) = só o catálogo do framework.
    """
    name: str
    logo: str
    tema: str
    title: Optional[str] = None
    version: Optional[Version] = None
    upload: Optional[dict] = None
    botoes: Optional[dict] = None
    inputs: Optional[dict] = None
    modules: List[Module] = field(default_factory=list)
    def module(self, type):
        """Retorna o módulo com o `type` dado; se ausente, o primeiro da lista
        (módulo padrão). `None` apenas se a lista estiver vazia."""
        for m in self.modules:
            if m.type == type:
                return m
        return self.modules[0] if self.modules else None


# Política de upload quando nem `App.upload` nem `Page.upload` declaram.
# `path`: subdir em `dados/uploads` (`''` = raiz); `max_size`: bytes;
# `allowed`: extensões (minúsculas, sem ponto).
DEFAULT_UPLOAD = {
    'path': '',
    'max_size': 5 * 1024 * 1024,
    'allowed': ['png', 'jpg', 'jpeg', 'gif', 'webp'],
}


def build_tema(key, cfg) -> Tema:
    cfg = dict(cfg)
    cfg.setdefault('base', key)
    return Tema(**cfg)


def build_item(cfg) -> MenuItem:
    cfg = dict(cfg)
    sub = cfg.pop('submenus', None) or {}
    submenus = {k: build_item(v) for k, v in sub.items()}
    return MenuItem(**cfg, submenus=submenus or None)


def build_layout(cfg) -> Optional[Layout]:
    if not cfg:
        return None
    cfg = dict(cfg)
    header = cfg.pop('header', None) or {}
    footer = cfg.pop('footer', None) or {}
    logo = header.pop('logo', None) or {}
    title = header.pop('title', None) or {}
    return Layout(
        header=LayoutHeader(
            logo=LayoutLogo(**logo),
            title=LayoutTitle(**title),
        ),
        footer=LayoutFooter(**footer),
    )


def build_module(cfg) -> Module:
    cfg = dict(cfg)
    menus = {k: build_item(v) for k, v in (cfg.pop('menus', None) or {}).items()}
    layout = build_layout(cfg.pop('layout', None))
    return Module(**cfg, menus=menus, layout=layout)


def build_version(cfg) -> Optional[Version]:
    """Constrói o `Version` a partir do sub-dict `APP['version']`.

    Ausente/`None` → `None` (rodapé sem versão). A validação de tipos e do mês
    mora em `Version.__post_init__`, com mensagem nomeando a chave.
    """
    if not cfg:
        return None
    if not isinstance(cfg, dict):
        raise ValueError(
            f"APP['version'] deve ser dict {{cycle, year, month, number}}, veio "
            f"{cfg!r}. Edite APP['version'] em app/config.py.")
    try:
        return Version(cycle=cfg['cycle'], year=cfg['year'],
                       month=cfg['month'], number=cfg['number'])
    except KeyError as e:
        raise ValueError(
            f"APP['version'] sem a chave {e}. Esperado {{cycle, year, month, "
            f"number}} — edite APP['version'] em app/config.py.")


def build_app(cfg, botoes=None, inputs=None) -> App:
    cfg = dict(cfg)
    mods = [build_module(m) for m in cfg.pop('modules', None) or []]
    tipos = [m.type for m in mods]
    if len(tipos) != len(set(tipos)):
        dup = {t for t in tipos if tipos.count(t) > 1}
        raise ValueError(f"APP['modules'] com tipos duplicados: {sorted(dup)}")
    versao = build_version(cfg.get('version'))
    return App(
        name=cfg['name'],
        title=cfg.get('title'),
        logo=cfg['logo'],
        version=versao,
        tema=cfg['tema'],
        upload=cfg.get('upload'),
        botoes=botoes,
        inputs=inputs,
        modules=mods,
    )


def build_temas(cfg) -> Dict[str, Tema]:
    return {k: build_tema(k, v) for k, v in cfg.items()}
