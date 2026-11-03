# Plano — Gráficos desacoplados no AJSYSTEM

> Documento de planejamento. Nada implementado ainda.
> Toda alteração em `ajsystem/` exige aprovação explícita antes de codar.

## 1. Objetivo

Adicionar gráficos ao sistema espelhando a estrutura declarativa de `REPORT`:

- app declara **spec** (dict puro);
- motor resolve **dados** (agnóstico de lib);
- um **renderer** desenha (tela, PDF, imagem).

Isso permite: mesma declaração → gráfico interativo na tela **e** imagem no PDF.

## 2. Arquitetura (3 camadas)

```
app/charts/*.py          → ChartSpec (dict puro)
ajsystem/defs/chart.py   → dataclasses + parse_chart
ajsystem/core/do_chart.py→ resolve_chart → ChartDataset (neutro)
ajsystem/render/*.py     → ChartJsRenderer | MatplotlibRenderer | TableRenderer
```

Contrato principal:

```
ChartSpec (app) → resolve_chart → ChartDataset (neutro) → renderer
```

`ChartDataset` **não pode** conhecer opções de Chart.js/ECharts. Se opções da lib vazarem para os dados, o desacoplamento se perde.

## 3. Dataclasses propostas (`ajsystem/defs/chart.py`)

```python
@dataclass
class ChartSeries:
    field: str
    label: str | None = None
    agg: str | None = None              # sum|avg|min|max|count (semântica de ReportColumn)
    calc: Callable | str | None = None  # coluna virtual, regra do REPORT
    type: str | None = None             # bar|line|area|scatter (sobrepõe ChartSpec.kind)
    axis: str = 'y'                     # y | y2
    color: str | None = None
    stack: str | None = None
    format: str | None = None           # máscara de exibição (não afeta o dado)

@dataclass
class ChartAxis:
    field: str | None = None            # categoria (default: 1ª coluna não-série do source)
    type: str = 'category'              # category|time|number
    label: str | None = None
    format: str | None = None
    order: str | None = None            # asc|desc|decl
    limit: int | None = None            # top N
    bucket: str | None = None           # day|month|year (para type='time')

@dataclass
class ChartOptions:
    stacked: bool = False
    horizontal: bool = False
    legend: bool = True
    tooltip: bool = True
    grid: bool = True
    palette: str | None = None
    height: int = 320
    responsive: bool = True

@dataclass
class ChartSpec:
    label: str
    kind: str = 'bar'                   # bar|line|area|pie|donut|scatter
    source: str | dict | object | None = None
    filter: Any = None                  # mesma gramática de ReportBody.filter
    x: ChartAxis = field(default_factory=ChartAxis)
    series: list[ChartSeries] = field(default_factory=list)
    options: ChartOptions = field(default_factory=ChartOptions)
    limit: int | None = None

@dataclass
class ChartDataset:
    labels: list                        # eixo X
    series: list[dict]                  # {'name','data','type','axis','color','stack'}
    meta: dict                          # title, subtitle, filters, total, empty, warnings
```

Funções:

```python
def parse_chart(spec) -> ChartSpec: ...
def resolve_chart(spec, *, entity=None, filter=None) -> ChartDataset: ...
```

## 4. Renderers (Protocol)

```python
class ChartRenderer(Protocol):
    def render(self, ds: ChartDataset, spec: ChartSpec) -> str: ...
```

| Renderer | Uso |
|---|---|
| `ChartJsRenderer` | JSON `{type,data,options}` para tela |
| `MatplotlibRenderer` | PNG (backend Agg) 200–300 dpi para PDF |
| `TableRenderer` | fallback acessível / testes |
| `PdfChartRenderer` | embute o PNG no `ReportBody` (fase 2) |

## 5. Ferramentas — decisão

| Cenário | Ferramenta | Motivo |
|---|---|---|
| Gráfico na tela | **Chart.js 4 (UMD, vendorizado)** | MIT, ~200KB, canvas, responsivo, sem build, offline |
| PDF (fpdf2 já existe no projeto) | **Matplotlib (Agg) → PNG** | determinístico, sem browser; Pillow já instalado |
| Exportar PNG no navegador | Chart.js `toBase64Image()` | client-side, sem backend |
| Dashboard avançado (opcional) | ECharts ou Plotly | só se precisar heatmap/sankey/gauge |
| Evitar | Seaborn como camada; Plotly+Kaleido no núcleo | Seaborn é wrapper; Kaleido puxa Chromium (~100MB) e é frágil em Docker |

Análise da tabela comparativa original:

