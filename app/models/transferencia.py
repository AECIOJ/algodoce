from ajsystem.core.extensions import db


class Transferencia(db.Model):
    __tablename__ = "transferencias"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    historico = db.Column(db.Text, nullable=True)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    movtos = db.relationship("Movimento", backref="transferencia", lazy="dynamic",
                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transferencia {self.id} total={self.total}>"


def _trf_status(t):
    """Situação da transferência: sem linhas → Editando; total ≠ 0 → Pendente."""
    try:
        n = t.movtos.count() if t is not None and t.id else 0
    except Exception:
        n = 0
    if not n:
        return 'Editando'
    try:
        total = float(t.total or 0)
    except (TypeError, ValueError):
        total = 0.0
    return 'Pendente' if abs(total) > 0.005 else 'Fechada'


Entity = {
    'id':        {'type': 'ID', 'width': 7},
    'data':      {'type': 'DATA', 'width': 10, 'required': True},
    'historico': {'type': 'MEMO', 'label': 'Histórico', 'width': 30, 'pos_list': 2},
    'total':     {'type': 'NUM', 'label': 'Total', 'width': 12, 'currency': 1, 'readonly': True},
    'status':    {'type': 'TEXT', 'label': 'Status', 'width': 12, 'calc': _trf_status,
                  'tag': {'colors': {'Editando': 'neutral', 'Pendente': 'warning',
                                     'Fechada': 'success'}}},
}
