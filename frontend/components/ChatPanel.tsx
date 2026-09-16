"use client";

import { useEffect, useRef, useState } from "react";
import { postChat, type ChatToolCall, type ChatVehicle } from "@/lib/api";
import { VehicleResultCard } from "./VehicleResultCard";
import { ToolFlowDiagram } from "./ToolFlowDiagram";

interface Message {
  role: "user" | "assistant";
  text: string;
}

const EXEMPLOS = [
  "Quanto vale um Toyota Corolla XEi 2022?",
  "Qual o preço FIPE de uma Honda CG 160 Titan 2023?",
  "Quanto custa um Volkswagen Gol 1.0 2020?",
];

export function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [vehicle, setVehicle] = useState<ChatVehicle | null>(null);
  const [toolCall, setToolCall] = useState<ChatToolCall | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  async function enviar(pergunta: string) {
    const texto = pergunta.trim();
    if (!texto || loading) return;

    setErrorBanner(null);
    setMessages((prev) => [...prev, { role: "user", text: texto }]);
    setInput("");
    setLoading(true);

    try {
      const data = await postChat(texto);
      setMessages((prev) => [...prev, { role: "assistant", text: data.response }]);
      if (data.vehicle) setVehicle(data.vehicle);
      if (data.tool_call) setToolCall(data.tool_call);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro inesperado ao consultar o agente.";
      setErrorBanner(msg);
      setMessages((prev) => [...prev, { role: "assistant", text: `Não consegui concluir a consulta: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    void enviar(input);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr] lg:items-start">
      <div className="flex flex-col rounded-2xl border border-white/10 bg-white/5 p-6">
        <div className="flex max-h-[28rem] min-h-[16rem] flex-col gap-4 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center gap-4 py-10 text-center text-slate-400">
              <p>Pergunte sobre o preço de um veículo na Tabela FIPE.</p>
              <div className="flex flex-wrap justify-center gap-2">
                {EXEMPLOS.map((exemplo) => (
                  <button
                    key={exemplo}
                    type="button"
                    onClick={() => void enviar(exemplo)}
                    className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-300 transition hover:border-blue-500/50 hover:text-blue-300"
                  >
                    {exemplo}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((mensagem, i) => (
            <div key={i} className={`flex ${mensagem.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  mensagem.role === "user"
                    ? "bg-blue-600 text-white"
                    : "border border-white/10 bg-white/5 text-slate-100"
                }`}
              >
                {mensagem.text}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-400">
                Consultando a Tabela FIPE…
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {errorBanner && (
          <p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
            {errorBanner}
          </p>
        )}

        <form onSubmit={onSubmit} className="mt-4 flex gap-2">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ex.: Quanto vale um Toyota Corolla XEi 2022?"
            className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="shrink-0 rounded-xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Consultar
          </button>
        </form>
      </div>

      <div className="flex flex-col gap-6">
        {vehicle ? (
          <VehicleResultCard vehicle={vehicle} />
        ) : (
          <div className="rounded-2xl border border-dashed border-white/15 p-6 text-center text-sm text-slate-500">
            O resultado da consulta aparecerá aqui.
          </div>
        )}
        <ToolFlowDiagram lastToolCall={toolCall} />
      </div>
    </div>
  );
}
