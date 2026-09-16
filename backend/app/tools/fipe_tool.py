"""
Ferramenta de consulta à Tabela FIPE.

Este módulo é a "ferramenta" do agente: não tem nenhuma inteligência artificial.
Ele apenas recebe parâmetros já extraídos (marca, modelo, ano) e navega a API
pública da FIPE (Parallelum, https://fipe.parallelum.com.br/api/v2) fazendo
requisições HTTP GET reais para encontrar o veículo e retornar seus dados.

Hierarquia da API (confirmada em https://deividfortuna.github.io):
    tipo de veículo -> marca -> modelo -> ano -> preço

A API não aceita nomes livres de marca/modelo/ano: cada nível exige o código
retornado pelo nível anterior. Por isso a função principal navega a hierarquia
inteira, fazendo a correspondência entre o texto informado pelo usuário (via
Gemini) e os nomes reais cadastrados na FIPE.
"""

from __future__ import annotations

import difflib
import unicodedata
from functools import lru_cache
from typing import Any

import requests

FIPE_BASE_URL = "https://fipe.parallelum.com.br/api/v2"
FIPE_TIMEOUT_SEGUNDOS = 10

# Token opcional (ver README) — sem ele a API permite 500 requisições/dia por
# IP, o que é suficiente para uso acadêmico. Se definido, eleva o limite para
# 1.000/dia. Nunca é obrigatório.
_fipe_api_token: str | None = None

# "carros" é o padrão pedido na atividade; motos e caminhões já funcionam,
# bastando o usuário mencionar a categoria.
TIPOS_VEICULO_VALIDOS = {
    "carro": "cars",
    "carros": "cars",
    "automovel": "cars",
    "automóvel": "cars",
    "moto": "motorcycles",
    "motos": "motorcycles",
    "motocicleta": "motorcycles",
    "motocicletas": "motorcycles",
    "caminhao": "trucks",
    "caminhão": "trucks",
    "caminhoes": "trucks",
    "caminhões": "trucks",
}


def configurar_fipe_api_token(token: str | None) -> None:
    """Define o X-Subscription-Token opcional usado nas chamadas à API FIPE."""
    global _fipe_api_token
    _fipe_api_token = token or None


class FipeApiError(Exception):
    """Erro ao consultar a API pública da FIPE (rede, HTTP ou dados inesperados)."""

    def __init__(self, tipo: str, mensagem: str):
        self.tipo = tipo
        self.mensagem = mensagem
        super().__init__(mensagem)


