"""Notificações via ntfy.sh (genérico do framework)."""
import requests


def notificar(topic: str, title: str, message: str,
              tags=None, token: str = ""):
    """Envia notificação para o serviço ntfy.sh. Falhas silenciosas."""
    if not topic:
        return

    payload = {
        "topic": topic,
        "title": title,
        "message": message,
    }
    if tags:
        payload["tags"] = tags

    headers = {}
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
