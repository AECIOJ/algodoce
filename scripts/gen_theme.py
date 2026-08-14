#!/usr/bin/env python3
"""Gera `tailwind.daisyui.json` a partir de `Temas` em `app/config.py`.

Fonte única de cores do app: `app/config.py`. Os grupos `marca`, `neutras`,
`feedback` e `apoio` mapeiam 1:1 para tokens do tema DaisyUI (as chaves já têm
os nomes do DaisyUI: primary, base-100, success, accent, ...). Este script
achata esses grupos e grava o array de temas consumido por `tailwind.config.js`.

Uso (npm roda como prebuild de build:css/watch:css):

    python scripts/gen_theme.py

O arquivo gerado (`tailwind.daisyui.json`) NÃO deve ser editado à mão — rode
`npm run gen:theme` após alterar cores em `app/config.py`.
"""
import importlib.util
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GRUPOS = ("marca", "neutras", "feedback", "apoio")


def _carregar_config():
    """Carrega `app/config.py` como módulo avulso (evita `app/__init__`)."""
    caminho = RAIZ / "app" / "config.py"
    spec = importlib.util.spec_from_file_location("_app_config_gen", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_app_config_gen"] = mod
    spec.loader.exec_module(mod)
    return mod


def _tema_daisyui(cfg):
    tema = {}
    for grupo in GRUPOS:
        for chave, valor in (cfg.get(grupo) or {}).items():
            if valor:
                tema[chave] = valor
    base_content = (cfg.get("neutras") or {}).get("base-content")
    if base_content:
        tema["--fallback-bc"] = base_content
    return tema


def main():
    mod = _carregar_config()
    temas = getattr(mod, "Temas", {}) or {}
    saida = []
    for nome, cfg in temas.items():
        tema = _tema_daisyui(cfg)
        if tema:
            saida.append({nome: tema})
    for extra in ("light", "dark"):
        if extra not in {list(t)[0] for t in saida}:
            saida.append(extra)
    (RAIZ / "tailwind.daisyui.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OK: tailwind.daisyui.json ({len(saida)} temas)")


if __name__ == "__main__":
    main()
