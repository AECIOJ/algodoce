from app.models.ingredient import Ingredient
from app.models.product_ingredient import ProductIngredient
from app.models.producao_insumo import ProducaoInsumo
from app.models.compra_item import CompraItem
from app.models.unit_conversion import UnitConversion
from app.constantes import TIPO_INGREDIENTE, UND_LIST, PRODUCAO_ETAPAS


def unidade_on_set(row):
    """`on_set` da Unidade de Conversão: fator=1 ao trocar a unidade."""
    row['fator'] = 1


Entity = {
    'Ingredient': {
        'id':              {'type': 'ID', 'width': 6},
        'nome':            {'type': 'TEXT', 'width': 18, 'transform': 'title'},
        'tipo':            {'type': 'LIST', 'width': 12, 'list': TIPO_INGREDIENTE},
        'unidade_medida':  {'type': 'LIST', 'width': 8, 'list': UND_LIST, 'required': True},
    },
    'UnitConversion': {
        'id':            {'type': 'ID'},
        'ingredient_id': {'type': 'DK'},
        'unidade':       {'type': 'LIST', 'list': UND_LIST, 'required': True, 'on_set': unidade_on_set},
        'fator':         {'type': 'NUM', 'required': True, 'decimals': 6},
    },
    'ProductIngredient': {
        'ingredient_id': {'type': 'DK'},
        'product_id':    {'type': 'FK', 'label': 'Produto', 'required': True},
        'quantidade':    {'type': 'NUM'},
        'unidade':       {'type': 'LIST', 'list': UND_LIST},
        'etapas':        {'type': 'MULT10', 'list': PRODUCAO_ETAPAS},
    },
}

List = {
    'fields': 'Ingredient',
    'ordering': ['nome'],
}


Form = {
    'fields': 'Ingredient',
    'delete': {
        'when': {ProductIngredient, ProducaoInsumo, CompraItem, UnitConversion},
    },
    'sessions': {
        'Conversões': {'table': ['UnitConversion']},
        'Produtos': {'table': ['ProductIngredient'], 'readonly': True},
    },
}
