"""
EDITORS — Registro de tipos de editor (widgets de campo) do framework.

Um editor é um widget de campo que vai além do `<input>` simples
(ex.: multiseleção em modal). Cada Editor declara:

  name    chave de dispatch — coincide com `field.input` (ex.: 'multi')
  macro   macro Jinja em components/form_macros.html que renderiza o widget
  js      assets JS do blueprint ajsystem exigidos pelo editor
  css     assets CSS do blueprint ajsystem exigidos pelo editor
  modal   se o editor usa <dialog> (assets carregados por página de edição)

Para criar um novo editor:
  1. Em fields.py, defina o field type com `'input': '<nome-do-editor>'`
     (ex.: 'RICH' → {'input': 'rich'}).
  2. Registre aqui:  EDITOR_RICH = Editor(name='rich', macro='render_rich', js=..., css=...)
                      EDITORS['rich'] = EDITOR_RICH
  3. Implemente a macro em form_macros.html e o asset JS/CSS em
     app/ajsystem/static/.

O motor (core.edits.editor_assets) coleta os `field.input` usados na página e
injeta via editor_assets() os assets dos editores presentes.
"""
from ajsystem.defs.editor import Editor, EDITOR_MULTI, EDITORS  # noqa: F401


def editor_assets(inputs):
    """Retorna (js, css) — assets dos editores cujos inputs estão em `inputs`."""
    js, css = [], []
    for name in inputs:
        ed = EDITORS.get(name)
        if not ed:
            continue
        for f in ed.js:
            if f not in js:
                js.append(f)
        for f in ed.css:
            if f not in css:
                css.append(f)
    return js, css
