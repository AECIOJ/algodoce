import re

from flask import flash, request

from ajsystem.core.extensions import db
from ajsystem.core.formats import parse_brl
from ajsystem.defs.constants import TODAY

from app.extends.constants import ENTRADA, SAIDA
from app.extends.masks import MVALOR
from app.models.movimento import Movimento
from app.models.recurso import Recurso

from app.models.transferencia import Transferencia  # noqa: F401


_LINHA = re.compile(r'^child_movtos_(n-?\d+|\d+)_(tipo|valor|recurso_id)$')


def _lancamentos_postados():

    linhas = {}
    for key, raw in request.form.items():
        m = _LINHA.match(key)
        if m:
            linhas.setdefault(m.group(1), {})[m.group(2)] = raw
    return [{'tipo': v.get('tipo'),
             'valor': parse_brl(v.get('valor')),
             'recurso_id': int(v['recurso_id']) if (v.get('recurso_id') or '').isdigit() else None}
            for v in linhas.values()]


def _erro_mesmo_recurso(lancamentos):
    """A transferência move valor **entre recursos**: entrada e saída no mesmo
    recurso se anulam e nenhum saldo muda. `None` fica de fora porque o
    `pre_save` roda antes da validação de `required` (do_form.py:591), então
    recurso em branco ainda chega aqui — e quem reclama disso é o `required`."""
    entradas = {l['recurso_id'] for l in lancamentos if l['tipo'] == ENTRADA}
    saidas = {l['recurso_id'] for l in lancamentos if l['tipo'] == SAIDA}
    comum = (entradas & saidas) - {None}
    if not comum:
        return None
    nomes = [r.nome for r in Recurso.query.filter(Recurso.id.in_(comum)).all()]
    return ('Entrada e saída no mesmo recurso não transferem nada '
            f'({", ".join(nomes) or ", ".join(str(i) for i in sorted(comum))}).')


def _fechar_em_zero(instance, request, is_new):
    """`pre_save`: a transferência só grava com as entradas e saídas fechando
    em zero, e de recursos diferentes. Sem linhas é um rascunho — `Editando`."""
    lancamentos = _lancamentos_postados()
    if not lancamentos:
        return True
    erro = instance.erro_lancamentos([(l['tipo'], l['valor'])
                                       for l in lancamentos])
    if erro:
        flash(erro, 'warning')
        return False
    erro = _erro_mesmo_recurso(lancamentos)
    if erro:
        flash(erro, 'warning')
        return False


def _pos_save(instance, changed, old_vals):
    """`post_save`: status derivado + o que a linha **herda** do cabeçalho.

    A célula `data` das duas sessões é somente leitura e nasce preenchida pelo
    `on_new` (data da transferência no clique em Adicionar) — mas o `on_new` só
    age na linha nova: linha já existente continuaria com a data antiga se a
    data do cabeçalho mudasse depois. Aqui as duas pontas se fecham.

    `conta_id` também é herdado: transferência move valor entre recursos, não
    tem cliente nem fornecedor — a coluna é `nullable` e os lançamentos antigos
    ainda guardam o `conta` de quando o modelo era outro.
    """
    instance.status = instance.calc_status()
    for m in Movimento.query.filter_by(transferencia_id=instance.id).all():
        if m.data != instance.data:
            m.data = instance.data
        if m.conta_id is not None:
            m.conta_id = None
    db.session.commit()



NOVO_REGISTRO = {'replaces': {'data': 'data', 'documento': 'documento',
                               'historico': 'historico'}}


Schema = {
    'Transferencia': {
        'id': {'label': 'Transfer'},
        'data': {'default': TODAY},
        'total': {'calc': lambda row: row.total, 'mask': MVALOR},
        'status': {'calc': {'type': 'call', 'source': 'calc_status',
                            'diff': 'Aviso de Inconsistência: Status registrado desta transferência difere do status calculado.'},
                   'tag': {'colors': {0: 'neutral', 1: 'warning', 9: 'success'}}},
    },
    'Movimento': {
        'tipo': {},
        'data': {'default': TODAY, 'readonly': True},
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'conta_id': {},
        'previsao_id': {},
        'operacao_id': {},
        'variacao': {},
        'pedido_id': {},
        'compra_id': {},
    },
    'MEMORY': {'valor': {'type': 'NUM', 'label': 'Valor', 'width': 12, 'mask': MVALOR},
        # Campo `memory` não tem coluna no pai, então não há FK para o motor
        # inferir: o alvo vem do `lookup.model`, que é NOME de entidade
        # (o mesmo que `register_model` registrou), não a classe.
        'de': {'type': 'FK', 'label': 'De', 'width': 15,
               'lookup': {'model': 'Recurso', 'display': 'nome', 'fields': ['nome']}},
        'para': {'type': 'FK', 'label': 'Para', 'width': 15,
                 'lookup': {'model': 'Recurso', 'display': 'nome', 'fields': ['nome']}},
    },
}

Page = {
    'label': 'Transferência',
    'type': 'crud',
    'props': {
        'scripts': ['transferencias'],
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Transferencia',
            'master': 'Movimento',
            'line': ['id'],
            'hidden': ['documento', 'conta_id', 'previsao_id',
                       'operacao_id', 'variacao', 'pedido_id', 'compra_id'],
            'card': 'Transferencia',
            'order': ['data', 'id'],
        },
        'filter': {'types': {'checklist': 'status'}, 'hidden': ['conta_id'],
                   'default': {'data': {'preset': 'mes_ano'}}},
        'form': {
            'max_width': 115,
            'fields': {'Transferencia': ['data', 'documento', 'total', 'status',
                                         'historico'],
                       'MEMORY': ['valor', 'de', 'para']},
            # `id` é a chave primária, que a regra de motor esconderia: aqui ele
            # é o nº da transferência, que abre o pai, então é citado em `body`
            # e a declaração ganha da regra.
            'positions': {'bar': ['status']},
            'buttons': [
                {'lancar_transferencia': {'position': 'after',
                                          'action': 'transferenciaLancar',
                                          'enabled': ['valor', 'de', 'para']}},
            ],
            'pre_save': _fechar_em_zero,
            'post_save': _pos_save,
            'sessions': {
                # As duas sessões apontam para o mesmo relationship, então quem
                # as separa é o `defaults` (5.5.2) — e o `id` da linha é a chave
                # primária do filho, escondido pela mesma regra do mestre.
                'Entradas': {'table': {'columns': ['Movimento']},
                             'hidden': ['tipo', 'conta_id', 'previsao_id',
                                        'operacao_id', 'variacao', 'pedido_id',
                                        'compra_id'],
                             'defaults': {'tipo': ENTRADA},
                             'on_new': NOVO_REGISTRO},
                'Saídas': {'table': {'columns': ['Movimento']},
                           'hidden': ['tipo', 'conta_id', 'previsao_id',
                                      'operacao_id', 'variacao', 'pedido_id',
                                      'compra_id'],
                           'defaults': {'tipo': SAIDA},
                           'on_new': NOVO_REGISTRO},
            },
        },
    },
}
