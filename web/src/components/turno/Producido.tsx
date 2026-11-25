import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button, Card, Tabla, Td, Th } from "../ui/ui";
import { campo } from "../edicion/comun";
import { dinero } from "../../lib/format";
import { costoSobranteFila, nuevaClave, sobranteFila, type FilaForm } from "../../lib/turno";
import type { RecetaResumen } from "../../lib/api";

interface Props {
  filas: FilaForm[];
  recetas: RecetaResumen[];
  editado: boolean;
  soloLectura: boolean;
  hayVentas: boolean;
  alCambiar: (filas: FilaForm[]) => void;
}

const num = `${campo} w-24 text-right`;

export function Producido({ filas, recetas, editado, soloLectura, hayVentas, alCambiar }: Props) {
  const [nuevo, setNuevo] = useState("");
  const cambiar = (clave: number, parte: Partial<FilaForm>) => alCambiar(filas.map((f) => (f.clave === clave ? { ...f, ...parte } : f)));

  const agregar = () => {
    const nombre = nuevo.trim();
    if (!nombre) return;
    const r = recetas.find((x) => x.nombre.toLowerCase() === nombre.toLowerCase());
    alCambiar([...filas, {
      clave: nuevaClave(), receta_id: r?.id_receta ?? null, plato: r?.nombre ?? nombre, servicio: null,
      producido: "0", vendido: "0", costo_plato: r?.costo_plato ?? null, recibido: "",
    }]);
    setNuevo("");
  };

  return (
    <Card className="space-y-3">
      <h2 className="text-lg font-semibold">Producido y vendido</h2>
      {!editado && !soloLectura && hayVentas && <p className="text-sm text-muted">Estos números vienen de las ventas registradas. Corrígelos si hace falta.</p>}
      {filas.length === 0 ? (
        <p className="rounded-xl border border-dashed border-line p-4 text-sm text-muted">
          {soloLectura ? "No se anotó ningún plato." : "No hay ventas registradas de este turno: anota lo que produjiste."}
        </p>
      ) : (
        <Tabla>
          <thead>
            <tr>
              <Th>Plato</Th><Th className="text-right">Producido</Th><Th className="text-right">Vendido</Th><Th className="text-right">Recibido</Th>
              <Th className="text-right">Sobrante</Th><Th className="text-right">Costo del sobrante</Th>
              {!soloLectura && <Th><span className="sr-only">Quitar</span></Th>}
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.clave}>
                <Td>
                  <span className="font-medium">{f.plato}</span>
                  {f.servicio && <span className="block text-xs text-muted">{f.servicio}</span>}
                </Td>
                <Td className="text-right">
                  {soloLectura ? f.producido : (
                    <input inputMode="numeric" className={num} value={f.producido} aria-label={`Producido de ${f.plato}`}
                      onChange={(e) => cambiar(f.clave, { producido: e.target.value })} />
                  )}
                </Td>
                <Td className="text-right">
                  {soloLectura ? f.vendido : (
                    <input inputMode="numeric" className={num} value={f.vendido} aria-label={`Vendido de ${f.plato}`}
                      onChange={(e) => cambiar(f.clave, { vendido: e.target.value })} />
                  )}
                </Td>
                <Td className="text-right">
                  {soloLectura ? (f.recibido || "—") : (
                    <input inputMode="numeric" className={num} value={f.recibido} placeholder="—" aria-label={`Recibido de ${f.plato}`}
                      onChange={(e) => cambiar(f.clave, { recibido: e.target.value })} />
                  )}
                </Td>
                <Td className="text-right">{sobranteFila(f)}</Td>
                <Td className="text-right">{costoSobranteFila(f) === null ? <span className="text-muted">Sin costo</span> : dinero(costoSobranteFila(f))}</Td>
                {!soloLectura && (
                  <Td>
                    <button type="button" aria-label={`Quitar ${f.plato}`} className="rounded-lg p-2 text-bad hover:bg-bad/10"
                      onClick={() => alCambiar(filas.filter((x) => x.clave !== f.clave))}><Trash2 size={16} aria-hidden /></button>
                  </Td>
                )}
              </tr>
            ))}
          </tbody>
        </Tabla>
      )}
      {!soloLectura && (
        <form className="no-print flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); agregar(); }}>
          <input list="turno-recetas" className={`${campo} min-w-0 flex-1 sm:max-w-sm`} placeholder="Nombre del plato" aria-label="Plato que quieres agregar"
            value={nuevo} onChange={(e) => setNuevo(e.target.value)} />
          <datalist id="turno-recetas">{recetas.map((r) => <option key={r.id_receta} value={r.nombre} />)}</datalist>
          <Button type="submit" disabled={!nuevo.trim()}><Plus size={14} aria-hidden /> Agregar plato</Button>
        </form>
      )}
    </Card>
  );
}
