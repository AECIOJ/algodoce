import os
import threading
import time
from datetime import timedelta
from flask import Flask
from ajsystem.core.config import Config
from ajsystem.core.extensions import db, migrate, login_manager
from ajsystem.tunnel import provider as tunnel_provider
from flask_migrate import upgrade
import sqlalchemy as sa


def _fetch_tunnel_url():
    tunnel_provider.fetch_tunnel_url()


def get_tunnel_url(force=False):
    return tunnel_provider.get_tunnel_url(force=force)


def _bg_fetch_tunnel():
    time.sleep(3)
    _fetch_tunnel_url()


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    threading.Thread(target=_bg_fetch_tunnel, daemon=True).start()

    db.init_app(app)
    migrate.init_app(
        app,
        db,
        directory=os.path.join(os.path.dirname(__file__), "migrations"),
    )

    from app.models.usuario import Usuario

    @app.after_request
    def no_static_cache(response):
        from flask import request
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store, max-age=0'
        return response

    with app.app_context():
        # Import all models FIRST so mapper init resolves correctly
        from app.models import conta as conta_model, produto, insumo, produto_insumo, conversao_unidade, pedido, categoria, orcamento, operacao, transacao, previsao  # noqa
        from app.models.evento import Evento  # noqa
        from app.models.orcamento_item import OrcamentoItem  # noqa
        from app.models.compra import Compra  # noqa
        from app.models.compra_item import CompraItem  # noqa
        from app.models.compra_historico import CompraHistorico  # noqa
        from app.models.pedido_item import PedidoItem  # noqa
        from app.models.configuracao import Configuracao  # noqa
        from app.models.producao import Producao  # noqa
        from app.models.producao_insumo import ProducaoInsumo  # noqa
        from app.models.producao_produto import ProducaoProduto  # noqa
        from app.models.recurso import Recurso  # noqa
        from app.models.movimento import Movimento  # noqa
        from app.models.transferencia import Transferencia  # noqa
        from app.models.carteira import Carteira  # noqa

        from app.models.categoria import Categoria
        from app.models.conta import Conta
        from app.models.operacao import Operacao
        from app.models.produto import Produto
        from app.models.insumo import Insumo
        from app.models.orcamento import Orcamento
        from app.models.pedido import Pedido
        from app.models.pedido_item import PedidoItem
        from app.models.previsao import Previsao
        from app.models.produto_insumo import ProdutoInsumo
        from app.models.conversao_unidade import ConversaoUnidade

        from ajsystem.defs.data import register_model

        from ajsystem.core.do_upload import bp as uploads_bp

        app.register_blueprint(uploads_bp)

        from ajsystem import init_app
        init_app(app)

        # Rotinas extras fora do CRUD gerado pelo motor (a lógica vive no
        # arquivo da rota; aqui só a fiação, pois o blueprint já foi registrado).
        from flask_login import login_required
        from app.routes.sys import orcamentos as _mod_orcamentos
        app.add_url_rule('/orcamentos/<int:id>/aprovar', endpoint='orcamentos.aprovar',
                         view_func=login_required(_mod_orcamentos.aprovar),
                         methods=('GET', 'POST'))
        app.add_url_rule('/orcamentos/<int:id>/renovar', endpoint='orcamentos.renovar',
                         view_func=login_required(_mod_orcamentos.renovar),
                         methods=('POST',))
        from app.routes.sys import recebimentos as _mod_recebimentos
        from app.routes.sys import pagamentos as _mod_pagamentos
        app.add_url_rule('/recebimentos/<int:id>/excluir', endpoint='recebimentos.excluir',
                         view_func=login_required(_mod_recebimentos.excluir),
                         methods=('POST',))
        app.add_url_rule('/pagamentos/<int:id>/excluir', endpoint='pagamentos.excluir',
                         view_func=login_required(_mod_pagamentos.excluir),
                         methods=('POST',))

        from ajsystem.core import adapter
        adapter.set_tunnel_url_provider(lambda: get_tunnel_url(force=True))
        from ajsystem.core.content import render_pagina
        adapter.set_markdown_loader(render_pagina)

        register_model('category', Categoria)
        register_model('categoria', Categoria)
        register_model('conta', Conta)
        register_model('operacao', Operacao)
        register_model('product', Produto)
        register_model('produto', Produto)
        register_model('ingredient', Insumo)
        register_model('insumo', Insumo)
        register_model('quote', Orcamento)
        register_model('orcamento', Orcamento)
        register_model('recurso', Recurso)
        register_model('producao', Producao)
        register_model('previsao', Previsao)
        register_model('movto', Movimento)
        register_model('movimento', Movimento)
        register_model('recurso_trf', Transferencia)
        register_model('transferencia', Transferencia)
        register_model('carteira', Carteira)
        register_model('quote_item', OrcamentoItem)
        register_model('orcamento_item', OrcamentoItem)
        register_model('event', Evento)
        register_model('evento', Evento)
        register_model('product_ingredient', ProdutoInsumo)
        register_model('produto_insumo', ProdutoInsumo)
        register_model('unit_conversion', ConversaoUnidade)
        register_model('conversao_unidade', ConversaoUnidade)
        register_model('pedido', Pedido)
        register_model('pedido_item', PedidoItem)

        try:
            upgrade()
        except Exception:
            pass

        Configuracao.ensure_keys()

        for seq, tbl in [('orcamentos_id_seq', 'orcamentos'), ('pedidos_id_seq', 'pedidos'), ('compras_id_seq', 'compras')]:
            try:
                db.session.execute(
                    sa.text(f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {tbl}), 1))")
                )
            except Exception:
                db.session.rollback()
        db.session.commit()

        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        admin = Usuario.query.filter_by(username=admin_username).first()
        if not admin:
            admin = Usuario(username=admin_username)
            db.session.add(admin)
        admin.set_password(admin_password)
        db.session.commit()

    app.jinja_env.policies['json.dumps_kwargs'] = {'sort_keys': False}
    app.jinja_env.finalize = lambda x: 'Sim' if x is True else 'Não' if x is False else '' if x is None else x

    @app.context_processor
    def inject_globals():
        from datetime import date
        from flask import request
        host = request.host.split(':')[0]
        qr_enabled = host in ('localhost', '127.0.0.1', '::1')
        return dict(tunnel_url=get_tunnel_url(), qr_enabled=qr_enabled, timedelta=timedelta, hoje=date.today())

    @app.context_processor
    def inject_versao():
        from flask_login import current_user
        from ajsystem.core.adapter import APP
        usuario = (current_user.username if current_user.is_authenticated else "Visitante").upper()
        return dict(versao=APP.version or '', usuario=usuario)

    def tema_atual():
        from ajsystem.core.adapter import APP, TEMAS
        nome = APP.tema or next(iter(TEMAS))
        if nome not in TEMAS:
            nome = next(iter(TEMAS))
        return nome

    @app.context_processor
    def inject_app_config():
        import json
        from ajsystem.core.adapter import APP, TEMAS
        from ajsystem.core.menu import modulo_atual, menus_para_json
        tema_nome = tema_atual()
        return {
            'APP': APP,
            'TEMA': TEMAS[tema_nome],
            'TEMAS': TEMAS,
            'TEMA_NOME': tema_nome,
            'modulo': modulo_atual(),
            'modulo_menus_json': json.dumps(menus_para_json()),
        }

    @app.context_processor
    def inject_site_categories():
        from app.models.categoria import Categoria
        cats = Categoria.query.filter_by(ativo=True).order_by(Categoria.ordem).all()
        return dict(site_categories=cats)

    @app.context_processor
    def inject_buttons():
        from ajsystem.defs.buttons import (
            BTN_SALVAR, BTN_ENVIAR, BTN_EXCLUIR, BTN_NOVO, BTN_VOLTAR,
            BTN_EDITAR, BTN_CANCELAR, BTN_CONVERTER, BTN_LISTA,
            BTN_IMPRIMIR, BTN_DETALHES, BTN_ADICIONAR, BTN_ADICIONAR_ITEM,
            BTN_FINALIZAR, BTN_ATUALIZAR, BTN_REMOVER, BTN_SIM, BTN_NAO,
            BTN_LIMPAR, BTN_APLICAR, BTN_OK, BTN_SAIR, BTN_RENOVAR,
            BTN_RELATORIO, BTN_GERAR, BTN_CONFIRMAR, BTN_EDITAR_PRODUTO,
            BTN_ENTRAR, BTN_ACESSAR, Button, ConfirmModal,
            CONFIRM_EXCLUIR, CONFIRM_REMOVER_ITEM,
        )
        return dict(
            BTN_SALVAR=BTN_SALVAR, BTN_ENVIAR=BTN_ENVIAR, BTN_EXCLUIR=BTN_EXCLUIR,
            BTN_NOVO=BTN_NOVO, BTN_VOLTAR=BTN_VOLTAR, BTN_EDITAR=BTN_EDITAR,
            BTN_CANCELAR=BTN_CANCELAR, BTN_CONVERTER=BTN_CONVERTER,
            BTN_LISTA=BTN_LISTA, BTN_IMPRIMIR=BTN_IMPRIMIR,
            BTN_DETALHES=BTN_DETALHES, BTN_ADICIONAR=BTN_ADICIONAR,
            BTN_ADICIONAR_ITEM=BTN_ADICIONAR_ITEM, BTN_FINALIZAR=BTN_FINALIZAR,
            BTN_ATUALIZAR=BTN_ATUALIZAR, BTN_REMOVER=BTN_REMOVER,
            BTN_SIM=BTN_SIM, BTN_NAO=BTN_NAO,
            BTN_LIMPAR=BTN_LIMPAR, BTN_APLICAR=BTN_APLICAR,
            BTN_OK=BTN_OK, BTN_SAIR=BTN_SAIR, BTN_RENOVAR=BTN_RENOVAR,
            BTN_RELATORIO=BTN_RELATORIO, BTN_GERAR=BTN_GERAR,
            BTN_CONFIRMAR=BTN_CONFIRMAR, BTN_EDITAR_PRODUTO=BTN_EDITAR_PRODUTO,
            BTN_ENTRAR=BTN_ENTRAR, BTN_ACESSAR=BTN_ACESSAR,
            Button=Button, ConfirmModal=ConfirmModal,
            CONFIRM_EXCLUIR=CONFIRM_EXCLUIR, CONFIRM_REMOVER_ITEM=CONFIRM_REMOVER_ITEM,
        )

    @app.after_request
    def cache_static(response):
        from flask import request as _r
        if _r.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response

    return app
