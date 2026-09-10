from app.constantes import TIPO_OPERACAO
from ajsystem.core.extensions import db


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


_INDICE_KEY = None
_INDICE_MAP = {}


def _indice(item):
    rows = Operacao.query.order_by(Operacao.ordem, Operacao.id).all()
    key = tuple((r.id, r.pai_id, r.tipo, r.ordem) for r in rows)
    global _INDICE_KEY
    if _INDICE_KEY != key:
        _INDICE_MAP.clear()
        _INDICE_MAP.update(_numerar(rows))
        _INDICE_KEY = key
    return _INDICE_MAP.get(item.id, '')


def _numerar(rows):
    mapa = {}
    for tipo in sorted({r.tipo for r in rows}):
        filhos = {}
        raizes = []
        for r in (x for x in rows if x.tipo == tipo):
            if r.pai_id is None:
                raizes.append(r)
            else:
                filhos.setdefault(r.pai_id, []).append(r)
        raizes.sort(key=lambda r: (r.ordem, r.id))
        for i, raiz in enumerate(raizes, 1):
            _caminhar(mapa, raiz, filhos, [str(tipo), str(i)])
    return mapa


def _caminhar(mapa, node, filhos, partes):
    mapa[node.id] = '.'.join(partes)
    filhos_ord = sorted(filhos.get(node.id, []), key=lambda r: (r.ordem, r.id))
    for j, ch in enumerate(filhos_ord, 1):
        _caminhar(mapa, ch, filhos, partes + [f'{j:02d}'])


Entity = {
    'id':     {'type': 'ID', 'width': 6},
    'indice': {'type': 'TEXT', 'label': 'Índice', 'width': 6,
               'pos_list': 1, 'pos_filter': 0, 'pos_form': 0,
               'calc': _indice},
    'nome':   {'type': 'TEXT', 'width': 25, 'mask': '@T'},
    'tipo':   {'type': 'LIST', 'width': 12, 'options': TIPO_OPERACAO},
    'fator':  {'type': 'INT', 'width': 8},
    'pai_id': {'type': 'FK', 'label': 'Superior', 'width': 30,
               'lookup': {'display': 'nome', 'when': {'pai_id': None}}},
    'ordem':  {'type': 'INT', 'width': 8},
    'ativa':  {'type': 'BOOL', 'width': 8},
}
