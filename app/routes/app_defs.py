SITE = {
    'url_prefix': '/',
    'menus': {
        'Sobre':     {'endpoint': 'site.sobre',           'icon': 'bi-info-circle'},
        'Produtos':  {'endpoint': 'site_vitrine.listar',  'icon': 'bi-gift'},
        'Orçamento': {'endpoint': 'site_orcamento.lista', 'icon': 'bi-file-text'},
        'Contato':   {'endpoint': 'site.contato',         'icon': 'bi-whatsapp'},
    },
}

SYS = {
    'url_prefix': '/',
    'menus': {
        'Cadastro': {
            'icon': 'bi-journal',
            'submenus': {
                'Categorias': {'endpoint': 'categories.list', 'icon': 'bi-journal'},
                'Insumos':    {'endpoint': 'insumos.list',    'icon': 'bi-box-seam'},
                'Produtos':   {'endpoint': 'products.list',   'icon': 'bi-gift'},
                'Contas':     {'endpoint': 'contas.list',     'icon': 'bi-people'},
                'Operações':  {'endpoint': 'operacoes.list',  'icon': 'bi-tags'},
                'Carteiras':  {'endpoint': 'carteira.list',   'icon': 'bi-wallet2'},
            },
        },
        'Comercial': {
            'icon': 'bi-cart',
            'submenus': {
                'Orçamentos': {'endpoint': 'orcamentos.list', 'icon': 'bi-file-text'},
                'Pedidos':    {'endpoint': 'orders.list',     'icon': 'bi-cart'},
                'Compras':    {'endpoint': 'compras.list',    'icon': 'bi-bag'},
            },
        },
        'Produção': {
            'endpoint': 'producao.list',
            'icon': 'bi-gear',
        },
        'Financeiro': {
            'icon': 'bi-cash-stack',
            'submenus': {
                'Recursos':         {'endpoint': 'recursos.list',                'icon': 'bi-piggy-bank'},
                'Contas a Receber': {'endpoint': 'transacao.receber_list',       'icon': 'bi-arrow-down-circle'},
                'Contas a Pagar':   {'endpoint': 'transacao.pagar_list',         'icon': 'bi-arrow-up-circle'},
                'Recebimentos':     {'endpoint': 'movimentos.recebimentos_list', 'icon': 'bi-cash'},
                'Pagamentos':       {'endpoint': 'movimentos.pagamentos_list',   'icon': 'bi-credit-card'},
                'Transferências':   {'endpoint': 'transferencias.trf_list',      'icon': 'bi-arrow-left-right'},
            },
        },
    },
}

ADMIN = {
    'role': 'supervisor',
    'menus': {},
}

APP = {
    'nome': 'AlgoDoce',
    'logo': 'icons/Logo.png',
    'versao': 'v1.25.3-1',
    'cor': {
        'fundo': '#e91e63',
        'texto': '#FFF',
    },
    'barras': {
        'altura': 5,
 
    },
    'site': SITE,
    'system': SYS,
    'admin': ADMIN,
}
