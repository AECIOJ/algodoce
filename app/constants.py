TIPO_CONTA = {0: "Cliente", 1: "Cliente/Fornecedor", 2: "Fornecedor"}

TIPO_INGREDIENTE = {0: "Ingrediente", 1: "Forminha", 2: "Embalagem"}

ORDER_STATUS = {0: "Pendente", 1: "Produzindo", 2: "Pronto", 3: "Cancelado", 9: "Entregue"}

QUOTE_STATUS = {0: "Pendente", 1: "Negociação", 6: "Renovado",
                7: "Expirado", 8: "Reprovado", 9: "Aprovado"}

QUOTE_STATUS_FILTER = [("todos", "Todos"), ("0", "Pendente"), ("1", "Negociação"),
                       ("6", "Renovado"), ("7", "Expirado"),
                       ("8", "Reprovado"), ("9", "Aprovado")]

PRODUCAO_STATUS = {0: "Executando", 9: "Finalizado"}

PRODUCAO_ETAPAS = {0: "Preparação", 1: "Montagem", 2: "Embalagem"}

FORMA_PAGAMENTO = {0: "À vista", 1: "50% Pedido + 50% Entrega", 2: "Na Entrega"}

FORMINHAS = {0: "Simples", 1: "Fornecidas pelo Cliente"}

TIPO_RUBRICA = {1: "Receitas", 2: "Despesas"}

TIPO_PREVISAO = {"P": "Pagar", "R": "Receber"}

PREVISAO_STATUS = {0: "Editando", 1: "Pendente", 2: "Parcial", 8: "Cancelado", 9: "Quitado"}

TIPO_RECURSO = {0: "Caixa", 1: "Banco", 2: "Cartão"}
