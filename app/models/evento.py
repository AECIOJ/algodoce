from ajsystem.core.extensions import db
from app.constantes import tipos_evento


class Evento(db.Model):
    __tablename__ = "eventos"

    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(
        db.Integer, db.ForeignKey("orcamentos.id"), nullable=True, unique=True
    )
    pedido_id = db.Column(
        db.Integer, db.ForeignKey("pedidos.id"), nullable=True, unique=True
    )
    tipo = db.Column(db.String(30), nullable=True)
    tema = db.Column(db.String(200), nullable=True)
    obs = db.Column(db.Text, nullable=True)
    data = db.Column(db.Date, nullable=True)
    hora = db.Column(db.Time, nullable=True)
    local = db.Column(db.String(200), nullable=True)
    convidados = db.Column(db.Integer, nullable=True)
    cerimonial = db.Column(db.String(200), nullable=True)

    orcamento = db.relationship("Orcamento", back_populates="evento", foreign_keys=[orcamento_id])
    pedido = db.relationship("Pedido", back_populates="evento", foreign_keys=[pedido_id])

    def __repr__(self):
        return f"<Evento {self.id}>"


Entity = {
    'id':          {'type': 'ID'},
    'orcamento_id':    {'type': 'DK'},
    'pedido_id':    {'type': 'DK'},
    'tipo':        {'type': 'LIST', 'label': 'Tipo', 'options': tipos_evento},
    'tema':        {'type': 'TEXT', 'width': 22},
    'data':        {'type': 'DATA', 'label': 'Data do evento'},
    'hora':        {'type': 'HORA', 'label': 'Horário'},
    'local':       {'type': 'TEXT', 'width': 24},
    'convidados':  {'type': 'INT', 'label': 'Convidados'},
    'cerimonial':  {'type': 'TEXT', 'width': 22},
    'obs':         {'type': 'MEMO', 'label': 'Observações', 'pos_list': 2},
}
