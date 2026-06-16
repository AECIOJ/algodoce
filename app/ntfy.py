from app.models.setting import Setting
import requests


def notificar(quote):
    topic = Setting.get("ntfy_topic")
    if not topic:
        return

    cliente = quote.cliente_nome or "?"
    telefone = quote.cliente_telefone or "?"

    items = []
    for item in quote.items:
        nome = item.product.nome if item.product else "?"
        items.append(f"- {item.quantidade}x {nome}")

    event = quote.event
    extra = ""
    if event:
        if event.tipo:
            extra += f" | {event.tipo}"
        if event.data:
            extra += f" | {event.data.strftime('%d/%m')}"

    title = "Algodoce recebeu um novo orçamento"
    message = f"Cliente: {cliente}\nFone: {telefone}{extra}\n" + "\n".join(items)

    payload = {
        "topic": topic,
        "title": title,
        "message": message,
        "tags": ["envelope"],
    }

    headers = {}
    token = Setting.get("ntfy_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        requests.post(
            "https://ntfy.sh",
            json=payload,
            headers=headers,
            timeout=5,
        )
    except requests.RequestException:
        pass
