from app.ajsystem.defs.constants import CONECTORES
from app.ajsystem.core.utils import as_options


TIPO_CONTA = {0: "Cliente", 1: "Cliente/Fornecedor", 2: "Fornecedor"}

TIPO_INGREDIENTE = {0: "Ingrediente", 1: "Forminha", 2: "Embalagem"}

ORDER_STATUS = {0: "Pendente", 1: "Produzindo", 2: "Pronto", 8: "Cancelado", 9: "Entregue"}

COMPRA_STATUS = {0: "Orçamento", 1: "Pedido", 2: "Compra", 6: "Cancelado", 8: "Recebido", 9: "Devolvido"}

QUOTE_STATUS = {0: "Pendente", 1: "Negociação", 6: "Renovado",
                7: "Expirado", 8: "Rejeitado", 9: "Aprovado"}

PRODUCAO_STATUS = {0: "Executando", 9: "Finalizado"}

PRODUCAO_ETAPAS = {0: "Preparação", 1: "Montagem", 2: "Embalagem"}

FORMINHAS = {0: "Simples (Inclusa)", 1: "Fornecidas pelo Cliente"}

# Tipos de evento do formulário público de orçamento (valores gravados em
# `Event.tipo`). O painel (sys) mantém o próprio vocabulário em
# app/routes/sys/orcamentos.py.
tipos_evento = {
    'aniversario': 'Aniversário',
    'casamento': 'Casamento',
    'cha_de_bebe': 'Chá de Bebê',
    'cha_de_panela': 'Chá de Panela',
    'confraternizacao': 'Confraternização',
    'formatura': 'Formatura',
    '15_anos': '15 anos',
    'cafe': 'Café',
    'outros': 'Outros',
}

TIPO_OPERACAO = {1: "Receitas", 2: "Despesas"}

TIPO_TRANSACAO = {'R': 'Receber', 'P': 'Pagar'}

PREVISAO_STATUS = {0: "Editando", 1: "Pendente", 2: "Parcial", 8: "Cancelado", 9: "Quitado"}

TIPO_RECURSO = {0: "Caixa", 1: "Banco", 2: "Cartão"}

CARTEIRA_USO = {0: "Pedido", 1: "Pedido e Compra", 2: "Compra"}
CARTEIRA_GERAR = {0: "Movimento", 1: "Previsão"}

UND_INSUMO = ["Kg", "G", "L", "Ml", "Un", "Colher_cha", "Colher_sopa", "Xicara", "Pitada"]
UND_LIST = as_options(UND_INSUMO)

