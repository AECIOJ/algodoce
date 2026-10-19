# Diretrizes do Projeto - AJSYSTEM

## 1. Contexto Tecnológico
- **Stack:** Python 3.10+, Flask 3.0, Flask-SQLAlchemy, PostgreSQL (via Docker).
- **Arquitetura:** Framework declarativo AJSYSTEM (`Entity`, `Schema`, `Page`, `Field`).
- **Ambiente:** WSL / Ubuntu no Windows, editado via VS Code.

## 2. Gerenciamento de Contexto (Repomix)
- Sempre que for necessária uma análise ampla da estrutura do código-fonte ou do repositório, execute o `repomix` via terminal para gerar o arquivo consolidado de contexto de forma leve.
- Utilize a saída do Repomix para mapear dependências e arquivos, evitando varreduras manuais pesadas no sistema de arquivos para prevenir travamentos de I/O no WSL.

## 3. Padrões de Desenvolvimento AJSYSTEM
- **Modelos e Entidades:** `Entity` definida em `app/models/*.py`.
- **Overrides e Telas:** `Schema` e `Page` definidos em `app/routes/sys/*.py`.
- **Versionamento:** O versionamento do framework segue o formato `ciclo.ano.mes.dia.seq` (`ajsystem/version`). A versão do app hospedeiro fica em `APP['version']` (`app/config.py`).