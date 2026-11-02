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
                'title': {},
                'cols': {
                    'cliente': {
                        'group': '*',
                        'text': '{conta}. {cliente}',
                        'on_start': {'lf': -1},
                        'on_finish': {'lf': 1},
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
    },
    'footer': True,
}
