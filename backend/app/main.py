"""
Ponto de entrada da API FastAPI do FIPE AI.

Arquitetura: Frontend (Next.js) -> FastAPI (este serviço) -> Gemini (function
calling) -> ferramenta Python -> API pública da FIPE -> Gemini -> Frontend.
A chave do Gemini só existe aqui no backend; o frontend nunca tem acesso a ela.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.chat import router as chat_router

app = FastAPI(
    title="FIPE AI",
    description="Agente inteligente para consulta de preços de veículos na Tabela FIPE via Gemini Function Calling.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
