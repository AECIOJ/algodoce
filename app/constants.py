TIPO_CONTA = {0: "Cliente", 1: "Cliente/Fornecedor", 2: "Fornecedor"}

TIPO_INGREDIENTE = {0: "Ingrediente", 1: "Forminha", 2: "Embalagem"}

ORDER_STATUS = {0: "Pendente", 1: "Produzindo", 2: "Pronto", 8: "Cancelado", 9: "Entregue"}
ORDER_STATUS_FILTER = [("todos", "Todos"), ("0", "Pendente"), ("1", "Produzindo"),
                       ("2", "Pronto"), ("8", "Cancelado"), ("9", "Entregue")]

COMPRA_STATUS = {0: "Orçamento", 1: "Pedido", 6: "Cancelado", 8: "Recebido", 9: "Devolvido"}
COMPRA_STATUS_FILTER = [("todos", "Todos"), ("0", "Orçamento"), ("1", "Pedido"),
                        ("6", "Cancelado"), ("8", "Recebido"), ("9", "Devolvido")]

QUOTE_STATUS = {0: "Pendente", 1: "Negociação", 6: "Renovado",
                7: "Expirado", 8: "Reprovado", 9: "Aprovado"}

QUOTE_STATUS_FILTER = [("todos", "Todos"), ("0", "Pendente"), ("1", "Negociação"),
                       ("6", "Renovado"), ("7", "Expirado"),
                       ("8", "Reprovado"), ("9", "Aprovado")]

PRODUCAO_STATUS = {0: "Executando", 9: "Finalizado"}

PRODUCAO_ETAPAS = {0: "Preparação", 1: "Montagem", 2: "Embalagem"}

FORMINHAS = {0: "Simples", 1: "Fornecidas pelo Cliente"}

TIPO_RUBRICA = {1: "Receitas", 2: "Despesas"}

TIPO_PREVISAO = {"P": "Pagar", "R": "Receber"}
TIPO_TRANSACAO = {"P": "Contas a Pagar", "R": "Contas a Receber",
                  "C": "Compras", "V": "Vendas"}

PREVISAO_STATUS = {0: "Editando", 1: "Pendente", 2: "Parcial", 8: "Cancelado", 9: "Quitado"}

TIPO_RECURSO = {0: "Caixa", 1: "Banco", 2: "Cartão"}

CONECTORES = {"de", "da", "do", "das", "dos", "para", "pra", "com", "sem", "em", "no", "na", "nos", "nas", "por", "ao", "aos", "à", "às", "e", "ou", "a", "o", "as", "os", "um", "uma", "uns", "umas", "num", "numa", "dum", "duma", "pelo", "pela", "pelos", "pelas", "pro", "pra", "pros", "pras"}

TRANSFORMAR_AO_SALVAR = {
    "Category":    {"nome": 1},
    "Product":     {"nome": 1},
    "Ingredient":  {"nome": 1, "unidade_medida": 2},
    "Conta":       {"nome": 1},
    "Quote":       {"cliente_nome": 1},
    "Recurso":     {"nome": 1},
    "Carteira": {"nome": 1},
    "Producao":    {"descricao": 1},
    "Previsao":    {"documento": 2},
    "Movto":       {"documento": 2, "historico": 1},
}
