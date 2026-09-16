export interface ChatVehicle {
  brand: string;
  model: string;
  year: string;
  price: string;
  reference: string;
  fipe_code: string;
}

export interface ChatToolCall {
  name: string;
  arguments: Record<string, string>;
}

export interface ChatResponse {
  response: string;
  vehicle: ChatVehicle | null;
  tool_call: ChatToolCall | null;
  error: string | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * Envia a pergunta do usuário para o backend FastAPI, que por sua vez conversa
 * com o Gemini (function calling) e com a API da FIPE. O frontend nunca fala
 * diretamente com o Gemini nem com a FIPE — só com este backend.
 */
export async function postChat(message: string): Promise<ChatResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
  } catch {
    throw new Error("Não foi possível conectar ao backend do FIPE AI. Verifique se a API está em execução.");
  }

  if (!res.ok) {
    let detail = `Erro HTTP ${res.status} ao consultar o backend.`;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      // resposta sem corpo JSON — mantém a mensagem genérica
    }
    throw new Error(detail);
  }

  return res.json();
}
