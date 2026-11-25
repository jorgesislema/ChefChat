import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useResumen } from "../hooks/useResumen";
import { Card, Cargando, ErrorCaja, Pagina, Tabla, Td, Th, Vacio } from "../components/ui/ui";
import { dinero } from "../lib/format";

export default function Mermas() {
  const m = useQuery({ queryKey: ["mermas"], queryFn: api.mermas });
  const r = useResumen();
  const error = m.error ?? r.error;
  return (
    <Pagina titulo="Mermas" subtitulo="Lo que se pierde y cuánto cuesta.">
      {error ? <ErrorCaja error={error} onReintentar={() => { void m.refetch(); void r.refetch(); }} /> : !m.data || !r.data ? <Cargando /> : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {r.data.mermas_por_motivo.map((x) => (
              <Card key={x.motivo}>
                <p className="capitalize text-muted">{x.motivo}</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{dinero(x.costo)}</p>
                <p className="text-sm text-muted">{x.veces} {x.veces === 1 ? "registro" : "registros"}</p>
              </Card>
            ))}
          </div>
          {m.data.mermas.length === 0 ? <Vacio titulo="Sin mermas registradas" texto="Cuando registres una pérdida aparecerá aquí." /> : (
            <Tabla>
              <thead><tr><Th>Fecha</Th><Th>Producto</Th><Th className="text-right">Cantidad</Th><Th>Motivo</Th><Th className="text-right">Costo</Th></tr></thead>
              <tbody>
                {m.data.mermas.map((x, i) => (
                  <tr key={i}><Td>{x.fecha}</Td><Td className="font-medium">{x.producto}</Td>
                    <Td className="text-right tabular-nums">{x.cantidad} {x.unidad}</Td><Td className="capitalize">{x.motivo}</Td>
                    <Td className="text-right tabular-nums">{dinero(x.costo_estimado)}</Td></tr>
                ))}
              </tbody>
            </Tabla>
          )}
        </>
      )}
    </Pagina>
  );
}
