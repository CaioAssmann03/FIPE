import type { ChatToolCall } from "@/lib/api";

const STEPS = [
  { title: "Gemini AI", desc: "Interpreta a pergunta em linguagem natural" },
  { title: "Function Calling", desc: "Decide chamar uma ferramenta e extrai os parâmetros" },
  { title: "consultar_preco_fipe", desc: "Função Python executa a lógica da ferramenta" },
  { title: "API FIPE", desc: "Requisição HTTP GET real à Tabela FIPE" },
  { title: "Dados reais", desc: "O resultado volta ao Gemini, que escreve a resposta" },
];

export function ToolFlowDiagram({ lastToolCall }: { lastToolCall?: ChatToolCall | null }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <h3 className="mb-1 text-sm font-medium uppercase tracking-wide text-blue-400">Ferramenta utilizada</h3>
      <p className="mb-5 text-sm text-slate-400">Como o agente chega até o preço, passo a passo.</p>

      <ol className="flex flex-col items-stretch">
        {STEPS.map((step, i) => (
          <li key={step.title}>
            <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 px-4 py-3">
              <p className="font-mono text-sm font-medium text-blue-300">{step.title}</p>
              <p className="mt-0.5 text-xs text-slate-400">{step.desc}</p>
            </div>
            {i < STEPS.length - 1 && (
              <div className="py-1 text-center text-blue-500/60" aria-hidden="true">
                ↓
              </div>
            )}
          </li>
        ))}
      </ol>

      {lastToolCall && (
        <div className="mt-5 rounded-xl border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Última chamada real desta sessão</p>
          <p className="mt-1 break-words font-mono text-sm text-slate-200">
            {lastToolCall.name}(
            {Object.entries(lastToolCall.arguments)
              .map(([k, v]) => `${k}="${v}"`)
              .join(", ")}
            )
          </p>
        </div>
      )}
    </div>
  );
}
