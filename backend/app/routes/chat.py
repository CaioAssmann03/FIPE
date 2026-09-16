"""Rota HTTP do agente: recebe uma pergunta em linguagem natural e devolve a resposta do Gemini."""

from fastapi import APIRouter, HTTPException
from google.genai import errors as genai_errors

from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse, ToolCall, VehicleResult
from app.services.gemini_agent import perguntar_ao_agente
from app.tools.fipe_tool import configurar_fipe_api_token

router = APIRouter()

configurar_fipe_api_token(settings.FIPE_API_TOKEN)


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """
    Recebe `{"message": "..."}`, envia ao agente Gemini e devolve a resposta em
    linguagem natural junto com os dados estruturados do veículo (quando a
    ferramenta consultar_preco_fipe foi usada com sucesso).
    """
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY não configurada no servidor. Defina a variável de ambiente antes de iniciar a API.",
        )

    try:
        resultado = await perguntar_ao_agente(payload.message, settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
    except genai_errors.APIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao comunicar com a API do Gemini: {exc.message if hasattr(exc, 'message') else exc}",
        ) from exc

    tool_call = None
    for passo in resultado.passos:
        if passo.tipo == "function_call":
            tool_call = ToolCall(name=passo.detalhes["nome"], arguments=passo.detalhes["argumentos"])

    vehicle = None
    error = None
    if resultado.veiculo:
        dados = resultado.veiculo
        vehicle = VehicleResult(
            brand=str(dados.get("marca", "")),
            model=str(dados.get("modelo", "")),
            year=str(dados.get("ano_modelo", "")),
            price=str(dados.get("preco", "")),
            reference=str(dados.get("mes_referencia", "")),
            fipe_code=str(dados.get("codigo_fipe", "")),
        )
    else:
        for passo in resultado.passos:
            if passo.tipo == "function_result" and not passo.detalhes["resultado"].get("sucesso", True):
                error = passo.detalhes["resultado"].get("erro")

    return ChatResponse(response=resultado.texto, vehicle=vehicle, tool_call=tool_call, error=error)
