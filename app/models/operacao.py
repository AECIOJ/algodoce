from app.constantes import TIPO_OPERACAO
from app.ajsystem.core.extensions import db


class Operacao(db.Model):
    __tablename__ = "operacao"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.Integer, nullable=False, server_default="1")
    pai_id = db.Column(db.Integer, db.ForeignKey("operacao.id"), nullable=True)
    ordem = db.Column(db.Integer, nullable=False, server_default="0")
    fator = db.Column(db.Integer, nullable=False, server_default="1")
    ativa = db.Column(db.Boolean, default=True)

    pai = db.relationship("Operacao", remote_side="Operacao.id", backref="filhos")

    def __repr__(self):
        return f"<Operacao {self.nome}>"

    @classmethod
    def plano_rows(cls):
        """Linhas do Plano de Contas: itens com índice hierárquico
        (1, 1.1, ...) — seções por tipo são emitidas pelo motor (groups)."""
        todas = cls.query.order_by(cls.ordem, cls.id).all()
        filhos = {}
        for r in todas:
            filhos.setdefault(r.pai_id, []).append(r)

        def assign(nodes, prefix):
            out = []
            for i, n in enumerate(sorted(nodes, key=lambda x: (x.ordem, x.id)), 1):
                idx = f"{prefix}.{i}" if prefix else str(i)
                n.indice = idx
                out.append(n)
                out.extend(assign(filhos.get(n.id, []), idx))
            return out

        rows = []
        for tipo in sorted(TIPO_OPERACAO):
            top = [r for r in filhos.get(None, []) if r.tipo == tipo]
            if top:
                rows.extend(assign(top, str(tipo)))
        return rows
