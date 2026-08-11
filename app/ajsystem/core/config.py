"""Configuração do Flask (lê variáveis de ambiente).

A leitura de configuração é responsabilidade do framework; o app host não
constrói mais config (substituiu o antigo `app.config`). Variáveis lidas de
.env, com nomes documentados:

- POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB
  → montam SQLALCHEMY_DATABASE_URI
- SECRET_KEY
- SESSION_TIMEOUT (0 = sem timeout explícito)

Demais chaves (WTF/SESSION/upload) usam defaults seguros.
"""
import os
from datetime import timedelta


class Config:
    _user = os.getenv("POSTGRES_USER", "algodoce")
    _password = os.getenv("POSTGRES_PASSWORD", "algodoce123")
    _host = os.getenv("POSTGRES_HOST", "pg_18")
    _port = os.getenv("POSTGRES_PORT", "5432")
    _db = os.getenv("POSTGRES_DB", "algodoce")
    SQLALCHEMY_DATABASE_URI = f"postgresql://{_user}:{_password}@{_host}:{_port}/{_db}"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    WTF_CSRF_ENABLED = True
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "0"))
    SEND_FILE_MAX_AGE_DEFAULT = 0
