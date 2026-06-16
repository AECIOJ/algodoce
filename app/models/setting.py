from datetime import datetime, timezone
from app.extensions import db
from app.crypto import encrypt, decrypt

class Setting(db.Model):
    KEYS = {
        "doceira_telefone": "Telefone",
        "doceira_email": "E-mail",
        "doceira_nome": "Nome",
        "ntfy_topic": "Tópico",
        "ntfy_token": "Token",
        "painel_usuario": "Usuário",
        "painel_senha": "Senha",
        "painel_chave": "Chave",

    }
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    encrypted_value = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def value(self) -> str:
        return decrypt(self.encrypted_value) if self.encrypted_value else ""

    @value.setter
    def value(self, raw: str):
        self.encrypted_value = encrypt(raw) if raw else ""

    @property
    def label(self) -> str:
        return self.KEYS.get(self.key, self.key)

    @classmethod
    def get(cls, key: str) -> str:
        obj = cls.query.filter_by(key=key).first()
        return obj.value if obj else ""

    @classmethod
    def set(cls, key: str, raw: str):
        obj = cls.query.filter_by(key=key).first()
        if not obj:
            obj = cls(key=key)
            db.session.add(obj)
        obj.value = raw
        obj.updated_at = datetime.now(timezone.utc)

    @classmethod
    def ensure_keys(cls):
        DEFAULTS = {
            "painel_usuario": "doceira",
            "painel_senha": "doceira",
        }
        for k in cls.KEYS:
            existing = cls.query.filter_by(key=k).first()
            if not existing:
                val = DEFAULTS.get(k, "")
                db.session.add(cls(key=k, encrypted_value=encrypt(val) if val else ""))
        db.session.commit()
