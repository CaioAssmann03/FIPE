import type { ChatVehicle } from "@/lib/api";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className="mt-1 font-medium text-white">{value || "—"}</dd>
    </div>
  );
}

export function VehicleResultCard({ vehicle }: { vehicle: ChatVehicle }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-lg shadow-black/20">
      <h3 className="mb-1 text-sm font-medium uppercase tracking-wide text-blue-400">Resultado da consulta</h3>
      <p className="mb-5 text-3xl font-semibold text-white">{vehicle.price || "—"}</p>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3">
        <Field label="Marca" value={vehicle.brand} />
        <Field label="Modelo" value={vehicle.model} />
        <Field label="Ano" value={vehicle.year} />
        <Field label="Referência" value={vehicle.reference} />
        <Field label="Código FIPE" value={vehicle.fipe_code} />
      </dl>

      <p className="mt-5 border-t border-white/10 pt-4 text-xs text-slate-500">Fonte: Tabela FIPE</p>
    </div>
  );
}
