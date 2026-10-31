from ajsystem.defs.report import *
from ajsystem.defs.constants import POS_INLINE
QRECEBER = {
    'select': [
        {'previsao': 'id'},
        {'cliente': 'conta.nome'},
        'vencimento',
        {'fatura': 'transacao.fatura'},
        'documento',
        {'recurso': 'recurso.nome'},
        'previsto',
        'realizado',
        'variacao',
        'saldo',
        {'conta': 'transacao.conta_id'}
    ],
    'from': 'Previsao',
}

RECEBER = {
    'label': 'Contas a Receber',
    'header': [
        LOGO(),
        TITLE(),
    ],
    'body': {
        'source': QRECEBER,
        'order': [1, 3],
        'table': {
            'columns': {
                'cliente': {
                    'group': '*',
                    'pos': POS_INLINE,
                    'text': '{conta}. {cliente}',
                    'on_start': {'lf': -1},
                    'on_finish': {'lf': 1},
                    'totals': { 'align': 'R', 'span': 4},
                },
                'previsao': {},
                'vencimento': {},
                'fatura': {},
                'documento': {},
                'recurso': {},
                'previsto': {'agg': 'sum'},
                'realizado': {'agg': 'sum'},
                'variacao': {'agg': 'sum'},
                'saldo': {'agg': 'sum'},
            },
            'totals': {'align': 'R', 'span': 4},
        },
    },
    'footer': True,
}
