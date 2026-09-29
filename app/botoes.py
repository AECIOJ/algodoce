"""Botões que pertencem ao app — não ao framework.

O framework entrega os presets genéricos (`ajsystem.defs.buttons`) e as
factories de relatório (`BTN_PRINT`/`BTN_SEND`). O que é ação/aparência do
Algodoce fica aqui, estendendo um preset com `replace` em vez de copiar o dict
inteiro — assim uma mudança de aparência no framework chega aqui também.

Nome em português (é o app) e texto em português também: literal é o idioma do
app. Se um botão quiser o texto do framework, é `label=BTN_SAVE` ou
`i18n.<NOME>` (`ajsystem.locales` — o catálogo do framework já inclui a storefront).

Os botões de um form que se repetem em vários lugares (mesma regra de
`visible`, mesmo form) moram aqui. Botão de uso único continua no route.
"""
from dataclasses import replace

from ajsystem.defs.buttons import BTN_CONFIRM, BTN_RENEW, BTN_SEND

from app.reports.orcamentos import ORCAMENTO


# ── Form de Orçamento ───────────────────────────────────────────────────────
# Regra do domínio: só um orçamento avulso, ainda não aprovado, pode ser
# enviado/aprovado; renovar só faz sentido depois de expirado (status 7).
def _editavel(q):
    return q is not None and q.pedido_id is None and q.status < 7


def _expirado(q):
    return q is not None and q.pedido_id is None and q.status == 7


# `BTN_SEND` já vem com render/into/guard do relatório; aqui só a posição e a
# regra de visibilidade. Textos 'Enviar'/'Aprovar'/'Renovar' são do app.
BTN_ORC_ENV = replace(BTN_SEND(ORCAMENTO), position='top_right', visible=_editavel)
# `enabled=['total']`: só habilita com total > 0. `Orcamento.total` é property
# (soma dos itens) e `_filled` trata número ≠ 0 como preenchido — mesma regra
# roda no servidor (`enabled_ok`) e no JS (`itEnabledEval`). O botão fica na
# sessão Financeiro, junto do campo `total`, porque é ele que o habilita.
BTN_ORC_APROVAR = replace(BTN_CONFIRM, label='Aprovar', icon='check',
                          url='orcamentos.aprovar', position='right',
                          enabled=['total'], visible=_editavel)
# Cor diferente do `BTN_RENEW` do framework (que é info/cheio) — de propósito, é
# a ação secundária do form.
BTN_ORC_RENOVAR = replace(BTN_RENEW, color='secondary', outline=True,
                          url='orcamentos.renovar', method='POST',
                          position='top_right', visible=_expirado)
