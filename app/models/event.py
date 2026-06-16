from app.extensions import db


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