- Mistura eixos: camada (back/front) × finalidade (PDF/dashboard). Chart.js, Matplotlib e Plotly não são alternativas entre si.
- Ignora que o motor atual já gera PDF com fpdf2 e já embute imagens (logo via Pillow).
- Seaborn não é escolha de arquitetura.
- Plotly no backend exige `kaleido` (Chromium) — caro para este projeto.
- "Impressão pelo navegador" não se aplica: a aba Relatórios imprime via `/report-action` → PDF do servidor; o canvas do Chart.js não entra nesse PDF automaticamente.
- Falta o caso central: tela interativa **e** PDF no servidor com os mesmos dados.

## 6. Uso no app

### 6.1 Estrutura de arquivos

```
app/charts/__init__.py
app/charts/receber.py      ← specs (dict puro, igual RECEBER)
app/routes/sys/receber.py  ← importa e registra em Page.props.chart
```

### 6.2 Declaração da spec (`app/charts/receber.py`)

```python
from ajsystem.defs.constants import TODAY
from app.reports.receber import QRECEBER

# Barra horizontal: saldo por cliente
SALDO_POR_CLIENTE = {
    'label': 'Saldo por Cliente',
    'kind': 'bar',
    'source': QRECEBER,
    'x': {'field': 'cliente', 'order': 'desc', 'limit': 10},
    'series': [
        {'field': 'saldo', 'agg': 'sum', 'label': 'Saldo'},
    ],
    'options': {'horizontal': True, 'palette': 'aj'},
}

# Linha temporal: previsto x realizado por mês
PREVISTO_REALIZADO = {
    'label': 'Previsto x Realizado',
    'kind': 'line',
    'source': QRECEBER,
    'x': {'field': 'vencimento', 'type': 'time', 'bucket': 'month',
          'format': 'mm/yyyy'},
    'series': [
        {'field': 'previsto',  'agg': 'sum', 'label': 'Previsto'},
        {'field': 'realizado', 'agg': 'sum', 'label': 'Realizado'},
    ],
    'options': {'stacked': False, 'legend': True},
}

# Donut: composição por recurso
COMPOSICAO_RECURSO = {
    'label': 'Composição por Recurso',
    'kind': 'donut',
    'source': QRECEBER,
    'x': {'field': 'recurso', 'order': 'desc'},
    'series': [{'field': 'saldo', 'agg': 'sum', 'label': 'Saldo'}],
    'options': {'legend': True, 'palette': 'aj'},
}
```

Equivalência com o Report:

| Chart | Equivalente no Report |
|---|---|
| `source` | `body.source` (entity, query dict/QPLANO ou pivot) |
| `filter` | `body.filter` / `entry.filter` |
| `x` | coluna de agrupamento (`group: '*'`) |
| `series[].agg` | `ReportColumn.agg` |
| `series[].calc` | `calc` virtual do REPORT |
| `options` | `Report` (page_size, font…) |

### 6.3 Registro na `Page` (`app/routes/sys/receber.py`)

```python
from app.charts.receber import (
    SALDO_POR_CLIENTE, PREVISTO_REALIZADO, COMPOSICAO_RECURSO)

Page = {
    'label': 'Conta a Receber',
    'props': {
        'scripts': ['previsoes'],
        'tabs': {
            'Dados':      {'type': 'List'},
            'Filtros':    {'type': 'Filter'},
            'Relatórios': {'type': 'Report'},
            'Gráficos':   {'type': 'Chart'},     # nova aba
        },
        # ... list / filter / form / report existentes ...
        'chart': {
            'Saldo por Cliente': {
                'filter': {'conta_id': '=', 'vencimento': ('<=', TODAY())},
                'chart': SALDO_POR_CLIENTE,
            },
            'Previsto x Realizado': {
                'filter': {'conta_id': '=', 'vencimento': '<>'},
                'chart': PREVISTO_REALIZADO,
            },
            'Composição por Recurso': {
                'chart': COMPOSICAO_RECURSO,
            },
        },
    },
}
```

Semântica do `filter` (idêntica ao Report):

- cada chave vira um input (`conta_id` → select; `vencimento` → data/intervalo);
- `'='`, `'<>'`, `('<=', TODAY())` iguais às do relatório;
- campo vazio não aplica filtro;
- default aparece preenchido.

Nenhuma prop nova em `Field`/`Schema` — tudo na spec/entrada.

### 6.4 Fluxo do motor

```
Page.props.chart → _resolve_chart_entries()
  → {slug, title, chart, fields, variants?}
      → GET /ajsystem/chart-data?page=receber&ch=saldo-por-cliente&<filtros>
          → resolve_chart(spec, filter) → ChartDataset
              → ChartJsRenderer     (tela)
              → MatplotlibRenderer  (PDF)
```

