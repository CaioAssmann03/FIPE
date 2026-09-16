"""Modelos Pydantic do contrato HTTP da API (requisição/resposta do endpoint /chat)."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Pergunta do usuário em linguagem natural.")


class ToolCall(BaseModel):
    """Registra qual ferramenta o Gemini decidiu usar e com quais argumentos, para fins de demonstração."""

    name: str
    arguments: dict


class VehicleResult(BaseModel):
    brand: str
    model: str
    year: str
    price: str
    reference: str
    fipe_code: str


class ChatResponse(BaseModel):
    response: str
    vehicle: VehicleResult | None = None
    tool_call: ToolCall | None = None
    error: str | None = None
