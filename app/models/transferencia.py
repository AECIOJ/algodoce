from ajsystem.core.extensions import db


class Transferencia(db.Model):
    __tablename__ = "transferencias"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    historico = db.Column(db.Text, nullable=True)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='Editando')

    movtos = db.relationship("Movimento", backref="transferencia", lazy="dynamic",
                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transferencia {self.id} total={self.total}>"

    def calc_status(self):
        """Situação da transferência: sem linhas → Editando; total ≠ 0 → Pendente."""
        try:
            n = self.movtos.count() if self.id else 0
        except Exception:
            n = 0
        if not n:
            return 'Editando'
        try:
            total = float(self.total or 0)
        except (TypeError, ValueError):
            total = 0.0
        return 'Pendente' if abs(total) > 0.005 else 'Fechada'


Entity = {
    'id':        {'type': 'ID', 'width': 7},
    'data':      {'type': 'DATA', 'width': 10, 'required': True},
    'historico': {'type': 'MEMO', 'label': 'Histórico', 'width': 30},
    'total':     {'type': 'NUM', 'label': 'Total', 'width': 12, 'currency': 1, 'readonly': True},
    'status':    {'type': 'TEXT', 'label': 'Status', 'width': 12,
                  'calc': {'type': 'call', 'source': 'calc_status',
                           'diff': 'Aviso de Inconsistência: Status registrado desta transferência difere do status calculado.'}},
}