`x.field` e `series[].field` são resolvidos contra o `source` (`QRECEBER.select`), não contra a Entity. Campo inexistente = erro de declaração.

### 6.5 O que o usuário vê

Aba **Gráficos**, um card por entrada, com:

- inputs de filtro idênticos aos de Relatórios;
- gráfico renderizado (Chart.js);
- botões `Limpar`, `Imprimir`/`Exportar PNG`.

`Sintético` não se aplica — o gráfico já é a agregação.

### 6.6 Modo B (fase 2): gráfico dentro do relatório

```python
RECEBER['body']['chart'] = {
    'spec': SALDO_POR_CLIENTE,
    'position': 'after',      # renderiza no PDF via MatplotlibRenderer
}
```

Exige `ReportBody.chart` e `PdfChartRenderer`.

## 7. Componentes a criar/alterar

| Arquivo | Tipo | Conteúdo |
|---|---|---|
| `ajsystem/defs/chart.py` | novo | dataclasses + `parse_chart` |
| `ajsystem/core/do_chart.py` | novo | `resolve_chart`, agregação, `_resolve_chart_entries` |
| `ajsystem/render/chart_js.py` | novo | `ChartJsRenderer` |
| `ajsystem/render/chart_pdf.py` | novo | `MatplotlibRenderer` / `PdfChartRenderer` |
| `ajsystem/static/lib/chart.umd.min.js` | novo | Chart.js vendorizado |
| `ajsystem/static/js/charts.js` | novo | `chartRender` + fetch |
| `ajsystem/templates/components/chart.html` | novo | container/canvas |
| `ajsystem/templates/pages/list.html` | alterar | branch `{% elif t.type == 'Chart' %}` + macro de filtros |
| `ajsystem/core/do_list.py` | alterar | `TAB_TYPES += ('Chart',)` + `_resolve_chart_entries` |
| `ajsystem/__init__.py` | alterar | endpoint `GET /ajsystem/chart-data` |
| `ajsystem/core/do_report.py` | refatorar | extrair `resolve_source` de `_auto_data` para reuso |

## 8. Reuso obrigatório do que já existe

1. **Fonte de dados**: extrair de `do_report._auto_data` um `resolve_source(source, filter, order)` em `ajsystem/core/data_source.py`. `print_report` e `resolve_chart` passam a compartilhar QPLANO, pivot, entity, `_apply_entity`.
2. **Filtros**: mesma gramática literal (`report_filter_from_args`, `compile_conditions`, sentinelas).
3. **`agg`**: mesma semântica de `ReportColumn.agg` / `_aggregate_rows`.
4. **Máscaras/formatação**: `mask`/`format` só na saída, nunca no dado.
5. **Segurança**: endpoint `@login_required`, whitelist `[A-Za-z0-9_]+`, campos resolvidos do Entity/source (sem injeção).

## 9. Performance

- Agregar em SQL (`GROUP BY`), não em Python. `pandas` existe no projeto, mas carregar tudo em memória para agrupar é anti-padrão.
- `limit`/`top N` no `ChartAxis`.
- Cache por `spec + filter` (`lru_cache`/Flask-Caching) quando o dataset for caro.

## 10. Fases

1. **Fase 1 (MVP)**: `defs/chart.py` + `resolve_chart` + `ChartJsRenderer` + endpoint + aba `Chart`.
2. **Fase 2**: `MatplotlibRenderer` + embed no PDF (`ReportBody.chart`).
3. **Fase 3**: pivot como source de gráfico (série = colunas do pivot), cache e exportações.

## 11. Pontos de atenção

- Definir DPI e fonte do gráfico no PDF para não destoar (Courier 10pt do relatório vs DejaVu padrão do Matplotlib).
- Estado vazio ("nenhum dado") e fallback `TableRenderer` para acessibilidade.
- `ChartDataset` neutro: não deixar opções da lib vazarem para a camada de dados.
- `bucket` é essencial para séries temporais; sem ele a formatação vaza para o app via `calc`.

## 12. Props novas que exigem aprovação

| Prop | Onde | Por quê |
|---|---|---|
| `chart` | `Page.props` | registrar entradas (espelho de `report`) |
| `type: 'Chart'` | `tabs` / `TAB_TYPES` | nova aba |
| `bucket` | `ChartAxis` | agrupar data por dia/mês/ano |

Sem isso, o gráfico temporal teria que usar `calc` com `strftime`, empurrando formatação para o app.

## 13. Decisões em aberto

1. Aba **Gráficos** separada ou toggle **Tabela | Gráfico** dentro de Relatórios?
2. Chart.js (recomendado) ou ECharts?
3. Gráfico no PDF já na fase 1 ou na fase 2?
