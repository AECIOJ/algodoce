"""Constantes genéricas do framework (sem dependência da aplicação host)."""

CONECTORES = {"de", "da", "do", "das", "dos", "para", "pra", "com", "sem", "em", "no", "na", "nos", "nas", "por", "ao", "aos", "à", "às", "e", "ou", "a", "o", "as", "os", "um", "uma", "uns", "umas", "num", "numa", "dum", "duma", "pelo", "pela", "pelos", "pelas", "pro", "pra", "pros", "pras"}

# Moedas por código (prop `Field.currency`): 0 = sem moeda (falsy, como False).
# `True`/`'brl'` legados normalizam para o padrão (1). `locale` segue o
# padrão BCP 47 para agrupamento decimal nos renderizadores.
CURRENCY = {
    0: None,
    1: {'symbol': 'R$', 'locale': 'pt-BR'},
    2: {'symbol': '$', 'locale': 'en-US'},
    3: {'symbol': '€', 'locale': 'pt-BR'},
}
DEFAULT_CURRENCY = 1

# pos_form dict para campo `pos:0` explícito só quando valor não vazio (usado em transacao_id/movto_id)
# Exclusivamente via Schema, só afeta `form` (semântica de pos_form)
POS_EXPLICIT_NOT_EMPTY = {'pos': 0, 'when': {'not_empty': True}}
