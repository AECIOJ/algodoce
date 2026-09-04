from app.ajsystem.core.extensions import db
from app.constantes import tipos_evento


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(
        db.Integer, db.ForeignKey("quotes.id"), nullable=True, unique=True
    )
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id"), nullable=True, unique=True
    )
    tipo = db.Column(db.String(30), nullable=True)
    tema = db.Column(db.String(200), nullable=True)
    obs = db.Column(db.Text, nullable=True)
    data = db.Column(db.Date, nullable=True)
    hora = db.Column(db.Time, nullable=True)
    local = db.Column(db.String(200), nullable=True)
    convidados = db.Column(db.Integer, nullable=True)
    cerimonial = db.Column(db.String(200), nullable=True)

    quote = db.relationship("Quote", back_populates="event", foreign_keys=[quote_id])
    order = db.relationship("Order", back_populates="event", foreign_keys=[order_id])

    def __repr__(self):
        return f"<Event {self.id}>"


Entity = {
    'id':          {'type': 'ID'},
    'quote_id':    {'type': 'DK'},
    'order_id':    {'type': 'DK'},
    'tipo':        {'type': 'LIST', 'label': 'Tipo', 'options': tipos_evento},
    'tema':        {'type': 'TEXT', 'width': 22},
    'data':        {'type': 'DATA', 'label': 'Data do evento'},
    'hora':        {'type': 'HORA', 'label': 'Horário'},
    'local':       {'type': 'TEXT', 'width': 24},
    'convidados':  {'type': 'INT', 'label': 'Convidados'},
    'cerimonial':  {'type': 'TEXT', 'width': 22},
    'obs':         {'type': 'MEMO', 'label': 'Observações', 'pos_list': 2},
}
