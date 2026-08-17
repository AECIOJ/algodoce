"""Spec `Page` — configuração declarativa de páginas (camada de dados).

O módulo de rotas declara `Page` como dict com:

- `type` (opcional, default `'custom'`): tipo da página.
  Valores: `'custom'`, `'crud'`, `'showcase'`, `'cart'`, `'contacts'`.
- `max_width` (opcional): largura máxima do PAINEL (conteúdo) em `ch`,
  centralizada. `int` → `{n}ch`; string → CSS pronto.
- `route` (opcional): prefixo de URL (`'vitrine'` → `/vitrine`).
- `template` (opcional): `{'type': 'html'|'markdown', 'file': '...', ...}`.
- `events` (opcional): dict de hooks — `on_send` (pós-envio, cart),
  `on_show` (pre-render, qualquer tipo single-page).
- `props` (opcional): propriedades específicas do tipo:
  - `custom`: sem props (renderiza `template`).
  - `crud`: `tabs` (estrutura de abas), `list` (config listagem),
    `form` (config formulário), `reports` (relatórios).
  - `showcase`: `fields`, `filter`, `layout`, `show`, `client_fields`,
    `badge_id`.
  - `cart`: `sessions` (sessões table/form).
  - `contacts`: lista de contatos `{titulo: {type, value}, ...}`.

Para `crud`, `props.tabs` mapeia o id da aba (chave = rótulo exibido)
para um dict com `type` (opcional): `List`, `Filter`, `Report` ou
`Custom`. Derivado da chave quando omitido (`Dados`→`List`,
`Filtros`→`Filter`, `Relatórios`→`Report`, senão `Custom`).
`props.list` é mergeado na aba `type='List'` (se existir).

Se o `Page` declarado não incluir aba do tipo `Filter`, uma `Filtros`
default é acrescentada para não perder a filtragem da listagem.
"""
from dataclasses import dataclass, field
from typing import Optional

PAGE_TYPES = ('List', 'Filter', 'Report', 'Custom')
PAGE_PAGE_TYPES = ('custom', 'crud', 'showcase', 'cart', 'contacts')


@dataclass
class Tab:
    id: str
    type: str = 'Custom'
    max_width: Optional[int] = None
    template: Optional[str] = None
    config: dict = field(default_factory=dict)


def _default_type(key):
    norm = (key or '').strip().lower()
    if norm == 'dados':
        return 'List'
    if norm in ('filtros', 'filtrar'):
        return 'Filter'
    if norm in ('relatorios', 'relatório', 'relatórios', 'reports', 'report'):
        return 'Report'
    return 'Custom'


def _normalize_max_width(value):
    if value is None or value == '':
        return None
    value = int(value)
    if value <= 0:
        raise ValueError(f"Page: max_width deve ser positivo (recebido {value})")
    return value


def resolve_max_width(value):
    """`max_width` do `Page`: `int` → `<n>ch`; string é CSS pronto.

    Aceita `int` (largura em caracteres) ou string CSS (ex. `'48rem'`).
    `None`/vazio → sem limite (largura da página).
    """
    if value is None or value == '':
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        if value <= 0:
            raise ValueError(f"Page: max_width deve ser positivo (recebido {value})")
        return f'{value}ch'
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError("Page: max_width deve ser int (largura em ch) ou string CSS")


class Page:
    """Contêiner declarativo de configuração de página.

    Estrutura:
        Page = {
            'type': 'custom'|'crud'|'showcase'|'cart'|'contacts',
            'max_width': int|str,
            'route': str,
            'template': {'type': 'html'|'markdown', 'file': str, ...},
            'events': {'on_send': callable, 'on_show': callable},
            'props': { ... },  # conforme o type
        }
    """

    def __init__(self, spec=None):
        spec = spec or {}
        self.type = spec.get('type', 'custom') if isinstance(spec, dict) else 'custom'
        self.props = spec.get('props', {}) if isinstance(spec, dict) else {}
        self.events = spec.get('events', {}) if isinstance(spec, dict) else {}
        self.crud = self.type == 'crud'
        self.single = self.type != 'crud'
        self.template = spec.get('template') if isinstance(spec, dict) else None
        self.max_width = resolve_max_width(spec.get('max_width')) if isinstance(spec, dict) else None

        self.items = []
        if not self.crud:
            return

        tabs = self.props.get('tabs', {})
        list_cfg = self.props.get('list', {})
        if not tabs:
            tabs = {'Dados': {'type': 'List'}}
        for key, cfg in tabs.items():
            cfg = dict(cfg or {})
            cfg['id'] = key
            if cfg.get('type') == 'List' and list_cfg:
                cfg.update(list_cfg)
            self.items.append(Tab(
                id=key,
                type=cfg.pop('type', None) or _default_type(key),
                max_width=_normalize_max_width(cfg.pop('max_width', None)),
                template=cfg.pop('template', None),
                config=cfg,
            ))
        for tab in self.items:
            if tab.type not in PAGE_TYPES:
                raise ValueError(
                    f"Page: tipo inválido '{tab.type}' na aba '{tab.id}' "
                    f"(válidos: {', '.join(PAGE_TYPES)})"
                )
        if not any(t.type == 'Filter' for t in self.items):
            self.items.append(Tab(id='Filtros', type='Filter'))

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def by_id(self, tab_id):
        for t in self.items:
            if t.id == tab_id:
                return t
        return None

    @property
    def active(self):
        return self.items[0].id if self.items else ''

    @property
    def dados(self):
        """Aba `type='List'` (config da listagem), para `core.do_list`."""
        for t in self.items:
            if t.type == 'List':
                return t
        return None

    @classmethod
    def from_module(cls, mod):
        return cls(getattr(mod, 'Page', None))
