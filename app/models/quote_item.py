from app.extensions import db


class QuoteItem(db.Model):
    __tablename__ = "quote_items"

    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(
        db.Integer, db.ForeignKey("quotes.id"), nullable=False
    )
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), nullable=False
    )
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    product = db.relationship("Product", lazy="joined")
    quote = db.relationship("Quote", back_populates="items")

    def __repr__(self):
        return f"<QuoteItem q={self.quote_id} p={self.product_id}>"
