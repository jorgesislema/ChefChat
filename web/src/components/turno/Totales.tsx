import { Card } from "../ui/ui";
import { dinero } from "../../lib/format";
import type { TotalesTurno } from "../../lib/api";

/** Totales del turno en tarjetas; se recalculan mientras el chef edita. */
export function Totales({ t }: { t: TotalesTurno }) {
  const items: { nombre: string; valor: string }[] = [
    { nombre: "Platos producidos", valor: String(t.platos_producidos) },
    { nombre: "Platos vendidos", valor: String(t.platos_vendidos) },
    { nombre: "Platos sobrantes", valor: String(t.platos_sobrantes) },
    { nombre: "Costo del sobrante", valor: dinero(t.costo_sobrante) },
    { nombre: "Merma del día", valor: dinero(t.merma) },
    { nombre: "Merma recuperada", valor: dinero(t.recuperado) },
    { nombre: "Compras recibidas", valor: dinero(t.compras) },
  ];
  return (
    <section aria-label="Totales del turno" className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
      {items.map((i) => (
        <Card key={i.nombre} className="p-4">
          <p className="text-xs text-muted">{i.nombre}</p>
          <p className="mt-1 text-xl font-bold">{i.valor}</p>
        </Card>
      ))}
    </section>
  );
}
