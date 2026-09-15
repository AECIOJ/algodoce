from datetime import timedelta


def parse_prazo_recebimento(texto, data_base, data_entrega=None, total=0.0):
    """Interpreta o prazo de uma carteira e gera os vencimentos.

    Formatos aceitos (case-insensitive):
        vazio      -> à vista, vencimento na data base.
        "N"        -> único vencimento em N dias (ex.: "30").
        "Nx"       -> N parcelas iguais a cada 30 dias (ex.: "3x" -> 30/60/90).
        "P/E"      -> metade na data base e metade na entrega.
        "A/B"      -> vencimentos em A e B dias (ex.: "0/15").
        outro      -> fallback: à vista na data base.
    """
    if not texto or not texto.strip():
        return [{"vencimento": data_base, "previsto": round(total, 2)}]
    texto = texto.strip().upper()

    if texto == "P/E":
        if not data_entrega:
            return [{"vencimento": data_base, "previsto": round(total, 2)}]
        split = total / 2
        return [
            {"vencimento": data_base, "previsto": round(split, 2)},
            {"vencimento": data_entrega, "previsto": round(total - split, 2)},
        ]

    if texto.endswith("X") and texto[:-1].isdigit():
        n = int(texto[:-1])
        if n < 1:
            n = 1
        parcelas = []
        for i in range(1, n + 1):
            parcelas.append({
                "vencimento": data_base + timedelta(days=30 * i),
                "previsto": round(total / n, 2) if i < n else round(total - (total / n) * (n - 1), 2),
            })
        return parcelas

    if texto.isdigit():
        return [{"vencimento": data_base + timedelta(days=int(texto)), "previsto": round(total, 2)}]

    if "/" in texto:
        partes = texto.split("/")
        dias_lista = [int(p.strip()) for p in partes if p.strip().isdigit()]
        n = len(dias_lista)
        if n == 0:
            return [{"vencimento": data_base, "previsto": round(total, 2)}]
        parcelas = []
        for i, dias in enumerate(dias_lista):
            if i == n - 1:
                parcelas.append({
                    "vencimento": data_base + timedelta(days=dias),
                    "previsto": round(total - sum(p["previsto"] for p in parcelas), 2),
                })
            else:
                parcelas.append({
                    "vencimento": data_base + timedelta(days=dias),
                    "previsto": round(total / n, 2),
                })
        return parcelas

    return [{"vencimento": data_base, "previsto": round(total, 2)}]