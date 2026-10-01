from ajsystem.defs.constants import CONNECTORS
from ajsystem.core.utils import as_options


CARTEIRA_GERAR = {0: "Movimento", 1: "Previsão"}

CARTEIRA_USO = {0: "Pedido", 1: "Pedido e Compra", 2: "Compra"}

FORMINHAS = {0: "Simples (Inclusa)", 1: "Fornecidas pelo Cliente"}

PRODUCAO_ETAPAS = {0: "Preparação", 1: "Montagem", 2: "Embalagem"}

STATUS_COMPRA = {0: "Orçamento", 1: "Pedido", 2: "Faturado", 6: "Cancelado",
                 8: "Recebido", 9: "Devolvido"}

STATUS_ORCAMENTO = {0: "Pendente", 1: "Negociação", 6: "Renovado",
                    7: "Expirado", 8: "Rejeitado", 9: "Aprovado"}

STATUS_PEDIDO = {0: "Pendente", 1: "Faturado", 2: "Produzindo", 3: "Pronto",
                 8: "Cancelado", 9: "Entregue"}

STATUS_PREVISAO = {0: "Editando", 1: "Pendente", 2: "Parcial", 8: "Cancelado",
                   9: "Quitado"}

STATUS_PRODUCAO = {0: "Executando", 9: "Finalizado"}

TIPO_CONTA = {0: "Cliente", 1: "Cliente/Fornecedor", 2: "Fornecedor"}

# Tipos de evento do formulário público de orçamento (valores gravados em
# `Evento.tipo`). O painel (sys) mantém o próprio vocabulário em
# app/routes/sys/orcamentos.py.
TIPO_EVENTO = as_options(
    'Aniversário', 'Casamento', 'Chá de Bebê', 'Chá de Panela',
    'Confraternização', 'Formatura', '15 anos', 'Café', 'Outros')

TIPO_INGREDIENTE = {0: "Ingrediente", 1: "Forminha", 2: "Embalagem"}

TIPO_OPERACAO = {1: "Receitas", 2: "Despesas"}

TIPO_RECURSO = {0: "Caixa", 1: "Banco", 2: "Cartão"}

TIPO_TRANSACAO = {'R': 'Receber', 'P': 'Pagar'}

UND_INSUMO = as_options('Kg', 'G', 'L', 'Ml', 'Un', 'Colher de Chá',
                        'Colher de Sopa', 'Xícara', 'Pitada')