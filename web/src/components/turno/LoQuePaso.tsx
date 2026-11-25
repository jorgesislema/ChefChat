import type { ReactNode } from "react";
import { Card, Tabla, Td, Th } from "../ui/ui";
import { dinero } from "../../lib/format";
import type { DatosTurno } from "../../lib/api";

function Bloque({ titulo, total, vacio, children }: { titulo: string; total?: string; vacio: boolean; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="font-medium">{titulo}</h3>
        {total && <span className="text-sm text-muted">Total: <strong className="text-ink">{total}</strong></span>}
      </div>
      {vacio ? <p className="text-sm text-muted">Nada registrado.</p> : children}
    </div>
  );
}

const cant = (n: number, u: string) => `${n.toLocaleString("es-EC", { maximumFractionDigits: 3 })} ${u}`;

/** Lo que la base ya sabe del turno. Solo lectura. */
export function LoQuePaso({ d }: { d: DatosTurno }) {
  return (
    <Card className="space-y-6">
      <h2 className="text-lg font-semibold">Lo que pasó en el turno</h2>
      <Bloque titulo="Merma del día" total={dinero(d.merma_total)} vacio={d.mermas.length === 0}>
        <Tabla>
          <thead><tr><Th>Producto</Th><Th>Cantidad</Th><Th>Motivo</Th><Th className="text-right">Costo</Th></tr></thead>
          <tbody>
            {d.mermas.map((m, i) => (
              <tr key={`${m.producto}-${i}`}><Td>{m.producto}</Td><Td>{cant(m.cantidad, m.unidad)}</Td><Td>{m.motivo}</Td>
                <Td className="text-right">{m.costo_estimado === null ? "Sin costo" : dinero(m.costo_estimado)}</Td></tr>
            ))}
          </tbody>
        </Tabla>
      </Bloque>
      {d.nota_merma && <p className="text-sm text-muted">{d.nota_merma}</p>}
      <Bloque titulo="Merma recuperada" total={dinero(d.recuperado_total)} vacio={d.recuperado.length === 0}>
        <Tabla>
          <thead><tr><Th>Producto</Th><Th>Cantidad</Th><Th className="text-right">Valor</Th></tr></thead>
          <tbody>
            {d.recuperado.map((r, i) => (
              <tr key={`${r.producto}-${i}`}><Td>{r.producto}</Td><Td>{cant(r.cantidad, r.unidad)}</Td>
                <Td className="text-right">{r.valor === null ? "Sin valor" : dinero(r.valor)}</Td></tr>
            ))}
          </tbody>
        </Tabla>
      </Bloque>
      <Bloque titulo="Sobrantes nuevos" vacio={d.sobrantes_nuevos.length === 0}>
        <Tabla>
          <thead><tr><Th>Producto</Th><Th>Cantidad</Th><Th>Destino</Th></tr></thead>
          <tbody>
            {d.sobrantes_nuevos.map((s, i) => (
              <tr key={`${s.producto}-${i}`}><Td>{s.producto}</Td><Td>{cant(s.cantidad, s.unidad)}</Td><Td>{s.destino}</Td></tr>
            ))}
          </tbody>
        </Tabla>
      </Bloque>
      <Bloque titulo="Compras recibidas" total={dinero(d.compras_total)} vacio={d.compras.length === 0}>
        <Tabla>
          <thead><tr><Th>Proveedor</Th><Th>Producto</Th><Th>Cantidad</Th><Th className="text-right">Total</Th></tr></thead>
          <tbody>
            {d.compras.map((c, i) => (
              <tr key={`${c.producto}-${i}`}><Td>{c.proveedor}</Td><Td>{c.producto}</Td><Td>{cant(c.cantidad, c.unidad)}</Td>
                <Td className="text-right">{dinero(c.total)}</Td></tr>
            ))}
          </tbody>
        </Tabla>
      </Bloque>
      <Bloque titulo="Incidencias ya anotadas en la bitácora" vacio={d.incidencias_registradas.length === 0}>
        <ul className="space-y-1 text-sm">
          {d.incidencias_registradas.map((i, k) => (
            <li key={`${i.hora}-${k}`}><strong>{i.tipo}</strong>{i.hora ? <span className="text-muted"> ({i.hora})</span> : null}: {i.descripcion}</li>
          ))}
        </ul>
      </Bloque>
    </Card>
  );
}
