from ajsystem.defs.report import *

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
        'table': {
            'pre': {
                'cliente': {
                    'group': '*',
                    'text': '{conta}. {cliente}',
                    'on_start': {'lf': -1},
                    'on_finish': {'lf': 1},
                    'totals': {'align': 'R'},
                },
            },
            'cols': {
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
            'totals': {'align': 'R'},
            'syn': {
                'cols': {
                    'cliente': {
                        'group': '*',
                        'text': '{conta}. {cliente}',
                        'width': 40
                    },
                    'previsto': {'agg': 'sum'},
                    'realizado': {'agg': 'sum'},
                    'variacao': {'agg': 'sum'},
                    'saldo': {'agg': 'sum'},
                },
                'totals': {'align': 'R'},
            },
        },
        'chart': {
            'title': 'Saldo por Cliente',
            'type': 'bar',
            'cat': {'cliente': {'order': 'desc', 'limit': 10}},
            'value': {
                'previsto':  {'color': '#0d6efd'},
                'realizado': {'color': '#198754'},
                'saldo':     {'color': '#dc3545'},
            },
            'stack': {'total': ['previsto', 'realizado', 'saldo']},
            'label': {
                'cat': 'Cliente',
                'value': 'Saldo (R$)',
                'val': True,
            },
            'options': {'legend': 'bottom'},
            'syn': {
                'type': 'pie',
                'value': {
                    'previsto': {},
                    'realizado': {},
                    'variacao': {},
                    'saldo': {}
                    },
                'label': {
                    'cat': True,
                    'val': True,
                    'perc': True,
                    'pos': 'O',
                },
                'options': {
                    'legend': False,
                    'shadow': (5, -3), 
                    'explode': 'realizado'
                },
            },
        },
    },
    'footer': True,
}
