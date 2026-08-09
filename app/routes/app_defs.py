# ── Tema ── Cores em 4 categorias (design tokens → vars DaisyUI/CSS em components/theme.html)
# 1. marca:  Cores de Marca (Primary/Brand) — CTAs, links importantes, destaque da marca
# 2. neutras: Surfaces/Backgrounds/Textos — fundos, cards, bordas, textos
# 3. feedback: Estado semântico — sucesso/alerta/erro/info
# 4. apoio:   Destaque/Accent — complementa a marca, chama atenção sem erro/sucesso
# Coleção de temas — o motor resolve a partir de APP['tema'] (nome da chave)
Temas = {
    'algodoce': {
        'base': 'algodoce',
        'rotulo': 'AlgoDoce',
        'marca': {
            'primary': '#26A69A',
            'primary-content': '#FFFFFF',
            'secondary': '#E91E63',
            'secondary-content': '#FFFFFF',
        },
        'neutras': {
            'base-100': '#f5f5f5',
            'base-200': '#e0e0e0',
            'base-300': '#bdbdbd',
            'base-content': '#212121',
            'neutral': '#37474F',
            'neutral-content': '#FFFFFF',
        },
        'feedback': {
            'success': '#43A047',
            'success-content': '#FFFFFF',
            'warning': '#FB8C00',
            'warning-content': '#000000',
            'error': '#E53935',
            'error-content': '#FFFFFF',
            'info': '#0288D1',
            'info-content': '#FFFFFF',
        },
        'apoio': {
            'accent': '#FFB300',
            'accent-content': '#000000',
        },
        'barras': {
            'altura': 5,
            'menu':    {'fundo': '#e91e63', 'texto': '#FFFFFF'},
            'submenu': {'fundo': '#FFFFFF', 'texto': '#e91e63'},
            'form':    {'fundo': '#FFFFFF', 'texto': '#e91e63'},
            'rodape':  {'fundo': '#FFFFFF', 'texto': '#e91e63'},
        },
    },
}

SITE = {
    'url_prefix': '/',
    'home': 'site_vitrine.listar',
    'menus': {
        'Sobre':     {'endpoint': 'site.sobre',           'icon': 'bi-info-circle'},
        'Produtos':  {'endpoint': 'site_vitrine.listar',  'icon': 'bi-gift'},
        'Orçamento': {'endpoint': 'site_orcamento.lista', 'icon': 'bi-file-text'},
        'Contato':   {'endpoint': 'site.contato',         'icon': 'bi-whatsapp'},
    },
}

SYS = {
    'url_prefix': '/',
    'home': 'categorias.list',
    'menus': {
        'Cadastro': {
            'icon': 'bi-journal',
            'submenus': {
                'Categorias': {'icon': 'bi-journal'},
                'Insumos':    {'icon': 'bi-box-seam'},
                'Produtos':   {'icon': 'bi-gift'},
                'Contas':     {'icon': 'bi-people'},
                'Operações':  {'icon': 'bi-tags'},
                'Carteiras':  {'icon': 'bi-wallet2'},
            },
        },
        'Comercial': {
            'icon': 'bi-cart',
            'submenus': {
                'Orçamentos': {'endpoint': 'orcamentos.list', 'icon': 'bi-file-text'},
                'Pedidos':    {'endpoint': 'pedidos.list',    'icon': 'bi-cart'},
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
    'home': 'seguranca.painel',
    'menus': {},
}

APP = {
    'nome': 'AlgoDoce',
    'logo': 'icons/Logo.png',
    'versao': 'v1.25.3-1',
    'tema': 'algodoce',
    'site': SITE,
    'system': SYS,
    'admin': ADMIN,
}
