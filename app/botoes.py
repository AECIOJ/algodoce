"""Botões que pertencem ao app — não ao framework.

O framework entrega o catálogo genérico (`ajsystem.defs.buttons.BUTTON_TYPES`) e
as factories de relatório (`BTN_PRINT`/`BTN_SEND`). O que é ação/aparência do
Algodoce fica aqui, em `Buttons` — o mesmo papel que o `Schema` de um módulo tem
sobre a entity: o catálogo base resolve a chave, e o app descreve o que diverge.

    # framework
    BUTTON_TYPES = {'generate': {'label': 'Gerar', 'color': 'success', 'variant': 'solid'}, …}

    # app — `type` diz de qual genérico diverge
    Buttons = {'gerar_financeiro': {'type': 'generate', 'icon': 'currency-dollar'}}

    # route — só o que depende do form e do registro
    'buttons': [{'gerar_financeiro': {'url': 'pedidos.gerar_financeiro', 'method': 'POST'}}]

O merge é raso em cada camada e vai do framework para o app e do app para a spec,
então cada botão declara só o que muda. Nenhuma camada muta o catálogo.

Nome em português (é o app) e texto em português também: literal é o idioma do
app. Se um botão quiser o texto do framework, é `i18n.<NOME>` (`ajsystem.locales`).

Os botões de um form que se repetem em vários lugares (mesma regra de `visible`,
mesmo form) moram aqui. Botão de uso único continua no route.
"""
from dataclasses import replace

from ajsystem.defs.buttons import BTN_SEND

from app.reports.orcamentos import ORCAMENTO


# ── Regras de visibilidade do domínio ────────────────────────────────────────
# `_sem_financeiro` mora aqui porque é a MESMA regra nos dois forms (compras e
# pedidos) — antes ela estava duplicada byte a byte em `compras.py` e `pedidos.py`,
# contra a regra que este arquivo já enunciava.
def _sem_financeiro(instance):
    return instance is not None and not instance.transacao and not instance.movto


def _editavel(q):
    return q is not None and q.pedido_id is None and q.status < 7


def _expirado(q):
    return q is not None and q.pedido_id is None and q.status == 7


# ── Aparência que é do app ───────────────────────────────────────────────────
# Só o que diverge de um tipo genérico do framework. O `type` declara de qual:
#
#     BUTTON_TYPES[tipo]  <  esta entrada  <  a spec do ponto de uso
#
# Sem `type`, a base seria o tipo de mesmo nome — que é o caso de quem
# sobrescreve um genérico. Com `type`, o app nomeia um botão seu e declara só a
# diferença, sem ter de repetir `label`/`color` de um tipo que ele não está
# inventando. `enabled`/`carry`/`url` NÃO moram aqui: dependem do form e do
# registro, e ficam no ponto de uso.
Buttons = {
    # 'Gerar' do financeiro: é o tipo `generate` com outro ícone e sem o filled,
    # porque na barra do form ele divide espaço com o `Enviar`.
    'gerar_financeiro': {'type': 'generate', 'icon': 'currency-dollar',
                         'variant': 'outline'},
    # 'Gerar' das previsões: o `generate` inteiro, só com o ícone do refazer.
    'gerar_previsoes':  {'type': 'generate', 'icon': 'arrow-path'},
    # 'Zerar': o `clear` com a palavra e a cor do app. `variant: 'solid'`
    # sobrescreve o outline do `clear` — sem ele o botão mudaria de aparência.
    'zerar_previsoes':  {'type': 'clear', 'label': 'Zerar', 'icon': 'xcircle',
                         'color': 'warning', 'variant': 'solid'},
    # Ação de app sem CRUD, fluxo ou estado que corresponda: nasce do genérico
    # neutro `execute`.
    'precos_zerados':   {'type': 'execute', 'label': 'Preços zerados',
                         'icon': 'currency-dollar'},
}


# ── Form de Orçamento ───────────────────────────────────────────────────────
# Regra do domínio: só um orçamento avulso, ainda não aprovado, pode ser
# enviado/aprovado; renovar só faz sentido depois de expirado (status 7).
# Textos 'Enviar'/'Aprovar'/'Renovar' são do app.
#
# `BTN_SEND` já vem com render/into/guard do relatório; aqui só a posição e a
# regra de visibilidade.
BTN_ORC_ENV = replace(BTN_SEND(ORCAMENTO), position='top_right', visible=_editavel)

# `enabled=['total']`: só habilita com total > 0. `Orcamento.total` é property
# (soma dos itens) e `_filled` trata número ≠ 0 como preenchido — mesma regra
# roda no servidor (`enabled_ok`) e no JS (`itEnabledEval`). O botão fica na
# sessão Financeiro, junto do campo `total`, porque é ele que o habilita.
# O tipo `approve` já é "Aprovar" com `check` verde — antes o botão sobrescrevia
# `label` e `icon` à mão para chegar no mesmo lugar.
BTN_ORC_APROVAR = {'approve': {'url': 'orcamentos.aprovar', 'position': 'right',
                               'enabled': ['total'], 'visible': _editavel}}

# Cor diferente do tipo `renew` do framework (que é info/cheio) — de propósito, é
# a ação secundária do form.
BTN_ORC_RENOVAR = {'renew': {'color': 'secondary', 'variant': 'outline',
                             'url': 'orcamentos.renovar', 'method': 'POST',
                             'position': 'top_right', 'visible': _expirado}}
