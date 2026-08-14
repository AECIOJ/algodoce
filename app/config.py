# ── Tema ── Fonte ÚNICA de cores do app (design tokens → tema DaisyUI + vars CSS)
# 1. marca:   Cores de Marca (primary/secondary) — CTAs, links, destaque da marca
# 2. neutras: Superfícies/Backgrounds/Textos — fundos, cards, bordas, textos
# 3. feedback: Estado semântico — success/warning/error/info (mensagens, botões, badges)
# 4. apoio:   Destaque/Accent — complementa a marca
# 5. barras:  Chrome do app — consumido em runtime por components/theme.html (vars --bar-*)
#
# Os grupos marca/neutras/feedback/apoio alimentam o tema DaisyUI COMPILADO:
#   scripts/gen_theme.py gera tailwind.daisyui.json (usado por tailwind.config.js)
#   → `npm run build:css`. Alterou uma cor? Mude AQUI e rode `npm run build:css`.
#   barras propaga sem rebuild (runtime).
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
    'type': 'public',
    'default_path': 'produtos',
    'menus': {
        'Sobre':     {'url': 'site.sobre',           'icon': 'bi-info-circle'},
        'Produtos':  {'url': 'site_vitrine.listar',  'icon': 'bi-gift'},
        'Orçamento': {'url': 'site_orcamento.lista', 'icon': 'bi-file-text'},
        'Contato':   {'url': 'site.contato',         'icon': 'bi-whatsapp'},
    },
}

SYS = {
    'type': 'system',
    'default_path': 'cadastro/categorias',
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
                'Orçamentos': {'icon': 'bi-file-text'},
                'Pedidos':    {'url': 'pedidos.list',    'icon': 'bi-cart'},
                'Compras':    {'url': 'compras.list',    'icon': 'bi-bag'},
            },
        },
        'Produção': {
            'url': 'producao.list',
            'icon': 'bi-gear',
        },
        'Financeiro': {
            'icon': 'bi-cash-stack',
            'submenus': {
                'Recursos':         {'url': 'recursos.list',                'icon': 'bi-piggy-bank'},
                'Contas a Receber': {'url': 'transacao.receber_list',       'icon': 'bi-arrow-down-circle'},
                'Contas a Pagar':   {'url': 'transacao.pagar_list',         'icon': 'bi-arrow-up-circle'},
                'Recebimentos':     {'url': 'movimentos.recebimentos_list', 'icon': 'bi-cash'},
                'Pagamentos':       {'url': 'movimentos.pagamentos_list',   'icon': 'bi-credit-card'},
                'Transferências':   {'url': 'transferencias.trf_list',      'icon': 'bi-arrow-left-right'},
            },
        },
    },
}

ADMIN = {
    'type': 'admin',
    'default_path': 'seguranca.painel',
    'menus': {},
}

APP = {
    'name': 'AlgoDoce',
    'logo': 'icons/Logo.png',
    'version': 'v1.25.3-1',
    'tema': 'algodoce',
    'modules': [SITE, SYS, ADMIN],
}
