"""Catálogo de fontes do framework (genérico, declarativo, sem funções).

`cpp` é ÍNDICE de pitch (impressora de linha): {0: 10, 1: 12, 2: 17, 3: 20}
caracteres por polegada. A col da grade é nominal (`25.4/cpp` mm) — estável
entre famílias; envoltório/corte absorvem a diferença p/ o glifo real.
Negrito/sublinhado vão no texto (`font_style` do item), nunca aqui.

Camadas como `buttons`/`inputs`: `FONTS` (framework) < `app.extends.fonts`
(`Fonts`, só o que diverge) < `Fonts` da rota.
"""
from dataclasses import dataclass


# Chars por polegada por índice cpp.
CPP = {0: 10, 1: 12, 2: 17, 3: 20}

# Largura da col draft em mm (10cpp): base da conta de margens.
DRAFT_COL_MM = 25.4 / CPP[0]


@dataclass(frozen=True)
class Font:
    """Fonte nomeada: família + índice cpp."""
    name: str
    family: str
    cpp: int = 0

    def __post_init__(self):
        if self.cpp not in CPP:
            raise ValueError(f"FONT '{self.name}': cpp deve ser {sorted(CPP)}")


FONTS = {
    'DRAFT': Font(name='DRAFT', family='Courier', cpp=0),
    'NORMAL': Font(name='NORMAL', family='Helvetica', cpp=0),
    'TITLE': Font(name='TITLE', family='Helvetica', cpp=0),
}


def module_fonts(mod) -> dict:
    """Lê o `Fonts` de um módulo de rota ({} se ausente/inválido)."""
    f = getattr(mod, 'Fonts', None)
    return f if isinstance(f, dict) else {}


def resolve_font(name, cpp=None, types=()):
    """Preset (framework < app < página) ou família crua + cpp obrigatório.

    Retorna {family, cpp, col}. fail-fast nomeando.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("FONT: nome deve ser str não vazia")
    chain = [FONTS]
    for layer in (types or ()):
        if isinstance(layer, dict) and layer:
            chain.append(layer)
    found = None
    for layer in reversed(chain):
        if name in layer:
            found = layer[name]
            break
    if found is None:
        if cpp is None:
            raise ValueError(f"FONT '{name}' desconhecida {sorted(FONTS)} (passe cpp p/ família crua)")
        if cpp not in CPP:
            raise ValueError(f"FONT: cpp deve ser {sorted(CPP)}")
        return {'family': name, 'cpp': cpp, 'col': 25.4 / CPP[cpp]}
    if isinstance(found, Font):
        _family, _cpp = found.family, found.cpp
    elif isinstance(found, dict):
        _family, _cpp = found.get('family', name), found.get('cpp', 0)
    elif isinstance(found, (list, tuple)) and len(found) == 2:
        _family, _cpp = found
    else:
        raise ValueError(f"FONT '{name}': entrada inválida (Font, dict ou (família, cpp))")
    if cpp is not None:
        if cpp not in CPP:
            raise ValueError(f"FONT: cpp deve ser {sorted(CPP)}")
        _cpp = cpp
    return {'family': _family, 'cpp': _cpp, 'col': 25.4 / CPP[_cpp]}
