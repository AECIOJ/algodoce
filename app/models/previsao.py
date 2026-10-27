from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property

from ajsystem.core.extensions import db
from app.extends.masks import MVALOR


class Previsao(db.Model):
    __tablename__ = "previsao"

    id = db.Column(db.Integer, primary_key=True)
    transacao_id = db.Column(db.Integer, db.ForeignKey("transacao.id"), nullable=False)
    documento = db.Column(db.String(50), nullable=True)
    vencimento = db.Column(db.Date, nullable=False)
    previsto = db.Column(db.Numeric(12, 2), nullable=False)
    realizado = db.Column(db.Numeric(12, 2), nullable=True)
    variacao = db.Column(db.Numeric(12, 2), nullable=True, server_default="0")
    recurso_id = db.Column(db.Integer, db.ForeignKey("recurso.id"), nullable=True)
    taxa = db.Column(db.Numeric(5, 2), nullable=False, default=0)

    recurso = db.relationship("Recurso", uselist=False)
    # conta via transacao (backref de Transacao.previsoes)
    conta = db.relationship("Conta", secondary="transacao",
                            primaryjoin="Previsao.transacao_id==Transacao.id",
                            secondaryjoin="Transacao.conta_id==Conta.id",
                            uselist=False, viewonly=True)

    @property
    def status(self):
        if self.transacao and self.transacao.cancelado:
            return 8
        if self.realizado is None:
            return 1
        base = float(self.previsto) + float(self.variacao or 0)
        return 9 if float(self.realizado) >= base else 2

    @hybrid_property
    def saldo(self):
        return float(self.previsto) + float(self.variacao or 0) - float(self.realizado or 0)

    @saldo.expression
    def saldo(cls):
        return (func.coalesce(cls.previsto, 0) + func.coalesce(cls.variacao, 0)
                - func.coalesce(cls.realizado, 0))


Entity = {
    'id':           {'type': 'ID'},
    'transacao_id': {'type': 'DK'},
    'conta_id':     {'type': 'FK', 'label': 'Conta', 'readonly': True,
                     'lookup': {'model': 'Conta', 'display': 'nome', 'fields': ['nome']}}, 
    'fatura':       {'type': 'TEXT', 'label': 'Fatura', 'readonly': True},
    'documento':    {'type': 'TEXT', 'label': 'Documento'},
    'vencimento':   {'type': 'DATA', 'label': 'Vencimento', 'required': True},
    'recurso_id':   {'type': 'FK', 'label': 'Recurso'},
    'previsto':     {'type': 'NUM', 'label': 'Previsto', 'required': True, 'mask': MVALOR},
    'realizado':    {'type': 'NUM', 'label': 'Realizado', 'mask': MVALOR},
    'variacao':     {'type': 'NUM', 'label': 'Variação', 'mask': MVALOR},
    'saldo':        {'type': 'NUM', 'label': 'Saldo', 'mask': MVALOR,
                     'calc': 'previsto - (realizado or 0) + (variacao or 0)'},
}
