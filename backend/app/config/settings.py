"""
Configuração da aplicação via variáveis de ambiente.

Nenhuma chave de API fica escrita neste repositório: em desenvolvimento, o
arquivo `.env` (não versionado — ver `.gitignore`) é carregado pelo
`python-dotenv`; em produção, as variáveis vêm do ambiente do serviço de
hospedagem.
"""

import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str | None = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Opcional: eleva o limite de requisições não autenticadas da API pública da
# FIPE (ver app/tools/fipe_tool.py). A aplicação funciona normalmente sem ele.
FIPE_API_TOKEN: str | None = os.environ.get("FIPE_API_TOKEN")

CORS_ORIGINS: list[str] = [
    origem.strip()
    for origem in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origem.strip()
]
