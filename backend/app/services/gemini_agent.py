"""
Serviço do agente Gemini — aqui mora a "IA" do projeto.

Este módulo é responsável por tudo que envolve inteligência artificial:
interpretar a pergunta do usuário, decidir quando consultar a ferramenta,
extrair os parâmetros e transformar o resultado em uma resposta em linguagem
natural. Ele NUNCA fala HTTP diretamente com a API da FIPE — quando o Gemini
decide usar a ferramenta `consultar_preco_fipe`, a execução é delegada ao
módulo `app.tools.fipe_tool`, que é quem efetivamente acessa a API externa.

Fluxo implementado manualmente (function calling "manual", não automático do
SDK) para que cada etapa fique visível e logável — decisão do modelo, nome da
função, argumentos, execução, resultado e resposta final — conforme exigido
pela atividade acadêmica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types
from starlette.concurrency import run_in_threadpool

from app.tools.fipe_tool import consultar_preco_fipe

SYSTEM_INSTRUCTION = """Você é o FIPE AI, um assistente que ajuda pessoas a consultar preços de veículos na Tabela FIPE brasileira.

Regras importantes:
1. Você nunca sabe o preço de um veículo de antemão. A única forma de descobrir é chamando a função consultar_preco_fipe.
2. Se o usuário não informar claramente marca, modelo e ano, peça essas informações antes de chamar a função. Não presuma valores.
3. Depois de receber o resultado da função, use somente os dados retornados para responder. Nunca invente ou arredonde valores.
4. Se a função retornar um erro (marca/modelo/ano não encontrado, ambiguidade entre versões, etc.), explique o problema de forma clara e amigável, aproveitando as sugestões retornadas para orientar o usuário a reformular a pergunta.
5. Sempre cite o mês/ano de referência da tabela na resposta final, quando disponível.
6. Seja objetivo e cordial, respondendo sempre em português do Brasil.
"""

CONSULTAR_PRECO_FIPE_DECLARATION = types.FunctionDeclaration(
    name="consultar_preco_fipe",
    description=(
        "Consulta o preço médio de referência de um veículo na Tabela FIPE através de uma "
        "API pública oficial de dados da FIPE. Use sempre que o usuário perguntar quanto "
        "vale, qual o preço, cotação ou valor de revenda de um veículo específico. É "
        "necessário saber marca, modelo e ano; se alguma dessas informações não estiver "
        "clara na pergunta do usuário, peça esclarecimento ANTES de chamar esta função."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "marca": types.Schema(
                type=types.Type.STRING,
                description="Marca/fabricante do veículo, por exemplo: Toyota, Honda, Volkswagen.",
            ),
            "modelo": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Modelo do veículo, incluindo a versão/trim quando o usuário mencionar "
                    "(ex.: 'Corolla XEi', 'CG 160 Titan', 'Gol 1.0')."
                ),
            ),
            "ano": types.Schema(
                type=types.Type.STRING,
                description="Ano-modelo do veículo, por exemplo: '2022'.",
            ),
            "tipo_veiculo": types.Schema(
                type=types.Type.STRING,
                description="Categoria do veículo. Use 'carros' quando não for possível inferir outra categoria.",
                enum=["carros", "motos", "caminhoes"],
            ),
        },
        required=["marca", "modelo", "ano"],
    ),
)

FIPE_TOOL = types.Tool(function_declarations=[CONSULTAR_PRECO_FIPE_DECLARATION])

FUNCOES_DISPONIVEIS = {
    "consultar_preco_fipe": consultar_preco_fipe,
}


@dataclass
class PassoAgente:
    """Um passo do raciocínio do agente (para logging/depuração e para a API expor a UI)."""

    tipo: str  # "function_call" | "function_result" | "resposta_final"
    detalhes: dict[str, Any] = field(default_factory=dict)


@dataclass
class RespostaAgente:
    texto: str
    passos: list[PassoAgente]
    veiculo: dict[str, Any] | None = None


@lru_cache(maxsize=1)
def _obter_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def _config(model: str) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(tools=[FIPE_TOOL], system_instruction=SYSTEM_INSTRUCTION)


async def perguntar_ao_agente(pergunta: str, api_key: str, model: str) -> RespostaAgente:
    """Executa uma rodada completa do agente: pergunta -> (function calling) -> resposta final."""
    client = _obter_client(api_key)
    config = _config(model)
    passos: list[PassoAgente] = []

    contents: list[types.Content] = [types.Content(role="user", parts=[types.Part(text=pergunta)])]

    resposta = await client.aio.models.generate_content(model=model, contents=contents, config=config)
    candidate_content = resposta.candidates[0].content
    partes = candidate_content.parts or []
    function_call_part = next((p for p in partes if p.function_call), None)

    if function_call_part is None:
        texto = resposta.text or ""
        passos.append(PassoAgente(tipo="resposta_final", detalhes={"texto": texto}))
        return RespostaAgente(texto=texto, passos=passos, veiculo=None)

    function_call = function_call_part.function_call
    nome_funcao = function_call.name
    argumentos = dict(function_call.args or {})
    passos.append(PassoAgente(tipo="function_call", detalhes={"nome": nome_funcao, "argumentos": argumentos}))

    contents.append(candidate_content)

    funcao_python = FUNCOES_DISPONIVEIS.get(nome_funcao)
    if funcao_python is None:
        resultado: dict[str, Any] = {
            "sucesso": False,
            "erro": "funcao_desconhecida",
            "mensagem": f"Função '{nome_funcao}' não está implementada.",
        }
    else:
        resultado = await run_in_threadpool(funcao_python, **argumentos)

    passos.append(PassoAgente(tipo="function_result", detalhes={"resultado": resultado}))

    function_response_part = types.Part.from_function_response(name=nome_funcao, response={"result": resultado})
    contents.append(types.Content(role="user", parts=[function_response_part]))

    resposta_final = await client.aio.models.generate_content(model=model, contents=contents, config=config)
    texto_final = resposta_final.text or ""
    passos.append(PassoAgente(tipo="resposta_final", detalhes={"texto": texto_final}))

    veiculo = resultado if resultado.get("sucesso") else None
    return RespostaAgente(texto=texto_final, passos=passos, veiculo=veiculo)
