"""Page — spec pura de página (camada de dados).

Dataclass declarativa de um módulo de rota, no mesmo padrão de `Field`,
`Form`, `Report`: o app declara `Page = {...}` (dict) ou `Page = Page(...)`
(dataclass); o motor resolve qualquer forma via `parse_page` (idempotente).

Contém o rótulo (`label`, ex.: 'Orçamento') — usado no id da navegação do
form, nas mensagens de inclusão/alteração etc. — e a estrutura da página
(`type`, `crud`, `props` com `form`/`list`/`tabs`, `template`, `route`,
`on_show`).
"""
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Optional


@dataclass
class Page:
    # ── Props declarativas ──
    label: Optional[str] = None           # rótulo da página (ex.: 'Orçamento')
    type: str = 'crud'                    # 'crud' | 'redirect' | 'cart' | 'showcase' | 'contacts' | 'custom'
    crud: bool = True                     # se False, não gera rotas CRUD automáticas
    route: Optional[str] = None           # subpasta p/ páginas custom (do_page)
    template: Optional[dict] = None       # config de template custom (do_page)
    props: dict = dc_field(default_factory=dict)   # form / list / tabs / etc.
    on_show: Optional[Callable] = None    # hook executado ao renderizar a página
    upload: Optional[dict] = None         # política de upload da página (sobrescreve App.upload; ausente = herda)

    # Acesso amigável a sub-configs (mantém compat com usos via dict .get)
    def get(self, key, default=None):
        return getattr(self, key, default)


def parse_page(spec) -> Page:
    """dict | Page → Page (idempotente), no padrão de `parse_report`.

    Páginas são declaradas como `Page = {...}` (dict) no app; o motor resolve
    para a dataclass aqui. Aceita também `Page = Page(...)`.
    """
    if isinstance(spec, Page):
        return spec
    if isinstance(spec, dict):
        spec = dict(spec)
        return Page(**{k: v for k, v in spec.items() if k in _page_fields()})
    raise TypeError(f"Page deve ser dict ou Page, recebeu {type(spec).__name__}: {spec!r}")


def _page_fields():
    from dataclasses import fields as dc_fields
    return {f.name for f in dc_fields(Page)}