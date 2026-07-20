from app.extensions import db


class Trf(db.Model):
    __tablename__ = "recurso_trf"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    historico = db.Column(db.Text, nullable=True)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    movtos = db.relationship("Movto", backref="trf", lazy="dynamic")

    def __repr__(self):
        return f"<Trf {self.id} total={self.total}>"