def _normalizar(texto: str) -> str:
    """Remove acentos, baixa a caixa e colapsa espaços para comparação de texto."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.lower().split())


def _get_json(path: str, params: dict[str, Any] | None = None) -> Any:
    """Executa um GET na API da FIPE e retorna o JSON, ou levanta FipeApiError."""
    headers = {"Accept": "application/json"}
    if _fipe_api_token:
        headers["X-Subscription-Token"] = _fipe_api_token

    try:
        resposta = requests.get(
            f"{FIPE_BASE_URL}{path}",
            params=params,
            headers=headers,
            timeout=FIPE_TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.Timeout as exc:
        raise FipeApiError("timeout", "A API da FIPE não respondeu a tempo. Tente novamente em instantes.") from exc
    except requests.exceptions.ConnectionError as exc:
        raise FipeApiError("conexao", "Não foi possível conectar à API da FIPE. Verifique sua conexão.") from exc
    except requests.exceptions.RequestException as exc:
        raise FipeApiError("requisicao", f"Falha ao consultar a API da FIPE: {exc}") from exc

    if resposta.status_code == 200:
        try:
            return resposta.json()
        except ValueError as exc:
            raise FipeApiError("json_invalido", "A API da FIPE retornou uma resposta em formato inesperado.") from exc

    if resposta.status_code == 404:
        raise FipeApiError("nao_encontrado", "Recurso não encontrado na Tabela FIPE para os parâmetros informados.")
    if resposta.status_code == 429:
        raise FipeApiError("limite_excedido", "Limite de requisições da API FIPE foi atingido. Tente novamente mais tarde.")
    if resposta.status_code >= 500:
        raise FipeApiError("servico_indisponivel", "A API da FIPE está indisponível no momento.")

    raise FipeApiError("http_" + str(resposta.status_code), f"A API da FIPE retornou o status HTTP {resposta.status_code}.")


@lru_cache(maxsize=8)
def _listar_marcas(tipo_api: str) -> tuple[dict[str, str], ...]:
    """Lista marcas de um tipo de veículo. Cacheada: marcas mudam raramente."""
    return tuple(_get_json(f"/{tipo_api}/brands"))


@lru_cache(maxsize=64)
def _listar_modelos(tipo_api: str, marca_codigo: str) -> tuple[dict[str, str], ...]:
    """Lista modelos de uma marca. Cacheada para evitar chamadas repetidas."""
    return tuple(_get_json(f"/{tipo_api}/brands/{marca_codigo}/models"))


@lru_cache(maxsize=256)
def _listar_anos(tipo_api: str, marca_codigo: str, modelo_codigo: str) -> tuple[dict[str, str], ...]:
    """Lista anos/versões de combustível de um modelo. Cacheada."""
    return tuple(_get_json(f"/{tipo_api}/brands/{marca_codigo}/models/{modelo_codigo}/years"))


def _melhor_marca(tipo_api: str, marca_usuario: str) -> tuple[dict[str, str] | None, tuple[dict[str, str], ...]]:
    """Encontra a marca cujo nome mais se aproxima do texto informado pelo usuário."""
    marcas = _listar_marcas(tipo_api)
    alvo = _normalizar(marca_usuario)

    exatas = [m for m in marcas if _normalizar(m["name"]) == alvo]
    if exatas:
        return exatas[0], marcas

    contendo = [m for m in marcas if alvo in _normalizar(m["name"])]
    if contendo:
        return contendo[0], marcas

    nomes_normalizados = {_normalizar(m["name"]): m for m in marcas}
    proximos = difflib.get_close_matches(alvo, nomes_normalizados.keys(), n=1, cutoff=0.6)
    if proximos:
        return nomes_normalizados[proximos[0]], marcas

    return None, marcas


def _rankear_modelos(
    modelos: tuple[dict[str, str], ...], modelo_usuario: str
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """
    Separa os modelos em três níveis de confiança pelo texto informado pelo usuário:
    correspondência exata, correspondência por subconjunto de palavras e correspondência
    difusa (fuzzy) por similaridade textual.

    Os nomes de modelo na FIPE incluem detalhes de versão/motorização (ex.:
    "Corolla XEi 2.0 Flex 16V Aut."), então uma busca exata quase nunca bate.
    Importante: dentro de cada nível NÃO se penaliza modelos com nomes mais
    longos/detalhados — um ranking por "menos palavras extras" faria trims
    antigos e genéricos (ex.: "Corolla WG", só vendido até 1999) vencerem
    versões atuais (ex.: "Corolla XEi 2.0 Flex 16V Aut.") sempre que o usuário
    não especifica a versão, o que é o oposto do desejável.
    """
    alvo = _normalizar(modelo_usuario)
    alvo_tokens = set(alvo.split())
    exatos: list[dict[str, str]] = []
    subconjunto: list[dict[str, str]] = []
    difusos: list[tuple[float, dict[str, str]]] = []

    for modelo in modelos:
        nome_normalizado = _normalizar(modelo["name"])
        if nome_normalizado == alvo:
            exatos.append(modelo)
            continue

        tokens_modelo = set(nome_normalizado.split())
        if alvo_tokens and alvo_tokens.issubset(tokens_modelo):
            subconjunto.append(modelo)
            continue

        similaridade = difflib.SequenceMatcher(None, alvo, nome_normalizado).ratio()
        if alvo in nome_normalizado or similaridade > 0.5:
            difusos.append((similaridade, modelo))

    difusos.sort(key=lambda item: item[0], reverse=True)
    return exatos, subconjunto, [modelo for _, modelo in difusos]


def _ano_para_codigo(anos: tuple[dict[str, str], ...], ano_usuario: str) -> dict[str, str] | None:
    """Encontra o código de ano (ex.: '2022-5') correspondente ao ano informado (ex.: '2022')."""
    alvo = str(ano_usuario).strip()[:4]
    for ano in anos:
        if ano["code"].split("-")[0] == alvo:
            return ano
    return None


def _anos_disponiveis_legiveis(anos: tuple[dict[str, str], ...], limite: int = 10) -> list[str]:
    """Lista anos reais disponíveis (ignorando o placeholder '32000' da FIPE) para mensagens de erro."""
    anos_unicos = sorted({ano["code"].split("-")[0] for ano in anos if ano["code"].split("-")[0] != "32000"}, reverse=True)
    return anos_unicos[:limite]


# Se a correspondência por subconjunto de palavras encontrar mais candidatos do
# que isso, o nome do modelo é considerado genérico demais (ex.: "Corolla" sem
# versão) e a função retorna um erro de ambiguidade em vez de arriscar checar
# o ano em dezenas de trims diferentes (o que também violaria o cuidado de não
# fazer excesso de chamadas à API pública).
LIMITE_MODELOS_AMBIGUOS = 6

# Número máximo de modelos candidatos testados contra o ano pedido.
LIMITE_TENTATIVAS_DE_ANO = 5


def consultar_preco_fipe(marca: str, modelo: str, ano: str, tipo_veiculo: str = "carros") -> dict[str, Any]:
    """
    Consulta o preço médio de um veículo na Tabela FIPE através da API pública.

    Esta é a ÚNICA função exposta ao Gemini como ferramenta (function calling).
    Internamente ela executa a navegação hierárquica completa da API
    (tipo -> marca -> modelo -> ano -> preço), mas para o modelo de IA ela se
    comporta como uma chamada única: recebe marca/modelo/ano e devolve um
    dicionário de resultado (sucesso ou erro), sempre com dados reais vindos
    da API — nunca inventados.

    Args:
        marca: Marca/fabricante do veículo (ex.: "Toyota", "Honda").
        modelo: Modelo e, se possível, a versão do veículo (ex.: "Corolla XEi").
        ano: Ano-modelo do veículo (ex.: "2022").
        tipo_veiculo: "carros", "motos" ou "caminhoes". Padrão: "carros".

    Returns:
        Em caso de sucesso: {"sucesso": True, "marca", "modelo", "ano_modelo",
        "combustivel", "preco", "codigo_fipe", "mes_referencia", "tipo_veiculo"}.
        Em caso de falha: {"sucesso": False, "erro": <categoria>, "mensagem": <texto>,
        e opcionalmente "sugestoes" ou "anos_disponiveis"}.
    """
    if not marca or not str(marca).strip():
        return {"sucesso": False, "erro": "parametros_invalidos", "mensagem": "É necessário informar a marca do veículo."}
    if not modelo or not str(modelo).strip():
        return {"sucesso": False, "erro": "parametros_invalidos", "mensagem": "É necessário informar o modelo do veículo."}
    if not ano or not str(ano).strip():
        return {"sucesso": False, "erro": "parametros_invalidos", "mensagem": "É necessário informar o ano do veículo."}

    tipo_api = TIPOS_VEICULO_VALIDOS.get(_normalizar(tipo_veiculo))
    if tipo_api is None:
        return {
            "sucesso": False,
            "erro": "tipo_invalido",
            "mensagem": f"Tipo de veículo '{tipo_veiculo}' não reconhecido. Utilize carros, motos ou caminhões.",
        }

    try:
        marca_info, marcas = _melhor_marca(tipo_api, marca)
        if marca_info is None:
            return {
                "sucesso": False,
                "erro": "marca_nao_encontrada",
                "mensagem": f"Não encontrei a marca '{marca}' na Tabela FIPE.",
                "sugestoes": [m["name"] for m in marcas[:5]],
            }

        modelos = _listar_modelos(tipo_api, marca_info["code"])
        exatos, subconjunto, difusos = _rankear_modelos(modelos, modelo)

        # Só é tratado como ambíguo quando NÃO há nenhuma correspondência exata
        # para desempatar — um nome exato como "CG 160 TITAN" deve continuar
        # sendo tentado (e complementado por variantes próximas) mesmo que
        # existam outras variantes parecidas, pois o usuário foi preciso.
        if not exatos and len(subconjunto) > LIMITE_MODELOS_AMBIGUOS:
            return {
                "sucesso": False,
                "erro": "modelo_ambiguo",
                "mensagem": (
                    f"Encontrei {len(subconjunto)} versões diferentes de '{modelo}' para a marca "
                    f"{marca_info['name']}. Preciso que você especifique a versão exata."
                ),
                "sugestoes": [m["name"] for m in subconjunto[:8]],
            }

        # Correspondências exatas vêm primeiro, complementadas por variantes
        # próximas: o nome exato pode não ter o ano pedido (ex.: "CG 160
        # TITAN" só existe hoje sob um nome de edição especial), então vale
        # tentar algumas variantes antes de desistir.
        candidatos = exatos + subconjunto[:LIMITE_TENTATIVAS_DE_ANO]
        if not candidatos:
            candidatos = difusos[:LIMITE_TENTATIVAS_DE_ANO]
        if not candidatos:
            return {
                "sucesso": False,
                "erro": "modelo_nao_encontrado",
                "mensagem": f"Não encontrei o modelo '{modelo}' para a marca {marca_info['name']}.",
                "sugestoes": [m["name"] for m in modelos[:5]],
            }

        for candidato in candidatos[:LIMITE_TENTATIVAS_DE_ANO]:
            anos = _listar_anos(tipo_api, marca_info["code"], candidato["code"])
            ano_info = _ano_para_codigo(anos, ano)
            if ano_info is None:
                continue

            dados = _get_json(
                f"/{tipo_api}/brands/{marca_info['code']}/models/{candidato['code']}/years/{ano_info['code']}"
            )
            return {
                "sucesso": True,
                "marca": dados.get("brand"),
                "modelo": dados.get("model"),
                "ano_modelo": dados.get("modelYear"),
                "combustivel": dados.get("fuel"),
                "preco": dados.get("price"),
                "codigo_fipe": dados.get("codeFipe"),
                "mes_referencia": dados.get("referenceMonth"),
                "tipo_veiculo": tipo_veiculo,
            }

        anos_do_melhor_candidato = _listar_anos(tipo_api, marca_info["code"], candidatos[0]["code"])
        return {
            "sucesso": False,
            "erro": "ano_nao_encontrado",
            "mensagem": (
                f"Encontrei o modelo '{candidatos[0]['name']}' da marca {marca_info['name']}, "
                f"mas não há dados na FIPE para o ano {ano}."
            ),
            "anos_disponiveis": _anos_disponiveis_legiveis(anos_do_melhor_candidato),
        }

    except FipeApiError as exc:
        return {"sucesso": False, "erro": exc.tipo, "mensagem": exc.mensagem}
