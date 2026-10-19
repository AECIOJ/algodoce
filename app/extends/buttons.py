"""Botões que pertencem ao app — não ao framework.

O framework entrega o catálogo genérico (`ajsystem.defs.buttons.BUTTON_TYPES`) e
as factories de relatório (`BTN_PRINT`/`BTN_SEND`). O que é ação/aparência
deste app fica aqui, em `Buttons` — o mesmo papel que o `Schema` de um módulo tem
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

O que é de UMA rota não mora aqui: a rota declara o `Buttons` dela, no mesmo
papel que o `Schema` dela tem sobre os campos, e o `form.buttons` vira só uma
lista de nomes. Aqui fica o que **volta em dois ou mais forms** — a regra de
visibilidade compartilhada entre telas entra no catálogo, não na rota que a
descobriu primeiro.
"""

def _sem_financeiro(instance):
    return instance is not None and not instance.transacao and not instance.movto


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
    'gerar_financeiro': {'type': 'generate', 'icon': 'currency-dollar',
                         'variant': 'outline'},
    'gerar_previsoes':  {'type': 'generate', 'icon': 'arrow-path'},
    'zerar_previsoes':  {'type': 'clear', 'label': 'Zerar', 'icon': 'xcircle',
                         'color': 'warning', 'variant': 'solid'},
    # Ação de app sem CRUD, fluxo ou estado que corresponda: nasce do genérico
    # neutro `execute`.
    'precos_zerados':   {'type': 'execute', 'label': 'Preços zerados',
                         'icon': 'currency-dollar'},
    'lancar_transferencia': {'type': 'execute', 'label': 'Lançar',
                             'icon': 'arrow-right', 'color': 'success'},
}
