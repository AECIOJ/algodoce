# Gráficos no `ReportBody` — implementação

> **Status: implementado.** O gráfico é declarado em `Report.body.chart` e sai
> como **PNG dentro do PDF** da aba Relatórios. Não há aba Gráficos separada
> nem renderização no navegador.
>
> Manual de declaração: `ajsystem/README.md` → seção 6 → `body.chart`.

## 1. Objetivo

Adicionar gráficos como **formato de saída do `ReportBody`**, espelhando a
estrutura de `table`:

- o app declara o gráfico dentro do próprio report (`body.chart`);
- o motor resolve os dados (agnóstico de renderer);
- o renderer desenha o PNG, embutido no PDF.

`source`, `filter`, `titles`, `variants` e o sintético vêm do `Report`. O
`chart` não declara fonte, filtro nem aba próprios.

## 2. Fluxo

```
app/reports/*.py          → Report.body.chart (dict puro)
ajsystem/defs/chart.py    → normalize_chart → parse_chart → Chart
ajsystem/core/do_chart.py → resolve_chart → ChartDataset (neutro)
ajsystem/render/chart_pdf.py → MatplotlibRenderer → PNG (Pillow)
ajsystem/core/do_report.py   → embute o PNG no PDF (fpdf2)
```

```
ReportBody.chart → normalize_chart(variant, syn) → parse_chart → Chart
                 → resolve_chart(report, filter) → ChartDataset
                 → MatplotlibRenderer.render(ds, chart) → PNG → PDF
```

`ChartDataset` (`labels`, `series`, `meta`) não conhece Pillow/fpdf2; o layout
é decidido no renderer.

## 3. Camadas

### `ajsystem/defs/chart.py`

- `ChartField` — props de um campo de `cat`/`value`:
  `agg`, `color`, `bucket`, `order`, `limit`, `variants`, `syn`
  (`axis`/`format` são aceitos e reservados).
- `ChartLabel` — `cat`, `value`, `data`, `limit`.
- `ChartOptions` — `legend` (fallback); demais chaves aceitas sem efeito no PDF.
- `Chart` — `title` e `legend` na **raiz**, `type`, `cat`, `value`, `stack`,
  `label`, `options`, `limit`.
- `ChartDataset` — saída neutra: `labels`, `series`, `meta`.
- `normalize_chart` — seleciona variante/sintético e aplica `variants`/`syn`
  **somente dentro de `cat`/`value`**, preservando as props de raiz.
- `parse_chart` — dict ativo → `Chart` tipado.
- `chart_has_syn` — o layout ativo declara `syn`?

### `ajsystem/core/do_chart.py`

- `load_chart(report, variant, syn)` — resolve `ReportBody.chart` no `Chart`
  ativo.
- `resolve_chart(report, filter, variant, syn)` — reusa `_auto_data` do
  relatório (mesma source/filtros) e devolve `ChartDataset`.
- `_build_dataset` — agrupa por `cat` (com `bucket`), agrega `value` com
  `_agg_apply`, ordena por `cat.order`, aplica `limit`/top N e monta `meta`.

### `ajsystem/render/chart_pdf.py`

Renderer Pillow puro (sem Matplotlib), 1080×540 (7,2×3,6 in @150 dpi):

| `type` | Desenho |
|---|---|
| `col` | colunas verticais (default) |
| `bar` | barras horizontais |
| `pie` / `donut` | pizza/rosca com valor por fatia |
| `line` / `area` / `scatter` | aceitos na declaração; no PDF atual caem no renderizador de colunas |

- Título: 34pt bold, centralizado, na margem superior (fora da área de plot).
- Legenda: `top`/`bottom` em linha; `left`/`right` em coluna; `none` omite.
  A largura de cada item é medida com `textbbox` e o conjunto é centralizado
  no eixo.
- Eixos começam em 0; grade e valores em 5 faixas.
- `label.val` imprime o valor sobre barras/fatias; `label.perc` imprime a
  porcentagem (empilhados, um sobre o outro). `label.pos` define a posição:
  `O`=fora da fatia (texto escuro + conector cinza até a borda),
  `I`=dentro da fatia, centralizado (contraste automático pela luminância da
  cor da fatia).
- Fontes DejaVu embutidas em `ajsystem/static/fonts/` (a imagem
  `python:*-slim` não traz TTF; sem elas o Pillow cai no bitmap de 11px).

### `ajsystem/core/do_report.py`

- `_pdf_bytes(..., rp_output)`:
  - `both` → tabela + PNG;
  - `table` → só tabela;
  - `chart` → corpo copiado sem `table`, só o PNG (cabeçalho/rodapé mantidos).
- Falha no gráfico gera `warning` e não invalida o PDF da tabela.

## 4. Saída e tela

- `report_outputs(body)` → `['both','table','chart']` quando há os dois.
- Select **Saída** (`rp_output`) na aba Relatórios, montado a partir de
  `report_outputs`; sem select quando só há uma opção.
- Checkbox **Sintético** aparece se `table.syn` **ou** `chart.syn` existir no
  layout ativo.
- Select **Modo** (`rp_variant`) usa `props.report.variants` e a mesma chave
  numérica em `table`/`chart`.

## 5. Declaração (resumo)

```python
RECEBER = {
    'label': 'Contas a Receber',
    'body': {
        'source': QRECEBER,
        'table': {...},
        'chart': {
            'title': 'Saldo por Cliente',
            'type': 'bar',
            'cat': {'cliente': {'order': 'desc', 'limit': 10}},
            'value': {
                'previsto':  {'color': '#0d6efd'},
                'realizado': {'color': '#198754'},
                'saldo':     {'color': '#dc3545'},
            },
            'stack': {'total': ['previsto', 'realizado', 'saldo']},
            'label': {'cat': 'Cliente', 'value': 'Saldo (R$)', 'val': True},
            'legend': 'bottom',
            'syn': {
                'title': 'Composição por Recurso',
                'type': 'pie',
                'cat': {'recurso': {}},
                'value': {'saldo': {}},
                'label': {'val': True, 'perc': True, 'pos': 'O'},
            },
        },
    },
}
```

## 6. Decisões fechadas

1. `chart` é prop de `ReportBody` (não de `Page.props`), aditivo ao `table` e
   fora do XOR `form`/`table`.
2. Saída **somente PDF**; sem Chart.js, sem aba Gráficos, sem endpoint de
   dados.
3. `type` é `col` (colunas verticais) e `bar` (barras horizontais).
4. `stack` é dict separado `{grupo: [fields]}`; `options.stacked` não existe.
5. `agg` default `'sum'`; `calc` não existe (o cálculo vem da `source`).
6. `title` e `legend` são props de **raiz** do `Chart`.
7. `variants`/`syn` do chart espelham `table` (layout por variante + por
   campo).
8. Um chart por body; vários gráficos = várias entradas de report.
9. Renderer padrão: Pillow (sem nova dependência); `MatplotlibRenderer` é
   apenas o nome histórico da classe.
