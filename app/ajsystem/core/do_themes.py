#!/usr/bin/env python3
"""Gera `tailwind.daisyui.json` a partir de `Temas` no `app/config.py` do host.

Faz parte do framework (tooling de build): `core/do_themes.py` (padrão `do_*`
de orquestrador — aqui, da geração de temas). O host invoca via
`npm run gen:theme` (package.json) e o resultado alimenta o `tailwind.config.js`.
A raiz do host é detectada a partir da localização do framework
(`<host>/app/ajsystem/...`), podendo ser sobrescrita por argumento:

    python -m app.ajsystem.core.do_themes [config.py] [tailwind.daisyui.json]

Modo `--framework`: gera `tailwind.daisyui.framework.json` a partir do tema
padrão do framework (`defs/themes.DEFAULT_TEMAS`) — base do CSS pré-compilado
de `app/ajsystem/static/css/tailwind.css` para hosts sem build
(`npm run build:css:framework`).

Fonte única de cores do host: `app/config.py`. Os grupos `marca`, `neutras`,
`feedback` e `apoio` mapeiam 1:1 para tokens do tema DaisyUI (as chaves já têm
os nomes do DaisyUI: primary, base-100, success, accent, ...). Este script
achata esses grupos e grava o array de temas consumido por `tailwind.config.js`.

Derivação automática (aplica só a tokens AUSENTES no tema; qualquer token
declarado explicitamente é mantido):

- `base-200`/`base-300`: `base-100` escurecido na direção de `base-content`
  (8% e 22%) — reproduzem a escala de cinza do tema padrão.
- `neutral`: `base-content` clareado em 35%.
- `*-content` (pc/sc/nc/suc/wac/erc/inc/ac): branco, exceto quando o branco
  tiver contraste < 2.6:1 sobre a cor base (ex.: âmbar/aviso) → preto.

O arquivo gerado (`tailwind.daisyui.json`) NÃO deve ser editado à mão — rode
`npm run gen:theme` após alterar cores em `app/config.py`.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

from app.ajsystem.defs.themes import DEFAULT_TEMAS

FRAMEWORK = Path(__file__).resolve().parent.parent  # <host>/app/ajsystem
HOST = FRAMEWORK.parent.parent                      # raiz do host (app/, tailwind.daisyui.json, package.json)
FRAMEWORK_JSON = FRAMEWORK / "tailwind.daisyui.framework.json"
GRUPOS = ("marca", "neutras", "feedback", "apoio")
DERIVADOS = (("base-200", 0.08), ("base-300", 0.22))
CONTEUDOS = {
    "primary": "primary-content",
    "secondary": "secondary-content",
    "neutral": "neutral-content",
    "success": "success-content",
    "warning": "warning-content",
    "error": "error-content",
    "info": "info-content",
    "accent": "accent-content",
}
BRANCO = "#FFFFFF"
PRETO = "#000000"
PISO_CONTRASTE = 2.6  # abaixo disso o conteúdo branco vira preto (âmbar/aviso)


def _hex_rgb(cor):
    cor = cor.lstrip("#")
    if len(cor) == 3:
        cor = "".join(ch * 2 for ch in cor)
    return tuple(int(cor[i : i + 2], 16) for i in (0, 2, 4))


def _rgb_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, round(v))) for v in rgb))


def _mix(a, b, t):
    """Interpola duas cores hex (#RRGGBB) pelo fator t (0..1)."""
    return _rgb_hex(tuple((1 - t) * x + t * y for x, y in zip(_hex_rgb(a), _hex_rgb(b))))


def _lum(cor):
    def chan(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _hex_rgb(cor)
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _conteudo(cor):
    """Branco; preto quando o branco tiver contraste < PISO_CONTRASTE sobre a cor."""
    lum = _lum(cor)
    return BRANCO if 1.05 / (lum + 0.05) >= PISO_CONTRASTE else PRETO


def _carregar_config(caminho):
    """Carrega o `config.py` do host como módulo avulso (evita o `app/__init__`)."""
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

    base = tema.get("base-100")
    texto = tema.get("base-content")
    if base and texto:
        for chave, t in DERIVADOS:
            tema.setdefault(chave, _mix(base, texto, t))
        tema.setdefault("neutral", _mix(texto, BRANCO, 0.35))

    for cor, token in CONTEUDOS.items():
        if cor in tema:
            tema.setdefault(token, _conteudo(tema[cor]))

    if texto:
        tema["--fallback-bc"] = texto
    return tema


def _array_temas(temas):
    array = []
    for nome, cfg in temas.items():
        tema = _tema_daisyui(cfg)
        if tema:
            array.append({nome: tema})
    for extra in ("light", "dark"):
        if extra not in {list(t)[0] for t in array}:
            array.append(extra)
    return array


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Gera o array de temas DaisyUI (tailwind.daisyui.json)."
    )
    parser.add_argument(
        "--framework",
        action="store_true",
        help="usa o tema padrão do framework e grava "
        "app/ajsystem/tailwind.daisyui.framework.json (CSS pré-compilado).",
    )
    parser.add_argument("config", nargs="?", help="caminho do app/config.py do host")
    parser.add_argument("saida", nargs="?", help="caminho do tailwind.daisyui.json de saída")
    args = parser.parse_args(argv or sys.argv[1:])

    if args.framework:
        array = _array_temas(DEFAULT_TEMAS)
        saida = FRAMEWORK_JSON
    else:
        config = Path(args.config) if args.config else HOST / "app" / "config.py"
        mod = _carregar_config(config)
        array = _array_temas(getattr(mod, "Temas", {}) or {})
        saida = Path(args.saida) if args.saida else HOST / "tailwind.daisyui.json"

    saida.write_text(
        json.dumps(array, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OK: {saida} ({len(array)} temas)")


if __name__ == "__main__":
    main()
