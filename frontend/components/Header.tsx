export function Header() {
  return (
    <header className="border-b border-white/10">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-10 sm:px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-lg font-bold text-white">
            F
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">FIPE AI</h1>
        </div>
        <p className="text-slate-300">Agente inteligente para consulta de veículos</p>
        <p className="text-sm text-slate-500">Consulte preços da Tabela FIPE usando Inteligência Artificial.</p>
      </div>
    </header>
  );
}
