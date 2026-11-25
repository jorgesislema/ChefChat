import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Badge, Card, Cargando, ErrorCaja, Vacio } from "../ui/ui";

const ENTIDAD: Record<string, string> = { lote: "Lote", producto: "Producto", proveedor: "Proveedor", precio: "Precio", sobrante: "Sobrante" };
const ACCION = {
  crear: { nivel: "ok", texto: "Nuevo" },
  cambiar: { nivel: "warn", texto: "Cambio" },
  quitar: { nivel: "bad", texto: "Quitado" },
} as const;

/** "2026-05-19 14:30:05" -> "19/05/2026 14:30". Si el formato no es el esperado, lo muestra tal cual. */
const fechaHora = (s: string) => {
  const r = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(s);
  return r ? `${r[3]}/${r[2]}/${r[1]} ${r[4]}:${r[5]}` : s;
};

export function Cambios() {
  const q = useQuery({ queryKey: ["cambios"], queryFn: () => api.cambios(100) });
  return (
    <div className="space-y-4">
      <p className="text-muted">Aquí queda anotado todo lo que se cambia en precios, productos, lotes y proveedores.</p>
      {q.error ? <ErrorCaja error={q.error} onReintentar={() => q.refetch()} /> : !q.data ? <Cargando filas={5} /> :
        q.data.cambios.length === 0 ? (
          <Vacio titulo="Todavía no hay cambios anotados" texto="Cuando cambies un precio, un producto, un lote o un proveedor, quedará anotado aquí." />
        ) : (
          <Card className="p-0">
            <ul className="divide-y divide-line">
              {q.data.cambios.map((c) => {
                const a = ACCION[c.accion as keyof typeof ACCION];
                return (
                  <li key={c.id} className="flex flex-wrap items-start gap-x-4 gap-y-1 px-5 py-3">
                    <span className="w-36 shrink-0 text-sm tabular-nums text-muted">{fechaHora(c.fecha)}</span>
                    <span className="flex w-44 shrink-0 flex-wrap items-center gap-2">
                      <span className="text-sm font-medium">{ENTIDAD[c.entidad] ?? c.entidad}</span>
                      {a ? <Badge nivel={a.nivel}>{a.texto}</Badge> : <span className="text-xs text-muted">{c.accion}</span>}
                    </span>
                    <span className="min-w-0 flex-1 break-words text-sm">{c.detalle}</span>
                  </li>
                );
              })}
            </ul>
          </Card>
        )}
    </div>
  );
}
