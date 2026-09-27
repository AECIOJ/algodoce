"""Locale do framework: textos do framework traduzidos por `App.locale`.

O idioma vem do app, em `app/config.py` (`APP = {..., 'locale': 'pt'}`), e o
framework já embarca os catálogos — copiar `ajsystem/` inteiro traz a tradução
junto, sem dependência do app.

Como o texto circula
--------------------
`en.py` é a âncora: cada constante é a chave **e** o fallback. O código do
framework usa a constante, não o texto:

    from ajsystem.locales.en import SAVE
    BTN_SAVE = Button(label=SAVE)     # label == 'Save' (inglês)

e a tradução acontece no render, em `Button.text()`:

    'Salvar'

Por isso nunca vaza chave para a tela e texto faltando no locale degrada para
inglês — erro que se enxerga, não bug silencioso. Corrigir a redação de um texto
é editar **uma linha do `pt.py`**, sem tocar em código.

O app não é obrigado a usar locale
----------------------------------
Ele pode escrever o texto direto no spec (`'Plurar'`), que é o idioma dele. Se
quiser participar, usa a chave do framework (`label=SAVE`) ou traz o próprio
catálogo: `t('Plurar', MEU_CATALOGO)` (dict `{'Plurar': 'Publicar'}`).

LIMITE DE ESCOPO — isto traduz TEXTO, não formatação
----------------------------------------------------
`locale` não mexe em número, moeda ou data. `core/formats.py` segue com
`'pt-BR'`, `R$` e `dd/mm/yyyy`, e `defs/constants.py` já escolhe locale **por
registro** (moeda 1→pt-BR, 2→en-US). Um global aqui para formatação seria
factualmente errado. Placeholder: `{label}`.
"""
import importlib
import pkgutil
from types import ModuleType

from ajsystem.locales import en as _en

# cache por locale: {locale: {chave_en: texto_traduzido}}
_CACHE = {}


def _nomes(mod: ModuleType) -> list:
    """Constantes públicas de um catálogo (tudo que não começa com `_`)."""
    return [n for n in vars(mod) if not n.startswith('_')]


def locale_ativo() -> str:
    """Locale declarado pelo app em `App.locale`.

    Import tardio de propósito: `core.adapter` importa `app.config` e os models,
    e os módulos de `defs/` (inclusive `buttons.py`) precisam deste pacote sem
    puxar essa cadeia.
    """
    from ajsystem.core.adapter import APP
    return getattr(APP, 'locale', 'pt') or 'pt'


def disponiveis() -> list:
    """Locales que acompanham o framework (módulos em `ajsystem/locales/`)."""
    return sorted(m.name for m in pkgutil.iter_modules(__path__))


def _mapa_en() -> dict:
    """Valores de `en.py` por nome, com valores únicos garantidos.

    O valor é a chave de tradução, então dois nomes com o mesmo texto colidiriam
    no dicionário e um sobrescreveria o outro em silêncio — foi o que aconteceu
    com `NEW`/`ADD` quando ambos eram '+ Adicionar' em português. Melhor falhar
    na carga.
    """
    por_nome = {}
    vistos = {}
    for nome in _nomes(_en):
        valor = getattr(_en, nome)
        if not isinstance(valor, str):
            raise ValueError(
                f"locales/en.py: {nome} deve ser str, é {type(valor).__name__}")
        if valor in vistos:
            raise ValueError(
                f"locales/en.py: {nome!r} e {vistos[valor]!r} têm o mesmo valor "
                f"({valor!r}) — o valor é a chave, então um sobrescreveria o "
                f"outro. Escolha textos ingleses distintos.")
        vistos[valor] = nome
        por_nome[nome] = valor
    return por_nome


def catalogo(locale=None) -> dict:
    """Mapa `{texto_en: texto_traduzido}` do locale, montado uma vez e cacheado.

    Só as chaves que `en.py` declara entram: o catálogo de um idioma é um
    *overlay*, então o app pode ter constantes próprias (que ninguém traduz) sem
    quebrar o framework.
    """
    loc = locale or locale_ativo()
    if loc in _CACHE:
        return _CACHE[loc]

    if loc == 'en':
        _CACHE[loc] = {}          # fallback é a própria chave
        return _CACHE[loc]

    try:
        mod = importlib.import_module(f'{__name__}.{loc}')
    except ModuleNotFoundError:
        raise ValueError(
            f"App.locale={loc!r} sem catálogo em ajsystem/locales/. "
            f"Disponíveis: {', '.join(disponiveis()) or '(nenhum)'}.") from None

    en_por_nome = _mapa_en()
    tabela = {}
    for nome in _nomes(mod):
        chave = en_por_nome.get(nome)     # None = chave que só o app tem
        if chave is not None:
            tabela[chave] = getattr(mod, nome)
    _CACHE[loc] = tabela
    return tabela


def t(texto, catalogo_proprio=None):
    """Traduz `texto` (um valor de `locales/en.py`) para o locale ativo.

    Devolve `texto` intacto quando não há tradução — inclusive quando `texto` não
    é uma chave conhecida, o que torna seguro passar copy do app por aqui.
    `catalogo_proprio` é um dict opcional do app, com o mesmo formato
    (`{'Plurar': 'Publicar'}`), para o app traduzir as chaves dele.
    """
    if catalogo_proprio is not None:
        if texto in catalogo_proprio:
            return catalogo_proprio[texto]
        return texto
    return catalogo().get(texto, texto)
