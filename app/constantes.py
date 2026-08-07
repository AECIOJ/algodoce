from app.ajsystem.constants import CONECTORES
from app.ajsystem.utils import as_options


TIPO_CONTA = {0: "Cliente", 1: "Cliente/Fornecedor", 2: "Fornecedor"}

TIPO_INGREDIENTE = {0: "Ingrediente", 1: "Forminha", 2: "Embalagem"}

ORDER_STATUS = {0: "Pendente", 1: "Produzindo", 2: "Pronto", 8: "Cancelado", 9: "Entregue"}
ORDER_STATUS_FILTER = [("todos", "Todos"), ("0", "Pendente"), ("1", "Produzindo"),
                       ("2", "Pronto"), ("8", "Cancelado"), ("9", "Entregue")]

COMPRA_STATUS = {0: "Orçamento", 1: "Pedido", 2: "Compra", 6: "Cancelado", 8: "Recebido", 9: "Devolvido"}
COMPRA_STATUS_FILTER = [("todos", "Todos"), ("0", "Orçamento"), ("1", "Pedido"),
                        ("2", "Compra"), ("6", "Cancelado"), ("8", "Recebido"), ("9", "Devolvido")]

QUOTE_STATUS = {0: "Pendente", 1: "Negociação", 6: "Renovado",
                7: "Expirado", 8: "Reprovado", 9: "Aprovado"}

QUOTE_STATUS_FILTER = [("todos", "Todos"), ("0", "Pendente"), ("1", "Negociação"),
                       ("6", "Renovado"), ("7", "Expirado"),
                       ("8", "Reprovado"), ("9", "Aprovado")]

PRODUCAO_STATUS = {0: "Executando", 9: "Finalizado"}

PRODUCAO_ETAPAS = {0: "Preparação", 1: "Montagem", 2: "Embalagem"}

FORMINHAS = {0: "Simples (Inclusa)", 1: "Fornecidas pelo Cliente"}

TIPO_OPERACAO = {1: "Receitas", 2: "Despesas"}

TIPO_PREVISAO = {"P": "Pagar", "R": "Receber"}
TIPO_TRANSACAO = {"P": "Contas a Pagar", "R": "Contas a Receber",
                  "C": "Compras", "V": "Vendas"}

PREVISAO_STATUS = {0: "Editando", 1: "Pendente", 2: "Parcial", 8: "Cancelado", 9: "Quitado"}

TIPO_RECURSO = {0: "Caixa", 1: "Banco", 2: "Cartão"}

CARTEIRA_USO = {0: "Pedido", 1: "Pedido e Compra", 2: "Compra"}
CARTEIRA_GERAR = {0: "Movimento", 1: "Previsão"}

UND_INSUMO = ["Kg", "G", "L", "Ml", "Un", "Cx", "Pacote", "Colher_cha", "Colher_sopa", "Xicara", "Pitada", "Litro"]
UND_LIST = as_options(UND_INSUMO)

