"""Locale do framework: um único catálogo, resolvido uma vez na importação.

O idioma é declarado pelo app em `app/config.py` (`APP = {..., 'locale': 'pt'}`) e
este módulo importa o catálogo correspondente **no momento em que é importado**,
reexportando as constantes no próprio namespace:

    from ajsystem import locales as i18n
    i18n.SAVE          #-> 'Salvar' com locale 'pt', 'Save' com 'en'

Nos templates é o mesmo objeto, com um único global injetado em `init.py`:

    {{ i18n.SAVE }}

Por que "no import" e não "na tradução"
--------------------------------------
Um catálogo importado é congelado na carga. Isso é o ponto: nenhum texto é
traduzido durante a execução, então nada pode capturar a linguagem cedo demais e
transformar num literal solto por accident. `Button(label=i18n.SAVE)` já recebe
`'Salvar'` e a tradução acontece **no import**, uma vez, para todo o processo.

O preço é que o idioma não muda em runtime. O app é monolingue, e o custo de um
trocar é uma linha em `app/config.py` — não um fork do projeto.

`app/config.py` é importado aqui porque não importa nada (é um dicionário puro),
o que torna impossível um ciclo de import. O `except ImportError` cobre o
framework usado avulso, sem o app no path: nesse caso vale o `AJSYSTEM_LOCALE` do
ambiente, ou 'pt'. Locale sem catálogo levanta `ValueError` na carga, com a lista
do que existe — falha alto e com mensagem, em vez de cair no default e ninguém
perceber.

Escopo: só copy visível ao usuário final (rótulos, mensagens de confirmação,
flash e `jsonify(error=...)`). Mensagem de `ValueError` é diagnóstico de
desenvolvedor e fica em português no código, de propósito. Isto traduz TEXTO, não
formatação: `core/formats.py` segue com 'pt-BR', 'R$' e 'dd/mm/yyyy', e
`defs/constants.py` já escolhe locale **por registro**. Placeholder: `{label}`.

O app não é obrigado a usar locale: basta escrever o texto direto no spec
(`label='Plurar'`), que é o idioma dele.
"""
import importlib
import os
import pkgutil


def disponiveis() -> list:
    """Locales que acompanham o framework (módulos em `ajsystem/locales/`)."""
    return sorted(m.name for m in pkgutil.iter_modules(__path__))


def _declarado() -> str:
    """Idioma declarado pelo app, ou o do ambiente se o app não está no path."""
    try:
        from app.config import APP as _cfg
    except ImportError:
        return os.environ.get('AJSYSTEM_LOCALE') or 'pt'
    return _cfg.get('locale') or 'pt'


#: Idioma ativo. Resolvido na importação e congelado daí em diante.
LOCALE = _declarado()

_erro = f"locale={LOCALE!r} sem catálogo em ajsystem/locales/. " \
        f"Disponíveis: {', '.join(disponiveis()) or '(nenhum)'}."

if LOCALE == 'en':
    _catalogo = importlib.import_module(f'{__name__}.en')
else:
    if LOCALE not in disponiveis():
        raise ValueError(_erro)
    _catalogo = importlib.import_module(f'{__name__}.{LOCALE}')

# Reexporta as constantes do catálogo como atributos deste módulo. Sem isso o
# re-expresso seria apenas `_catalogo.SAVE`, e o ponto do desenho é o consumidor
# escrever `i18n.SAVE`.
globals().update({n: v for n, v in vars(_catalogo).items()
                  if not n.startswith('_') and isinstance(v, str)})


def para_jinja() -> dict:
    """Globals do Jinja: um único `i18n` por template, não uma constante solta.

    Injetar os ~100 nomes direto no `jinja_env.globals` poluiria o namespace do
    template e poderia sombrear uma variável de contexto. `{{ i18n.SAVE }}` é
    explícito sobre a origem do texto.
    """
    return {'i18n': _catalogo}


def herdar_catalogo(globals_):
    """Copia as constantes do catálogo ativo para o namespace de um módulo.

    É o "superset" do host: o módulo que acrescenta o texto de domínio do app
    começa herdando o do framework e declara o dele em seguida:

        from ajsystem.locales import herdar_catalogo
        herdar_catalogo(globals())
        CART_TITLE = 'Meu Orçamento'

    O laço (e a regra de filtro) mora aqui, no motor, para o host não duplicar
    a rotina. O que é copiado é exatamente o que `ajsystem.locales` reexporta
    do catálogo ativo — constantes do framework, sem `LOCALE` (que fica no
    namespace do próprio framework) e sem functions/imports.
    """
    for nome, valor in vars(_catalogo).items():
        if not nome.startswith('_') and isinstance(valor, str):
            globals_[nome] = valor
