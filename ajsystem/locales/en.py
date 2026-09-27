"""Catálogo de textos do framework em inglês.

ESTE MÓDULO É A ÂNCORA do mecanismo de locale. Cada constante aqui é, ao mesmo
tempo, a **chave** de tradução e o **fallback** quando o locale ativo não define
aquele texto. Por isso os valores precisam ser únicos: dois nomes com o mesmo
valor colidiriam no dicionário, e um sobrescreveria o outro em silêncio. O
carregador (`ajsystem.locales.t`) verifica isso na carga e levanta.

Consequência prática de designar o valor em inglês como chave: `Button.label`
guarda sempre o **inglês**, e a tradução acontece no render (`Button.text()`).
Assim nunca vaza chave para a tela, e texto faltando no locale degrada para
inglês — que é um erro que se enxerga, não um bug silencioso.

Cada idioma vive num módulo irmão com os MESMOS nomes (`pt.py`), e o locale
ativo é declarado pelo app em `App.locale` (`app/config.py`).

Escopo: só copy visível ao usuário final (rótulos, mensagens de confirmação,
flash e `jsonify(error=...)`). Mensagem de `ValueError` é diagnóstico de
desenvolvedor e fica em português no código, de propósito.
"""

# ── botões ──────────────────────────────────────────────────────────────────
SAVE = 'Save'
SEND = 'Send'
DELETE = 'Delete'
NEW = '+ Include'
BACK = 'Back'
EDIT = 'Edit'
CANCEL = 'Cancel'
CONVERT = 'Convert'
LIST = 'List'
PRINT = 'Print'
DETAILS = 'Details'
ADD = '+ Add'
ADD_ITEM = '+ Add Item'
FINISH = 'Finish'
REFRESH = 'Refresh'
REMOVE = 'Remove'
YES = 'Yes, stay signed in'
NO = 'No'
CLEAR = 'Clear'
APPLY = 'Apply'
OK = 'OK'
EXIT = 'Exit'
RENEW = 'Renew'
REPORT = 'Report'
GENERATE = 'Generate'
CONFIRM = 'Confirm'
EDIT_PRODUCT = 'Edit Product'
LOGIN = 'Log in'
ACCESS = 'Access'
ACTIVATE = 'Activate'
DEACTIVATE = 'Deactivate'

# ── confirmações ───────────────────────────────────────────────────────────
CONFIRM_DELETE = 'Confirm deletion?'
REMOVE_ITEM = 'Remove this item?'
DISCARD_CHANGES = 'Discard changes?'

# ── ConfirmModal ───────────────────────────────────────────────────────────
CM_DELETE_TITLE = 'Delete record'
CM_DELETE_MSG = 'Are you sure you want to delete?'
CM_REMOVE_TITLE = 'Remove item'
CM_REMOVE_MSG = 'Remove this item from the list?'

# ── flash / mensagens de formulário ────────────────────────────────────────
MSG_DELETED = 'Deleted!'
MSG_ENTITY_DELETED = '{label} deleted!'
MSG_CANNOT_DELETE = 'Cannot delete — it is in use.'
MSG_UPDATED = 'Updated!'

# Validação: o texto é do framework, o `{field}` é o label do app (português).
MSG_FIELD_REQUIRED = '{field} is required.'
MSG_FIELD_INVALID = '{field} is invalid.'
MSG_FIELD_MIN = '{field} must be greater than or equal to {min}.'
MSG_FIELD_MAX = '{field} must be less than or equal to {max}.'
MSG_OUT_OF_SCOPE = 'Record outside the page scope.'
MSG_TOO_LARGE = '{field} exceeds the maximum size.'
MSG_FIELD_FORMAT = '{field} in a disallowed format.'

# ── sessão / acesso ────────────────────────────────────────────────────────
MSG_ACCESS_OK = 'Access authorized.'
MSG_ACCESS_DENIED = 'Access denied.'
# A resposta de login (`ERR_BAD_CREDENTIALS`) e o flash pós-submit são textos
# diferentes de propósito: um é UI do form de login, o outro é aviso de sessão.
MSG_BAD_CREDENTIALS_FLASH = 'Invalid credentials.'
MSG_SETTINGS_SAVED = 'Settings saved successfully.'
MSG_SESSION_ENDED = 'Session ended.'
MSG_LOGIN_RETRY = '. Attempt {count}, wait {delay}s.'
MSG_LOGIN_BACKOFF = '. Subsequent attempts will have a progressive delay.'

# ── erros de API (jsonify(error=...)) ──────────────────────────────────────
ERR_INVALID_PARAMS = 'invalid parameters'
ERR_UNKNOWN_PAGE = 'unknown page'
ERR_UNKNOWN_SEARCH = 'unknown search'
ERR_INVALID_PAGE_PARAM = 'invalid page parameter'
ERR_INVALID_BUTTON = 'invalid button'
ERR_NO_RENDER = 'button without `render`'
ERR_BAD_CREDENTIALS = 'Invalid username or password'
ERR_BAD_KEY = 'Invalid key'
ERR_USER_NOT_FOUND = 'User not found'
ERR_USER_REQUIRED = 'User required'
ERR_NO_IMAGE = 'No image'
ERR_INVALID_FORMAT = 'Invalid format'
ERR_FORMAT_NOT_ALLOWED = 'Format not allowed'
ERR_INVALID_FILE = 'Invalid file'
ERR_INVALID_QTY = 'Invalid quantity.'
ERR_NEED_IDENTIFY = 'identify'
REPORT_ERROR = 'Error printing the report'

# ── carrinho / vitrine ─────────────────────────────────────────────────────
CART_SENT = 'Quote sent! Awaiting contact via WhatsApp.'
CART_TITLE = 'My Quote'
CART_ITEMS = 'Quote Items'

# ── modais de escolha / impressão ──────────────────────────────────────────
CHOOSE = 'Choose'

# ── modos de filtro de listagem ─────────────────────────────────────────────
# Rótulo visível de cada modo de `List` (`core/list.py:filter_modes`). A chave
# `(valor, rótulo)` é gerada em tempo de render, então o rótulo sai daqui —
# antes ficava em português dentro do dicionário e ignorava `App.locale`.
# `text` e `number` compartilham FILTER_EQ de propósito: o valor inglês é a
# chave do catálogo e precisa ser único.
FILTER_EQ = 'Equal to'
FILTER_CONTAINS = 'Contains'
FILTER_STARTS = 'Starts with'
FILTER_BETWEEN = 'Between'
FILTER_GT = 'Greater than'
FILTER_GTE = 'Greater than or equal to'
FILTER_LT = 'Less than'
FILTER_LTE = 'Less than or equal to'
FILTER_TODAY = 'Today'
FILTER_YESTERDAY = 'Yesterday'
FILTER_LAST_7 = 'Last 7 days'
FILTER_THIS_MONTH = 'Current month'
FILTER_LAST_MONTH = 'Previous month'
FILTER_MONTH = 'Month'
FILTER_MONTH_YEAR = 'Month/Year'
FILTER_THIS_YEAR = 'Current year'
FILTER_LAST_YEAR = 'Previous year'
FILTER_YEAR = 'Year'
FILTER_UNTIL = 'Up to date'
FILTER_FROM = 'From date'
FILTER_PERIOD = 'Period'
FILTER_ALL = 'All'
FILTER_YES = 'Yes'
