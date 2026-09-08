from ajsystem.core.extensions import db
from app.constantes import TIPO_CONTA


class Conta(db.Model):
    __tablename__ = "conta"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.Text)
    cpf = db.Column(db.String(14), nullable=True)
    cnpj = db.Column(db.String(18), nullable=True)
    insc_estadual = db.Column(db.String(20), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    tipo = db.Column(db.Integer, default=0)

    pedidos = db.relationship("Pedido", backref="conta", lazy="dynamic")

    def __repr__(self):
        return f"<Conta {self.nome}>"


Entity = {
    'id':             {'type': 'ID', 'width': 7},
    'nome':           {'type': 'TEXT', 'width': 20, 'transform': 'title'},
    'tipo':           {'type': 'LIST', 'width': 12, 'options': TIPO_CONTA},
    'telefone':       {'type': 'FONE', 'required': True},
    'email':          {'type': 'TEXT', 'input': 'email', 'width': 50},
    'cpf':            {'type': 'CPF', 'label': 'CPF',
                       'on_set': {'disables': ['cnpj', 'insc_estadual']}},
    'cnpj':           {'type': 'CNPJ', 'label': 'CNPJ',
                       'on_set': {'disables': ['cpf']}},
    'insc_estadual':  {'type': 'TEXT', 'label': 'Insc. Estadual',
                       'on_set': {'disables': ['cpf']}},
    'endereco':       {'type': 'TEXT', 'label': 'Endereço', 'input': 'textarea', 'pos_list': 2},
    'ativo':          {'type': 'BOOL'},
}
