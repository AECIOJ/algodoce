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

    - `url`: rota registrada (nome de endpoint, ex.: 'orcamentos.list') ou
      caminho literal ('/pagina', 'https://...'). É escape de navegação — não
      monta módulo.
    - `page`: arquivo do módulo quando o rótulo do menu ≠ nome do arquivo
      (ex.: menu 'Operações', 'page': 'opr' → app.routes.sys.opr).
    - Se nem `url` nem `page` → módulo derivado do rótulo.
    """
    url: Optional[str] = None
    icon: str = ''
    submenus: Optional[Dict[str, 'MenuItem']] = None
    page: Optional[str] = None


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
    - `version`: versão exibida no rodapé. Se não informada, `build_app`
      procura o arquivo `versao.py` do app (YEAR/MONTH/SEQUENCE).
    """
    name: str
    logo: str
    tema: str
    title: Optional[str] = None
    version: Optional[str] = None
    modules: List[Module] = field(default_factory=list)
    def module(self, type):
        """Retorna o módulo com o `type` dado; se ausente, o primeiro da lista
        (módulo padrão). `None` apenas se a lista estiver vazia."""
        for m in self.modules:
            if m.type == type:
                return m
        return self.modules[0] if self.modules else None


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


def _versao_de_arquivo(caminho):
    """Lê um arquivo `versao.py` do app (YEAR/MONTH/SEQUENCE) → 'v1.YY.MM-SEQ'.

    Formato padrão do arquivo gerado (veja `app/versao.py`). Retorna '' se o
    arquivo não existir ou não tiver as variáveis esperadas.
    """
    try:
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("__versao__", caminho)
        vmod = importlib.util.module_from_spec(spec)
        sys.modules["__versao__"] = vmod
        spec.loader.exec_module(vmod)
        ano = str(vmod.YEAR)[-2:]
        return f"v1.{ano}.{vmod.MONTH}-{vmod.SEQUENCE}"
    except Exception:
        return ''


def build_app(cfg, versao_path=None) -> App:
    cfg = dict(cfg)
    mods = [build_module(m) for m in cfg.pop('modules', None) or []]
    tipos = [m.type for m in mods]
    if len(tipos) != len(set(tipos)):
        dup = {t for t in tipos if tipos.count(t) > 1}
        raise ValueError(f"APP['modules'] com tipos duplicados: {sorted(dup)}")
    versao = cfg.get('version') or ''
    if not versao and versao_path:
        versao = _versao_de_arquivo(versao_path)
    return App(
        name=cfg['name'],
        title=cfg.get('title'),
        logo=cfg['logo'],
        version=versao or None,
        tema=cfg['tema'],
        modules=mods,
    )


def build_temas(cfg) -> Dict[str, Tema]:
    return {k: build_tema(k, v) for k, v in cfg.items()}
