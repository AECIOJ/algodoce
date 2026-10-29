from ajsystem.defs.report import *
QRECEBER = {
    'select': [
        {'cliente': 'conta.nome'},
        'vencimento',
        {'previsao': 'id'},
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
        'order': [1, 2],
        'table': {
            'groups': {
                'cliente': {
                    'text': '{conta}. {cliente}',
                    'on_start': {'lf': -1},
                    'on_finish': {'lf': 1},
                    'totals': { 'align': 'R', 'span': 4},
                },
            },
            'columns': {
                'previsao': {},
                'vencimento': {},
                'fatura': {},
                'documento': {},
                'recurso_id': {},
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
