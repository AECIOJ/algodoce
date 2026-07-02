from app.extensions import db


class Compra(db.Model):
    __tablename__ = "compras"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("conta.id"), nullable=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    historico = db.Column(db.Text, nullable=True)
    status = db.Column(db.Integer, nullable=False, default=0)
    data_recepcao = db.Column(db.Date, nullable=True)
    carteira_id = db.Column(db.Integer, db.ForeignKey("carteira.id"), nullable=True)
    transacao_id = db.Column(db.Integer, db.ForeignKey("transacao.id"), nullable=True, unique=True)
    movto_id = db.Column(db.Integer, db.ForeignKey("movto.id"), nullable=True, unique=True)

    fornecedor = db.relationship("Conta", foreign_keys=[fornecedor_id])
    carteira = db.relationship("Carteira", uselist=False)
    transacao = db.relationship("Transacao", foreign_keys=[transacao_id], uselist=False)
    movto = db.relationship("Movto", foreign_keys=[movto_id], uselist=False)
    items = db.relationship(
        "CompraItem", back_populates="compra",
        foreign_keys="CompraItem.compra_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Compra {self.id}>"
