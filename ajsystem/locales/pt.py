"""Textos do framework em português (Brasil).

Declara as mesmas chaves de `en.py`. É o locale que o `App.locale` do
algodoce usa, e o framework o embarca de propósito: copiar `ajsystem/` inteiro
traz a tradução junto, sem depender do app.

Ver `en.py` para a lista completa e para a regra (o valor inglês é a chave, o
`label` guarda o inglês, a tradução acontece no render).
"""

# ── botões ──────────────────────────────────────────────────────────────────
SAVE = 'Salvar'
SEND = 'Enviar'
DELETE = 'Excluir'
NEW = '+ Incluir'
BACK = 'Voltar'
EDIT = 'Editar'
CANCEL = 'Cancelar'
CONVERT = 'Converter'
LIST = 'Lista'
PRINT = 'Imprimir'
DETAILS = 'Detalhes'
ADD = '+ Adicionar'
ADD_ITEM = '+ Adicionar Item'
FINISH = 'Finalizar'
REFRESH = 'Atualizar'
REMOVE = 'Remover'
YES = 'Sim, continuar logado'
NO = 'Não'
CLEAR = 'Limpar'
APPLY = 'Aplicar'
OK = 'OK'
EXIT = 'Sair'
RENEW = 'Renovar'
REPORT = 'Relatório'
GENERATE = 'Gerar'
CONFIRM = 'Confirmar'
EDIT_PRODUCT = 'Editar Produto'
LOGIN = 'Entrar'
ACCESS = 'Acessar'
ACTIVATE = 'Ativar'
DEACTIVATE = 'Desativar'

# ── confirmações ───────────────────────────────────────────────────────────
CONFIRM_DELETE = 'Confirmar exclusão?'
REMOVE_ITEM = 'Remover este item?'
DISCARD_CHANGES = 'Descartar alterações?'

# ── ConfirmModal ───────────────────────────────────────────────────────────
CM_DELETE_TITLE = 'Excluir registro'
CM_DELETE_MSG = 'Tem certeza que deseja excluir?'
CM_REMOVE_TITLE = 'Remover item'
CM_REMOVE_MSG = 'Remover este item da lista?'

# ── flash / mensagens de formulário ────────────────────────────────────────
MSG_DELETED = 'Excluído!'
MSG_ENTITY_DELETED = '{label} excluído!'
MSG_CANNOT_DELETE = 'Não é possível excluir — está em uso.'
MSG_UPDATED = 'Atualizado!'

# Validação: o texto é do framework, o `{field}` é o label do app (português).
MSG_FIELD_REQUIRED = '{field} é obrigatório.'
MSG_FIELD_INVALID = '{field} inválido.'
MSG_FIELD_MIN = '{field} deve ser maior ou igual a {min}.'
MSG_FIELD_MAX = '{field} deve ser menor ou igual a {max}.'
MSG_OUT_OF_SCOPE = 'Registro fora do escopo da página.'
MSG_TOO_LARGE = '{field} excede o tamanho máximo.'
MSG_FIELD_FORMAT = '{field} em formato não permitido.'

# ── sessão / acesso ────────────────────────────────────────────────────────
MSG_ACCESS_OK = 'Acesso autorizado.'
MSG_ACCESS_DENIED = 'Acesso negado.'
MSG_BAD_CREDENTIALS_FLASH = 'Credenciais inválidas.'
MSG_SETTINGS_SAVED = 'Configurações salvas com sucesso.'
MSG_SESSION_ENDED = 'Sessão encerrada.'
MSG_LOGIN_RETRY = '. Tentativa {count}, aguarde {delay}s.'
MSG_LOGIN_BACKOFF = '. Próximas tentativas terão atraso progressivo.'

# ── erros de API (jsonify(error=...)) ──────────────────────────────────────
ERR_INVALID_PARAMS = 'parâmetros inválidos'
ERR_UNKNOWN_PAGE = 'página desconhecida'
ERR_UNKNOWN_SEARCH = 'busca desconhecida'
ERR_INVALID_PAGE_PARAM = 'parâmetro page inválido'
ERR_INVALID_BUTTON = 'botão inválido'
ERR_NO_RENDER = 'botão sem `render`'
ERR_BAD_CREDENTIALS = 'Usuário ou senha inválidos'
ERR_BAD_KEY = 'Chave inválida'
ERR_USER_NOT_FOUND = 'Usuário não encontrado'
ERR_USER_REQUIRED = 'Usuário obrigatório'
ERR_NO_IMAGE = 'Nenhuma imagem'
ERR_INVALID_FORMAT = 'Formato inválido'
ERR_FORMAT_NOT_ALLOWED = 'Formato não permitido'
ERR_INVALID_FILE = 'Arquivo inválido'
ERR_INVALID_QTY = 'Quantidade inválida.'
# Texto herdado do código, onde já estava assim (`error='identificar'`). Não é
# uma frase — corrigir a redação é só editar esta linha.
ERR_NEED_IDENTIFY = 'identificar'
REPORT_ERROR = 'Erro na impressão do Relatório'

# ── carrinho / vitrine ─────────────────────────────────────────────────────
CART_SENT = 'Orçamento enviado! Aguarde contato no WhatsApp.'
CART_TITLE = 'Meu Orçamento'
CART_ITEMS = 'Itens do Orçamento'

# ── modais de escolha / impressão ──────────────────────────────────────────
CHOOSE = 'Escolha'

# ── modos de filtro de listagem ─────────────────────────────────────────────
# Mesmo conjunto de nomes de `en.py`; aqui é só a tradução exibida.
FILTER_EQ = 'Igual a'
FILTER_CONTAINS = 'Contém'
FILTER_STARTS = 'Começa'
FILTER_BETWEEN = 'Entre'
FILTER_GT = 'Maior que'
FILTER_GTE = 'Maior ou igual a'
FILTER_LT = 'Menor que'
FILTER_LTE = 'Menor ou igual a'
FILTER_TODAY = 'Hoje'
FILTER_YESTERDAY = 'Ontem'
FILTER_LAST_7 = 'Últimos 7 dias'
FILTER_THIS_MONTH = 'Mês Atual'
FILTER_LAST_MONTH = 'Mês Anterior'
FILTER_MONTH = 'Mês'
FILTER_MONTH_YEAR = 'Mês/Ano'
FILTER_THIS_YEAR = 'Ano Atual'
FILTER_LAST_YEAR = 'Ano Anterior'
FILTER_YEAR = 'Ano'
FILTER_UNTIL = 'Até a data de'
FILTER_FROM = 'A partir de'
FILTER_PERIOD = 'Período'
FILTER_ALL = 'Todos'
FILTER_YES = 'Sim'
