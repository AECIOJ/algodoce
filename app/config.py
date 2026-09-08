# ── Tema ── Fonte ÚNICA de cores do app (design tokens → tema DaisyUI + vars CSS)
# 1. PALETA: constantes de cor — fonte única dos valores hex (sem repetição).
# 2. marca:   Cores de Marca (primary/secondary) — CTAs, links, destaque da marca
# 3. neutras: Superfícies/Backgrounds/Textos — fundos, cards, bordas, textos
# 4. feedback: Estado semântico — success/warning/error/info (set fixo, não derivado)
# 5. apoio:   Destaque/Accent — complementa a marca
# 6. barras:  Chrome do app — consumido em runtime por components/theme.html (vars --bar-*)
#
# Os grupos marca/neutras/feedback/apoio alimentam o tema DaisyUI COMPILADO:
#   app/ajsystem/core/do_themes.py (do framework) gera tailwind.daisyui.json
#   (usado por tailwind.config.js) → `npm run build:css`. Alterou uma cor?
#   Mude AQUI e rode `npm run build:css`. barras propaga sem rebuild (runtime).
#
# Tokens derivados automaticamente (do_themes.py, quando ausentes):
#   base-200/base-300/neutral e todos os *-content (contraste). Declare apenas
#   o que quiser fixar/sobrescrever — o resto do tema se completa sozinho.

# ═══ PALETA — fonte única de cores ═══
_VERDE   = '#26A69A'   # primary       (verde-menta)
_ROSA    = '#E91E63'   # secondary     (rosa)
_FUNDO   = '#f5f5f5'   # base-100      (superfície do app)
_CREME   = '#F5EEE1'   # chrome/barras (submenu/form/lista)
_TEXTO   = '#212121'   # base-content  (texto principal)
_AMARELO = '#FFB300'   # accent        (destaque)
_OK      = '#43A047'   # success       (semântica — fixa)
_AVISO   = '#FB8C00'   # warning
_ERRO    = '#E53935'   # error
_INFO    = '#0288D1'   # info
_BRANCO  = '#FFFFFF'
_PRETO   = '#000000'

Temas = {
    'algodoce': {
        'base': 'algodoce',
        'rotulo': 'AlgoDoce',
        'marca': {
            'primary': _VERDE,
            'secondary': _ROSA,
        },
        'neutras': {
            'base-100': _FUNDO,
            'base-content': _TEXTO,
        },
        'feedback': {
            'success': _OK,
            'warning': _AVISO,
            'error': _ERRO,
            'info': _INFO,
        },
        'apoio': {
            'accent': _AMARELO,
        },
        'barras': {
            'altura': 5,
            'menu':    {'fundo': _ROSA,   'texto': _BRANCO},
            'submenu': {'fundo': _CREME,  'texto': _ROSA},
            'form':    {'fundo': _CREME,  'texto': _ROSA},
            'lista':   {'fundo': _CREME,  'texto': _ROSA},
            'rodape':  {'fundo': _FUNDO,  'texto': _ROSA},
        },
        'modal': {
            'tons': {
                'error':   {'fundo': _ERRO,   'texto': _BRANCO},
                'warning': {'fundo': _AVISO,  'texto': _PRETO},
                'info':    {'fundo': _INFO,   'texto': _BRANCO},
                'primary': {'fundo': _VERDE,  'texto': _BRANCO},
                'success': {'fundo': _OK,     'texto': _BRANCO},
            },
            'tipos': {
                'erro': 'error', 'alerta': 'warning', 'ajuda': 'info',
                'confirma': 'primary', 'busca': 'primary', 'sair': 'warning',
            },
        },
    },
}

SITE = {
    'type': 'public',
    'default_path': 'produtos',
    'triggers': {
        'click':     {'target': 'logo', 'action': 'system'},
        'click_dbl': {'target': 'logo', 'action': 'admin'},
    },
    'layout': {
        'header': {
            'logo': {'rows': 4, 'align': 'center'},
            'title': {
                'text': 'O doce sabor do seu evento!',
                'align': 'center',
                'color': 'var(--rosa)',
            },
        },
        'footer': {'user': False},
    },
    'menus': {
        'Sobre':     {'icon': 'bi-info-circle'},
        'Produtos':  {'icon': 'bi-gift'},
        'Orçamento': {'icon': 'bi-file-text'},
        'Contato':   {'icon': 'bi-whatsapp'},
    },
}

SYS = {
    'type': 'system',
    'default_path': 'cadastro/categorias',
    'triggers': {
        'click':     {'target': 'logo', 'action': 'qr'},
        'click_dbl': {'target': 'logo', 'action': 'admin'},
    },
    'layout': {
        'header': {
            'logo': {'rows': 4, 'align': 'center'},
            'title': {
                'text': 'app_title',
                'align': 'center',
            },
        },
        'footer': {'user': True},
    },
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
                'Pedidos':    {'icon': 'bi-cart'},
                'Compras':    {'icon': 'bi-bag'},
            },
        },
        # 'Produção': {
        #     'icon': 'bi-gear',
        # },
        'Financeiro': {
            'icon': 'bi-cash-stack',
            'submenus': {
                'Recursos':         {'icon': 'bi-piggy-bank'},
                'Contas a Receber': {'icon': 'bi-arrow-down-circle', 'page': 'receber'},
                'Contas a Pagar': {'icon': 'bi-arrow-up-circle', 'page': 'pagar'},
                'Recebimentos':     {'icon': 'bi-cash'},
                'Pagamentos':       {'icon': 'bi-credit-card'},
                'Transferências':   {'icon': 'bi-arrow-left-right'},
            },
        },
    },
}

ADMIN = {
    'type': 'admin',
    'default_path': 'seguranca.painel',
    'triggers': {
        'click': {'target': 'logo', 'action': 'system'},
    },
    'menus': {},
}

APP = {
    'name': 'AlgoDoce',
    'title': 'Sistema Gerenciador de Doceria',
    'logo': 'icons/Logo.png',
    'version': 'v1.25.3-1',
    'tema': 'algodoce',
    'modules': [SITE, SYS, ADMIN],
}
