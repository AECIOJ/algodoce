from decimal import Decimal

from ajsystem.core.extensions import db
from app.extends.constants import ENTRADA, STATUS_TRANSFERENCIA
from app.extends.masks import DECIMAL, MVALOR, THOUSAND
from app.extends.utils import num0

# Tolerância da soma em centavos (mesma do `calc_status` e do sistema legado):
# é o resto de ponto flutuante, não folga de digitação.
TOLERANCIA = 0.005


def _num(valor):
    s = f'{abs(float(valor)):,.2f}'.replace(',', '\x00').replace('.', '\x01')
    s = s.replace('\x00', THOUSAND).replace('\x01', DECIMAL)
    return ('-' if valor < 0 else '+') + s


class Transferencia(db.Model):
    __tablename__ = "transferencias"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    documento = db.Column(db.String(50), nullable=True)
    historico = db.Column(db.Text, nullable=True)
    status = db.Column(db.Integer, nullable=False, default=0)

    movtos = db.relationship("Movimento", backref="transferencia", lazy="dynamic",
                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transferencia {self.id} status={self.status}>"

    @property
    def total(self):
        return sum((num0(l.valor_assinado) for l in self.movtos), Decimal(0))

    def calc_status(self):
        try:
            n = self.movtos.count() if self.id else 0
        except Exception:
            n = 0
        if not n:
            return 0
        try:
            total = float(self.total or 0)
        except (TypeError, ValueError):
            total = 0.0
        return 9 if abs(total) <= TOLERANCIA else 1

    @staticmethod
    def erro_lancamentos(lancamentos):
        soma = Decimal(0)
        for i, (tipo, valor) in enumerate(lancamentos, start=1):
            valor = num0(valor)
            if valor <= 0:
                return f'Linha {i}: valor deve ser maior que zero.'
            soma += valor if tipo == ENTRADA else -valor
        if abs(soma) > TOLERANCIA:
            return (f'Transferência não fecha em zero '
                    f'(diferença: {_num(soma)}). Ajuste os valores.')
        return None


Entity = {
    'id':        {'type': 'ID', 'width': 7},
    'data':      {'type': 'DATA', 'width': 10, 'required': True},
    'documento': {'type': 'TEXT', 'width': 12},
    'total':     {'type': 'NUM', 'label': 'Diferença', 'width': 12, 'readonly': True,
                  'mask': MVALOR},
    'status':    {'type': 'LIST', 'label': 'Status', 'width': 12,
                  'options': STATUS_TRANSFERENCIA,
                  'calc': {'type': 'call', 'source': 'calc_status',
                           'diff': 'Aviso de Inconsistência: Status registrado desta transferência difere do status calculado.'}},
    'historico': {'type': 'MEMO', 'label': 'Histórico', 'width': 30},
}
