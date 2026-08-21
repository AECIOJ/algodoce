"""
DEPRECADO — shim temporário para as rotas que ainda não migraram para o padrão Entity.

As definições base de tipos vivem agora em `app/ajsystem/config/fields.py`
(`FIELD_TYPES`, usados via `'type': 'X'` na Entity). As constantes abaixo
serão removidas quando pedidos/orcamentos/recursos/transacao forem migrados.
"""

INPUT_NUMBER   = {'input': 'number', 'align': 'right'}
INPUT_DATE     = {'input': 'date'}
INPUT_TIME     = {'input': 'time'}
INPUT_BOOLEAN  = {'input': 'boolean'}
INPUT_TEXTAREA = {'input': 'textarea'}
INPUT_SELECT   = {'input': 'select'}
INPUT_CHECKBOX = {'input': 'checkbox'}

FIELD_ID         = {'label': '#', 'mask': '999.999', 'readonly': True}
FIELD_ID_SHORT   = {'label': '#', 'mask': '999', 'input': 'number', 'readonly': True}

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
FIELD_ATIVO      = {'input': 'boolean', 'readonly': True}

FIELD_VALOR      = {'input': 'number', 'align': 'right', 'currency': 'brl'}
FIELD_PRECO      = {'label': 'Preço', 'input': 'number', 'attrs': {'step': '0.01'}}
FIELD_QUANTIDADE = {'input': 'number'}
FIELD_TOTAL      = {'input': 'number', 'align': 'right', 'agg': 'sum', 'currency': 'brl', 'readonly': True}
FIELD_ORDEM      = {'mask': '999', 'input': 'number', 'attrs': {'min': 0, 'max': 99}}
FIELD_PREVISTO   = {'input': 'number', 'align': 'right', 'agg': 'sum', 'currency': 'brl'}
FIELD_REALIZADO  = {'input': 'number', 'align': 'right', 'agg': 'sum', 'currency': 'brl'}
FIELD_VARIACAO   = {'label': 'Variação', 'input': 'number', 'align': 'right', 'agg': 'sum', 'currency': 'brl'}
FIELD_SALDO      = {'input': 'number', 'align': 'right', 'agg': 'sum', 'currency': 'brl'}

FIELD_DATA       = {'input': 'date'}
FIELD_VENCIMENTO = {'input': 'date'}
FIELD_HORA       = {'input': 'time'}
FIELD_DATA_HORA  = {'label': 'Data', 'input': 'datetime-local'}

FIELD_TIPO       = {'input': 'select'}
FIELD_STATUS     = {'input': 'select', 'readonly': True}
