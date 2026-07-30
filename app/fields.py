from app.filters import FILTER_NUMBER, FILTER_DATE, FILTER_BOOLEAN, FILTER_SELECT

INPUT_NUMBER   = {'input': 'number', 'align': 'right'}
INPUT_DATE     = {'input': 'date'}
INPUT_TIME     = {'input': 'time'}
INPUT_BOOLEAN  = {'input': 'boolean'}
INPUT_TEXTAREA = {'input': 'textarea'}
INPUT_SELECT   = {'input': 'select'}
INPUT_CHECKBOX = {'input': 'checkbox'}

FIELD_ID         = {'label': '#', 'mask': '999.999', 'edit': False}
FIELD_ID_SHORT   = {'label': '#', 'mask': '999', 'input': 'number', 'edit': False, 'filter': FILTER_NUMBER}

FIELD_NOME       = {'required': True, 'transform': 'title'}
FIELD_DESCRICAO  = {'label': 'Descrição', 'grid': 12, 'input': 'textarea'}
FIELD_HISTORICO  = {'label': 'Histórico', 'transform': 'title'}
FIELD_OBS        = {'label': 'Observação', 'grid': 12, 'input': 'textarea'}
FIELD_DOCUMENTO  = {'transform': 'upper'}
FIELD_FATURA     = {'width': 10}

FIELD_TELEFONE   = {'width': 14}
FIELD_CPF        = {'label': 'CPF', 'grid': 4}
FIELD_CNPJ       = {'label': 'CNPJ', 'grid': 4}
FIELD_EMAIL      = {'grid': 3}
FIELD_ENDERECO   = {'label': 'Endereço', 'grid': 12, 'input': 'textarea'}
FIELD_ATIVO      = {'input': 'boolean', 'edit': False, 'filter': FILTER_BOOLEAN}

FIELD_VALOR      = {'input': 'number', 'align': 'right', 'currency': 'brl', 'filter': FILTER_NUMBER}
FIELD_PRECO      = {'label': 'Preço', 'input': 'number', 'attrs': {'step': '0.01'}, 'filter': FILTER_NUMBER}
FIELD_QUANTIDADE = {'input': 'number', 'filter': FILTER_NUMBER}
FIELD_TOTAL      = {'input': 'number', 'align': 'right', 'aggregate': 'sum', 'currency': 'brl', 'edit': False, 'filter': FILTER_NUMBER}
FIELD_ORDEM      = {'mask': '999', 'input': 'number', 'attrs': {'min': 0, 'max': 99}, 'filter': FILTER_NUMBER}
FIELD_PREVISTO   = {'input': 'number', 'align': 'right', 'aggregate': 'sum', 'currency': 'brl', 'filter': FILTER_NUMBER}
FIELD_REALIZADO  = {'input': 'number', 'align': 'right', 'aggregate': 'sum', 'currency': 'brl', 'filter': FILTER_NUMBER}
FIELD_VARIACAO   = {'label': 'Variação', 'input': 'number', 'align': 'right', 'aggregate': 'sum', 'currency': 'brl', 'filter': FILTER_NUMBER}
FIELD_SALDO      = {'input': 'number', 'align': 'right', 'aggregate': 'sum', 'currency': 'brl', 'filter': FILTER_NUMBER}

FIELD_DATA       = {'input': 'date', 'filter': FILTER_DATE}
FIELD_VENCIMENTO = {'input': 'date', 'filter': FILTER_DATE}
FIELD_HORA       = {'input': 'time'}
FIELD_DATA_HORA  = {'label': 'Data', 'input': 'datetime-local', 'filter': FILTER_DATE}

FIELD_TIPO       = {'input': 'select', 'filter': FILTER_SELECT}
FIELD_STATUS     = {'input': 'select', 'edit': False, 'filter': FILTER_SELECT}
