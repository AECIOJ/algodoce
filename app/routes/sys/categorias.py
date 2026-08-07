from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.form import handle_form


Entidade = {
    'Category': {
        'id':    {'type': 'ID', 'width': 6},
        'nome':  {'type': 'TEXT'},
        'ordem': {'type': 'INT', 'mask': '999', 'min': 0, 'max': 99},
        'ativo': {'type': 'LOGICO'},
    },
}

Lista = {
    'colunas': ['Category'],
    'ordering': ['ordem', 'nome'],
    'title': 'Categorias',
}


def _pre_save(instance, request, is_new):
    if instance.ordem is None and is_new:
        last = db.session.query(db.func.max(Category.ordem)).scalar() or 0
        instance.ordem = last + 1


def _post_save(instance, changed, old_vals):
    if 'ordem' not in changed:
        return
    others = Category.query.filter(Category.id != instance.id).order_by(Category.ordem, Category.nome).all()
    n = instance.ordem
    if n is None or n > len(others) + 1:
        ordered = others + [instance]
    else:
        ordered = others[:n-1] + [instance] + others[n-1:]
    for i, cat in enumerate(ordered, 1):
        cat.ordem = i
    db.session.commit()


Form = {
    'fields': 'Category',
    'delete': {
        'when': {Product},
        'msg_ok': 'Categoria excluída!',
        'msg_no': 'Não é possível excluir a categoria — está em uso.',
    },
    'pre_save': _pre_save,
    'post_save': _post_save,
    'buttons': ['on_off'],
}
