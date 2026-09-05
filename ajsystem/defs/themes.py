"""Tema padrão do framework — base do CSS pré-compilado (`static/css/tailwind.css`).

Hosts sem pipeline de build copiam esse CSS pronto para o próprio
`app/static/css/tailwind.css` (§2.6 do README). Para um host COM build, o tema
é o `Temas` do `app/config.py` (este padrão é apenas o fallback).

Regeneração do CSS pré-compilado:

    npm run build:css:framework   # gera tailwind.daisyui.framework.json + compila

As cores usam a mesma estrutura de `Temas` do host; os tokens derivados
(base-200/300, neutral, *-content) são calculados por `core/do_themes.py`.
"""

DEFAULT_TEMAS = {
    "ajsystem": {
        "base": "ajsystem",
        "rotulo": "AJSystem",
        "marca": {
            "primary": "#2563EB",    # azul
            "secondary": "#DB2777",  # magenta
        },
        "neutras": {
            "base-100": "#f5f5f5",   # superfície do app
            "base-content": "#212121",
        },
        "feedback": {
            "success": "#16A34A",
            "warning": "#F59E0B",
            "error": "#DC2626",
            "info": "#0284C7",
        },
        "apoio": {
            "accent": "#F59E0B",
        },
    },
}
