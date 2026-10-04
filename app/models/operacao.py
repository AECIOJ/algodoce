from app.extends.constants import TIPO_OPERACAO
from ajsystem.core.extensions import db


class Operacao(db.Model):
    __tablename__ = "operacao"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.Integer, nullable=False, server_default="1")
    pai_id = db.Column(db.Integer, db.ForeignKey("operacao.id"), nullable=True)
    ordem = db.Column(db.Integer, nullable=False, server_default="0")
    fator = db.Column(db.Integer, nullable=False, server_default="1")
    ativa = db.Column(db.Boolean, default=True)

    pai = db.relationship("Operacao", remote_side="Operacao.id", backref="filhos")

    def __repr__(self):
        return f"<Operacao {self.nome}>"


Entity = {
    'id':     {'type': 'ID', 'width': 6},
    # Sem 'calc': o índice ('1.01.001') vem montado da query (QPLANO via
    # over+calc, passo único). A entrada segue dando label/largura.
    'indice': {'type': 'TEXT', 'label': 'Índice', 'width': 6},
    'nome':   {'type': 'TEXT', 'width': 25, 'mask': '@T'},
    'tipo':   {'type': 'LIST', 'width': 12, 'options': TIPO_OPERACAO},
    'fator':  {'type': 'INT', 'width': 8},
    'pai_id': {'type': 'FK', 'label': 'Superior', 'width': 30,
               'lookup': {'display': 'nome', 'when': {'pai_id': None}}},
    'ordem':  {'type': 'INT', 'width': 8},
    'ativa':  {'type': 'BOOL', 'input': 'toggle', 'width': 8, 'pos_form': 3},
}
