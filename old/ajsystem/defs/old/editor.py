"""Spec `Editor` — registro de tipos de editor (widgets de campo).

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

O motor (`core.edits.editor_assets`) coleta os `field.input` usados na página
e injeta os assets dos editores presentes.
"""
from dataclasses import dataclass, field


@dataclass
class Editor:
    name: str
    macro: str
    js: list = field(default_factory=list)
    css: list = field(default_factory=list)
    modal: bool = False


EDITOR_MULTI = Editor(
    name='multi',
    macro='render_multi_ctl',
    js=['js/multi-ctl.js'],
    css=['css/multi-ctl.css'],
    modal=True,
)

EDITORS = {
    'multi': EDITOR_MULTI,
}
