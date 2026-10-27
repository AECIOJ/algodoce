from ajsystem.defs.report import *
from ajsystem.defs.constants import START, FINISH, NEVER, ROW, INLINE
QRECEBER = {
    'select': [
        {'cliente': 'conta.nome'},
        'vencimento',
        # {'fatura': 'transacao.fatura'},
        'documento',
        'recurso_id',
        'previsto',
        'realizado',
        'variacao',
        'saldo',
    ],
    'from': 'Previsao',
    # 'order': [1, 2],
}

RECEBER = {
    'label': 'Contas a Receber',
    'header': [
        LOGO(),
        TITLE(),
    ],
    'body': {
        'source': QRECEBER,
        'table': {
            # 'groups': {
            #     'cliente': {
            #         'text': 'Cliente: {cliente}',
            #         'on_start': {'lf': -1},
            #         'on_finish': {'lf': 1},
            #         'totals': True,
            #     },
            # },
            'columns': {
                # 'cliente': {},
                'vencimento': {},
                # 'fatura': {},
                'documento': {},
                'recurso_id': {},
                'previsto': {'agg': 'sum'},
                'realizado': {'agg': 'sum'},
                'variacao': {'agg': 'sum'},
                'saldo': {'agg': 'sum'},
            },
            'totals': {'label': 'Subtotal', 'align': 'R', 'span': 4},
        },
    },
    'footer': True,
}
