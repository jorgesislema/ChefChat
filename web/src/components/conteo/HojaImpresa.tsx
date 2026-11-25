import type { ConteoDetalle } from "../../lib/api";
import { agruparPorCategoria, textoCantidad } from "../../lib/conteo";
import { fechaLarga } from "../../lib/format";

/** Versión para papel: en pantalla está oculta. La columna «Hay» sale vacía para escribir a mano, salvo lo que ya se contó. */
export function HojaImpresa({ d }: { d: ConteoDetalle }) {
  return (
    <div className="print-area hidden space-y-4 print:block">
      <h1 className="text-xl font-bold">Conteo de inventario — {fechaLarga(d.fecha)}</h1>
      {agruparPorCategoria(d.lineas).map((g) => (
        <section key={g.categoria} style={{ breakInside: "avoid" }}>
          <h2 className="mb-1 font-semibold">{g.categoria}</h2>
          <table className="w-full table-fixed border-collapse text-sm">
            <thead>
              <tr>
                <th scope="col" className="border px-2 py-1 text-left">Producto</th>
                <th scope="col" className="border px-2 py-1 text-right">Sistema</th>
                <th scope="col" className="w-32 border px-2 py-1 text-right">Hay</th>
                <th scope="col" className="border px-2 py-1 text-left">Unidad</th>
              </tr>
            </thead>
            <tbody>
              {g.lineas.map((l) => (
                <tr key={l.id}>
                  <td className="border px-2 py-2">{l.producto}</td>
                  <td className="border px-2 py-2 text-right">{textoCantidad(l.cantidad_sistema)}</td>
                  <td className="border px-2 py-2 text-right">{textoCantidad(l.cantidad_contada)}</td>
                  <td className="border px-2 py-2">{l.unidad}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}
