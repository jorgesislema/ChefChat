import { Tabla, Td, Th } from "../ui/ui";
import { LoQuePaso } from "./LoQuePaso";
import { dinero, fechaLarga } from "../../lib/format";
import { etiquetaEstado, kg, pct } from "../../lib/balance";
import { costoSobranteFila, fechaHora, nombreTurno, sobranteFila, type FormInforme } from "../../lib/turno";
import type { Balance, InformeTurno, TotalesTurno } from "../../lib/api";

interface Props {
  inf: InformeTurno;
  form: FormInforme;
  totales: TotalesTurno;
  nombreChef: string;
  nombresPersonal: string[];
  balance?: Balance;
}

/** Versión para papel. En pantalla está oculta; el editor se oculta al imprimir (clase no-print). */
export function Imprimible({ inf, form, totales, nombreChef, nombresPersonal, balance }: Props) {
  const firmado = inf.estado === "firmado";
  return (
    <div className="print-area hidden space-y-4 print:block">
      <h1 className="text-2xl font-bold">Informe del turno — {nombreTurno(inf.turno)} — {fechaLarga(inf.fecha)}</h1>
      {!firmado && <p className="text-lg font-bold">BORRADOR</p>}
      <p><strong>Chef:</strong> {nombreChef || "Sin elegir"}</p>
      <p><strong>Personal:</strong> {nombresPersonal.length ? nombresPersonal.join(", ") : "Sin marcar"}</p>
      <p>
        <strong>Totales:</strong> producidos {totales.platos_producidos}, vendidos {totales.platos_vendidos}, sobrantes {totales.platos_sobrantes}
        {" "}({dinero(totales.costo_sobrante)}), merma {dinero(totales.merma)}, recuperado {dinero(totales.recuperado)}, compras {dinero(totales.compras)}.
      </p>
      <h2 className="text-lg font-semibold">Producido y vendido</h2>
      {form.filas.length === 0 ? <p>No se anotó ningún plato.</p> : (
        <Tabla>
          <thead><tr><Th>Plato</Th><Th>Producido</Th><Th>Vendido</Th><Th>Sobrante</Th><Th>Costo del sobrante</Th></tr></thead>
          <tbody>
            {form.filas.map((f) => (
              <tr key={f.clave}><Td>{f.plato}</Td><Td>{f.producido}</Td><Td>{f.vendido}</Td><Td>{sobranteFila(f)}</Td>
                <Td>{costoSobranteFila(f) === null ? "Sin costo" : dinero(costoSobranteFila(f))}</Td></tr>
            ))}
          </tbody>
        </Tabla>
      )}
      {balance && (
        <>
          <h2 className="text-lg font-semibold">Balance del turno</h2>
          <p><strong>Estado:</strong> {etiquetaEstado(balance.estado)}</p>
          <p>
            Entró {kg(balance.kg.entro)}, salió bueno {kg(balance.kg.salio_bueno)}, pérdida normal {kg(balance.kg.perdida_normal)},
            anotado {kg(balance.kg.anotado)}, sin explicar {kg(balance.kg.sin_explicar)} ({pct(balance.sin_explicar_pct)}
            {balance.sin_explicar_dinero === null ? "" : `, ${dinero(balance.sin_explicar_dinero)}`}).
          </p>
          {balance.por_ingrediente.length > 0 && (
            <Tabla>
              <thead><tr><Th>Producto</Th><Th>Entregado neto</Th><Th>Uso según receta</Th><Th>Merma</Th><Th>Diferencia</Th></tr></thead>
              <tbody>
                {balance.por_ingrediente.slice(0, 5).map((l) => (
                  <tr key={l.producto_id}><Td>{l.producto}</Td><Td>{kg(l.neto)}</Td><Td>{kg(l.uso_receta)}</Td><Td>{kg(l.merma)}</Td>
                    <Td>{l.calculable ? kg(l.diferencia) : "—"}</Td></tr>
                ))}
              </tbody>
            </Tabla>
          )}
        </>
      )}
      <LoQuePaso d={inf.datos} />
      <h2 className="text-lg font-semibold">Incidencias del turno</h2>
      {form.incidencias.length === 0 ? <p>Ninguna.</p> : (
        <ul className="list-disc pl-5">{form.incidencias.map((i, k) => <li key={k}><strong>{i.tipo}</strong>: {i.descripcion}</li>)}</ul>
      )}
      <h2 className="text-lg font-semibold">Observaciones</h2>
      <p className="whitespace-pre-wrap">{form.observaciones || "Sin observaciones."}</p>
      {firmado && <p className="pt-6"><strong>Firmado por {inf.firmado_por} el {fechaHora(inf.firmado_en)}</strong></p>}
    </div>
  );
}
