# FIPE AI — Agente Inteligente de Consulta da Tabela FIPE

> Consulte preços da Tabela FIPE usando Inteligência Artificial.

Projeto acadêmico para a disciplina de Inteligência Artificial — **Atividade 1: Agente com ferramenta**. Demonstra um agente construído com **Gemini Function Calling** que consulta preços reais de veículos na Tabela FIPE brasileira através de uma API pública, em duas partes: um [notebook Google Colab](notebook/fipe_ai_agent.ipynb) (entregável principal da atividade) e uma aplicação web completa (Next.js + FastAPI) que expõe o mesmo agente em uma interface de chat.

## Sumário

1. [O que é o projeto](#1-o-que-é-o-projeto)
2. [Objetivo acadêmico](#2-objetivo-acadêmico)
3. [O papel da IA vs. o papel do Python](#3-o-papel-da-ia-vs-o-papel-do-python)
4. [Arquitetura](#4-arquitetura)
5. [Tecnologias](#5-tecnologias)
6. [Estrutura do repositório](#6-estrutura-do-repositório)
7. [Como funciona o Function Calling](#7-como-funciona-o-function-calling)
8. [Fonte dos dados: API da FIPE](#8-fonte-dos-dados-api-da-fipe)
9. [Cuidados com a API pública](#9-cuidados-com-a-api-pública)
10. [Configuração do Gemini](#10-configuração-do-gemini)
11. [Como executar o notebook (Google Colab)](#11-como-executar-o-notebook-google-colab)
12. [Como executar o backend (FastAPI)](#12-como-executar-o-backend-fastapi)
13. [Como executar o frontend (Next.js)](#13-como-executar-o-frontend-nextjs)
14. [Exemplos de perguntas](#14-exemplos-de-perguntas)
15. [Tratamento de erros e ambiguidade](#15-tratamento-de-erros-e-ambiguidade)
16. [Limitações](#16-limitações)
17. [Como apresentar este projeto ao professor](#17-como-apresentar-este-projeto-ao-professor)

## 1. O que é o projeto

O **FIPE AI** é um agente de IA que responde perguntas em linguagem natural sobre preços de veículos, como:

- "Quanto vale um Toyota Corolla XEi 2022?"
- "Qual é o preço FIPE de uma Honda CG 160 Titan 2023?"
- "Quanto custa na FIPE uma Volkswagen Gol 1.0 2020?"

O modelo **Gemini** interpreta a pergunta, decide chamar uma ferramenta Python (`consultar_preco_fipe`) e essa ferramenta consulta, em tempo real, uma API pública com dados da Tabela FIPE. Nenhum preço é inventado: todo valor apresentado vem diretamente da resposta da API.

## 2. Objetivo acadêmico

Demonstrar, de forma prática e verificável, o padrão **agente + ferramenta** (*tool use* / *function calling*):

- Um modelo de linguagem sozinho **não tem acesso a dados atualizados** (como preços da FIPE, que mudam mensalmente).
- Para responder corretamente, o modelo precisa **decidir usar uma ferramenta externa**, fornecer os parâmetros corretos para ela, e depois **interpretar o resultado real** que ela devolve.
- Esse padrão é a base de agentes de IA capazes de agir sobre o mundo real (consultar sistemas, bancos de dados, APIs) em vez de apenas gerar texto a partir do que já sabem.

## 3. O papel da IA vs. o papel do Python

Esta separação é o ponto central da atividade e vale destacar com clareza:

**O Gemini (a IA) é responsável por:**
- Interpretar a linguagem natural da pergunta do usuário;
- Identificar a intenção (o usuário quer saber um preço FIPE);
- Extrair marca, modelo e ano da frase;
- Decidir **quando** usar a ferramenta `consultar_preco_fipe` (e pedir esclarecimento quando faltar informação, em vez de adivinhar);
- Fornecer os parâmetros corretos para a ferramenta;
- Interpretar o resultado (sucesso ou erro) recebido da ferramenta;
- Produzir uma resposta final em linguagem natural.

**A ferramenta Python é responsável por:**
- Receber os parâmetros já extraídos pelo Gemini;
- Realizar as requisições HTTP GET reais à API da FIPE;
- Navegar a hierarquia da API (tipo → marca → modelo → ano → preço);
- Tratar erros de rede, HTTP e dados;
- Retornar os dados reais (ou um erro estruturado) para o Gemini — **sem nenhuma inteligência própria**.

> **O Gemini nunca "sabe" um preço FIPE de antemão.** A única forma de obter esse valor é chamando a ferramenta, que busca o dado real na API. Isso é reforçado tanto pela instrução de sistema do agente quanto pela própria função, que nunca gera ou aproxima um valor — apenas repassa o que a API respondeu.

## 4. Arquitetura

```
Notebook (Colab):
  Usuário → Gemini (function calling) → Python (consultar_preco_fipe) → API FIPE → Gemini → Usuário

Aplicação web:
  Next.js (chat) → FastAPI (POST /chat) → Gemini (function calling) → Python (mesma ferramenta) → API FIPE
                                                                                                      │
  Next.js (chat) ← FastAPI (JSON: resposta + veículo) ← Gemini (interpreta o resultado) ←────────────┘
```

A chave da API do Gemini existe **somente no backend** (FastAPI) e nos *Secrets* do Colab — nunca no frontend, nunca no repositório.

O notebook e o backend implementam exatamente a mesma lógica de agente e a mesma ferramenta (a lógica foi escrita e validada uma vez no [backend](backend/app/tools/fipe_tool.py) e depois replicada de forma autocontida no notebook, para que ele possa ser executado isoladamente no Colab sem depender do restante do repositório).

## 5. Tecnologias

| Camada     | Tecnologia |
|------------|------------|
| Notebook   | Python, [`google-genai`](https://pypi.org/project/google-genai/) (SDK oficial do Gemini), `requests` |
| Frontend   | Next.js (App Router), TypeScript, Tailwind CSS |
| Backend    | Python, FastAPI, `google-genai`, `requests` |
| IA         | Gemini API (function calling) — modelo padrão `gemini-2.5-flash` |
| Dados      | [Fipe API v2](https://deividfortuna.github.io) (Parallelum) — `https://fipe.parallelum.com.br/api/v2` |

## 6. Estrutura do repositório

```
fipe-ai/
├── frontend/                    # Next.js + TypeScript + Tailwind CSS
│   ├── app/                     # App Router (layout, página, estilos globais)
│   ├── components/              # ChatPanel, VehicleResultCard, ToolFlowDiagram, Header
│   └── lib/api.ts               # Cliente HTTP para o backend (POST /chat)
│
├── backend/                     # FastAPI
│   ├── app/
│   │   ├── main.py              # Ponto de entrada da API (CORS, rotas)
│   │   ├── routes/chat.py       # POST /chat
│   │   ├── services/gemini_agent.py  # Configuração do agente e loop de function calling
│   │   ├── tools/fipe_tool.py   # A ferramenta: navegação da API da FIPE
│   │   ├── models/schemas.py    # Contratos Pydantic da API
│   │   └── config/settings.py   # Variáveis de ambiente
│   ├── requirements.txt
│   └── .env.example
│
├── notebook/
│   └── fipe_ai_agent.ipynb      # Entregável principal da atividade (Google Colab)
│
├── README.md
└── .gitignore
```

## 7. Como funciona o Function Calling

O fluxo é implementado **manualmente** (não pelo modo automático do SDK), tanto no notebook quanto no backend, propositalmente para deixar cada etapa visível e explicável:

1. A pergunta do usuário é enviada ao Gemini junto com a declaração da ferramenta (`tools=[...]`) e uma instrução de sistema.
2. Se o Gemini decidir que precisa de dados externos, a resposta contém uma **`function_call`** — nome da função e argumentos extraídos da pergunta (ex.: `consultar_preco_fipe(marca="Toyota", modelo="Corolla XEi", ano="2022")`) — em vez de texto.
3. O código Python executa essa função **localmente**. É aqui, e só aqui, que a API da FIPE é chamada de verdade via HTTP GET.
4. O resultado (JSON de sucesso ou erro) é devolvido ao Gemini como uma **`function_response`**.
5. O Gemini é chamado novamente, agora com o resultado real em mãos, e escreve a resposta final em linguagem natural.

Se o Gemini perceber que a pergunta está incompleta (ex.: falta o ano), ele responde diretamente pedindo esclarecimento, **sem** chamar a ferramenta — o parâmetro `ano` é obrigatório (`required`) na declaração da ferramenta, e a instrução de sistema reforça essa regra.

**Ferramenta exposta ao Gemini** (uma só, por simplicidade acadêmica — ver [seção 16](#16-limitações)):

```python
consultar_preco_fipe(marca: str, modelo: str, ano: str, tipo_veiculo: str = "carros")
```

Internamente ela executa a navegação hierárquica completa da API (`tipo → marca → modelo → ano → preço`) e a correspondência entre o texto livre do usuário e os nomes reais cadastrados na FIPE — mas isso é um detalhe de implementação da ferramenta, invisível ao Gemini, que só vê uma função de alto nível. Código completo em [`fipe_tool.py`](backend/app/tools/fipe_tool.py).

## 8. Fonte dos dados: API da FIPE

A Tabela FIPE oficial não expõe uma API pública própria. Este projeto usa a **Fipe API v2**, de terceiros, mantida por Deivid Fortuna (documentação em <https://deividfortuna.github.io>), gratuita e pública:

```
Base: https://fipe.parallelum.com.br/api/v2
```

Endpoints utilizados (confirmados na documentação oficial e validados manualmente durante o desenvolvimento):

| Método | Endpoint | Uso |
|--------|----------|-----|
| GET | `/references` | Referência de mês/ano vigente na FIPE |
| GET | `/{tipo}/brands` | Lista marcas (`tipo` = `cars`, `motorcycles` ou `trucks`) |
| GET | `/{tipo}/brands/{brandId}/models` | Lista modelos de uma marca |
| GET | `/{tipo}/brands/{brandId}/models/{modelId}/years` | Lista anos/versões de combustível de um modelo |
| GET | `/{tipo}/brands/{brandId}/models/{modelId}/years/{yearId}` | Preço final do veículo |

Não existe endpoint de busca livre por nome — por isso a ferramenta precisa navegar a hierarquia e fazer a correspondência de texto (ver [`_melhor_marca`, `_rankear_modelos`](backend/app/tools/fipe_tool.py)).

## 9. Cuidados com a API pública

- **Timeout** de 10s em toda requisição, para não travar o agente se a API da FIPE ficar lenta.
- **Cache em memória** (`functools.lru_cache`) para marcas, modelos e anos, evitando repetir chamadas para os mesmos dados durante a sessão.
- **Limite de candidatos testados** (no máximo 5 variantes de modelo por consulta) para não gerar dezenas de requisições em uma única pergunta ambígua.
- A API permite **500 requisições/dia por IP sem autenticação** — suficiente para uso acadêmico. Um token gratuito opcional (gerado em [fipe.api.br](https://fipe.api.br)) eleva esse limite para 1.000/dia; veja `FIPE_API_TOKEN` nos arquivos `.env.example`. **Não é obrigatório.**
- Nenhum dado é *mockado*: todas as demonstrações (notebook, backend, frontend) consultam a API real.

## 10. Configuração do Gemini

A chave (`GEMINI_API_KEY`) **nunca** é escrita em código-fonte:

- **No notebook**: é lida dos *Secrets* do Google Colab (`google.colab.userdata`) — veja a Seção 6 do notebook.
- **No backend**: é lida de uma variável de ambiente (arquivo `.env`, que está no `.gitignore` e nunca deve ser commitado).

Gere sua chave gratuita em [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

## 11. Como executar o notebook (Google Colab)

1. Abra o [`notebook/fipe_ai_agent.ipynb`](notebook/fipe_ai_agent.ipynb) no Google Colab.
2. No menu lateral, clique no ícone de chave (**Secrets**) e crie um secret `GEMINI_API_KEY` com sua chave. Habilite o acesso do notebook a ele.
3. (Opcional) Crie também um secret `FIPE_API_TOKEN` — não é obrigatório.
4. Execute as células em ordem (Ambiente de execução → Executar tudo).

## 12. Como executar o backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
copy .env.example .env        # Windows — no Linux/macOS: cp .env.example .env
```

Edite o `.env` e preencha `GEMINI_API_KEY`. Depois inicie o servidor:

```bash
uvicorn app.main:app --reload --port 8000
```

A API sobe em `http://localhost:8000` (documentação interativa em `/docs`). Teste rapidamente:

```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\": \"Quanto vale um Toyota Corolla XEi 2022?\"}"
```

## 13. Como executar o frontend (Next.js)

```bash
cd frontend
npm install
copy .env.example .env.local  # Windows — no Linux/macOS: cp .env.example .env.local
npm run dev
```

Por padrão o frontend espera o backend em `http://localhost:8000` (configurável via `NEXT_PUBLIC_API_BASE_URL` em `.env.local`). Acesse `http://localhost:3000`.

## 14. Exemplos de perguntas

- "Qual é o preço FIPE de um Toyota Corolla XEi 2022?"
- "Quanto vale uma Honda CG 160 Titan 2023?"
- "Quanto custa na FIPE uma Volkswagen Gol 1.0 2020?"
- "Quanto vale um Corolla?" → o agente pede a versão e o ano, em vez de adivinhar.

## 15. Tratamento de erros e ambiguidade

A ferramenta `consultar_preco_fipe` nunca deixa a aplicação quebrar; ela sempre devolve um resultado estruturado, com categorias de erro específicas:

| Categoria (`erro`) | Quando ocorre |
|---|---|
| `parametros_invalidos` | Marca, modelo ou ano não informados |
| `tipo_invalido` | Categoria de veículo não reconhecida |
| `marca_nao_encontrada` | Marca não existe na FIPE (com sugestões reais) |
| `modelo_ambiguo` | O nome do modelo casa com muitas versões diferentes (ex.: "Corolla" sem versão) — pede especificação |
| `modelo_nao_encontrado` | Nenhum modelo correspondente foi encontrado |
| `ano_nao_encontrado` | O modelo existe, mas não há dados para o ano pedido (lista os anos que existem) |
| `timeout` / `conexao` / `requisicao` | Falhas de rede ao chamar a API da FIPE |
| `limite_excedido` | HTTP 429 — limite de requisições da API atingido |
| `servico_indisponivel` | HTTP 5xx — API da FIPE fora do ar |
| `json_invalido` | Resposta em formato inesperado |

Em todos os casos, o Gemini recebe esse erro estruturado e o traduz em uma explicação amigável para o usuário — nunca inventando um valor no lugar do dado que faltou.

## 16. Limitações

- **Apenas uma ferramenta é exposta ao Gemini** (`consultar_preco_fipe`), por decisão consciente de simplicidade acadêmica: a navegação hierárquica (marca → modelo → ano) acontece **dentro** da ferramenta, não como múltiplas ferramentas separadas de function calling. A arquitetura já suporta expandir para ferramentas auxiliares (`listar_marcas`, `listar_modelos`, `listar_anos`) se desejado.
- **Carros, motos e caminhões são suportados** pela API e pelo código, mas os exemplos e testes deste projeto focam em carros e motos.
- **Correspondência de nomes é heurística** (normalização de texto + similaridade): nomes de modelo muito diferentes da nomenclatura oficial da FIPE podem não ser encontrados.
- **Preços mudam mensalmente**: os valores retornados refletem a tabela vigente no momento da consulta, não um valor fixo.
- **O modelo Gemini padrão** (`gemini-2.5-flash`) é configurável via variável de ambiente/constante, mas depende de disponibilidade contínua do modelo na API do Google.

## 17. Como apresentar este projeto ao professor

Um roteiro simples para explicar o projeto em poucos minutos:

1. **"Qual é o agente?"** — É o Gemini, configurado com uma instrução de sistema e uma ferramenta registrada ([`gemini_agent.py`](backend/app/services/gemini_agent.py) / Seção 11 do notebook). Ele recebe a pergunta em linguagem natural e decide sozinho se e como usar a ferramenta.
2. **"Qual é a ferramenta?"** — É a função Python [`consultar_preco_fipe`](backend/app/tools/fipe_tool.py) (Seção 9 do notebook). Ela não tem nenhuma inteligência: só sabe navegar a API da FIPE e devolver dados ou erros.
3. **"Onde está o Function Calling?"** — Na declaração `types.FunctionDeclaration` (Seção 10 do notebook / `gemini_agent.py`), que descreve para o Gemini o nome, a finalidade e os parâmetros da ferramenta; e no loop manual (Seção 12 do notebook) que mostra a resposta do Gemini contendo uma `function_call` antes de qualquer texto.
4. **"Onde acontece a chamada HTTP?"** — Dentro de `_get_json`, em `fipe_tool.py`: um `requests.get` real para `fipe.parallelum.com.br`.
5. **"Onde a API externa entra?"** — É a Fipe API v2 (Parallelum), uma API pública de terceiros com dados reais da Tabela FIPE, atualizados mensalmente.
6. **"Qual é o papel do Gemini?"** — Interpretar, decidir, extrair parâmetros e explicar o resultado em linguagem natural — nunca fornecer o preço por conta própria.
7. **"Qual é o papel do Python?"** — Buscar o dado real via HTTP e devolvê-lo, sem opinar ou inventar nada.
8. **Por que isso é um "agente com ferramenta"?** — Porque a IA **decide** quando agir sobre o mundo real (chamando uma função externa) em vez de apenas gerar texto a partir do que já sabe. A demonstração ao vivo — perguntar algo no notebook ou na interface web e observar os `print`s/logs de `function_call` → execução → `function_response` → resposta final — é a evidência mais direta desse conceito.

**Sugestão de demonstração ao vivo:** rodar as Seções 13, 14 e 15 do notebook (ou fazer as mesmas perguntas na interface web) e mostrar, em tempo real, o nome da função chamada, os argumentos extraídos pelo Gemini e o resultado retornado pela API antes da resposta final.

---

Projeto desenvolvido para fins acadêmicos. Dados de preços fornecidos pela [Fipe API](https://deividfortuna.github.io) (Parallelum), com base na Tabela FIPE oficial.
"# FIPE" 
