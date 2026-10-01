#!/usr/bin/env python3
"""Incrementa a versão do app (`APP['version']` em `app/config.py`).

Uso:
    python scripts/bump_version.py                 # number + 1, mesmo período
    python scripts/bump_version.py --number 25     # number explícito
    python scripts/bump_version.py --month 11      # vira o período, number volta a 1
    python scripts/bump_version.py --month 11 --year 26 --number 3

Só edita os dígitos do bloco `'version'` (regex cirúrgica no span do dict) e
depois relê o arquivo para provar o que foi escrito: divergência → exit 1
(revise `app/config.py` à mão nesse caso).

`ajsystem/version` (framework) NÃO é tocado: continua manual, pela regra do
assunto (ver README §6).
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / 'app' / 'config.py'

_BLOCO = re.compile(
    r"'version':\s*\{\s*'cycle':\s*(\d+),\s*'year':\s*(\d+),"
    r"\s*'month':\s*(\d+),\s*'number':\s*(\d+)\s*\}")


def _ler():
    texto = CONFIG.read_text()
    m = _BLOCO.search(texto)
    if not m:
        sys.exit("bloco 'version' não encontrado em app/config.py — "
                 "o formato esperado é "
                 "'version': {'cycle': 1, 'year': 26, 'month': 10, 'number': 10}.")
    cycle, year, month, number = (int(g) for g in m.groups())
    return texto, m.span(), {'cycle': cycle, 'year': year,
                             'month': month, 'number': number}


def _texto(v) -> str:
    return f"{v['cycle']}.{v['year']:02d}.{v['month']:02d}-{v['number']:03d}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--month', type=int, default=None)
    ap.add_argument('--year', type=int, default=None)
    ap.add_argument('--number', type=int, default=None)
    args = ap.parse_args()

    texto, (ini, fim), atual = _ler()
    novo = dict(atual)
    if args.month is not None or args.year is not None:
        if args.month is not None:
            novo['month'] = args.month
        if args.year is not None:
            novo['year'] = args.year
        novo['number'] = args.number if args.number is not None else 1
    else:
        novo['number'] = args.number if args.number is not None else atual['number'] + 1

    for chave, valor in novo.items():
        if valor < 0:
            sys.exit(f"{chave}={valor} inválido (negativo).")
    if not 1 <= novo['month'] <= 12:
        sys.exit(f"month={novo['month']} inválido (1–12).")

    bloco = texto[ini:fim]
    for chave in ('cycle', 'year', 'month', 'number'):
        bloco, n = re.subn(rf"'{chave}':\s*\d+", f"'{chave}': {novo[chave]}",
                           bloco, count=1)
        if not n:
            sys.exit(f"chave {chave!r} sumiu do bloco — arquivo fora do padrão?")
    CONFIG.write_text(texto[:ini] + bloco + texto[fim:])

    # Prova: reler e comparar com o pretendido.
    _, _, gravado = _ler()
    if gravado != novo:
        sys.exit(f"verificação falhou: lido {gravado}, pretendido {novo}. "
                 f"Revise app/config.py à mão.")
    print(f"{_texto(atual)} → {_texto(novo)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
